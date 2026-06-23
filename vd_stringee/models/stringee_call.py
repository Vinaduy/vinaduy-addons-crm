"""Stringee call log + REST helpers.

Core invariants:
- State machine never downgrades (ended/failed/no_answer/busy/declined are terminal).
- Webhook events are idempotent: dedupe by (call_id, event) signature.
- Recording is downloaded eagerly on terminal state, retried by cron for delays.

Refs:
- Call API overview:    https://developer.stringee.com/docs/call-api-overview
- REST callout:         https://developer.stringee.com/docs/rest-api-reference/call-rest-api-callout
- Recording download:   https://developer.stringee.com/docs/rest-api-reference/call-rest-api-download-recorded-file
"""
import json
import logging
import re
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .vd_stringee_hotline import vd_carrier_from_number

# Nhãn nhà mạng tiếng Việt cho thông báo lỗi.
_CARRIER_LABELS = {
    'viettel': 'Viettel', 'vina': 'Vinaphone', 'mobi': 'MobiFone',
    'vietnamobile': 'Vietnamobile', 'gmobile': 'Gmobile', 'itelecom': 'iTel',
    'other': 'mạng khác',
}


def _phone_field(payload_value):
    """Extract a phone string from a Stringee payload value that can be str or dict."""
    if isinstance(payload_value, dict):
        return payload_value.get('number') or payload_value.get('alias') or ''
    return payload_value or ''


def _digits_only(s):
    return re.sub(r'\D', '', str(s or ''))


def _is_customer_event(payload, callee_number):
    """True if this Stringee event originates from the customer's PSTN leg
    (vs the bridge/project-side leg). Stringee call2 in IVR mode fires events
    on BOTH legs; we only want customer-side state transitions to count."""
    actor = _digits_only(payload.get('actor'))
    callee = _digits_only(callee_number)
    if not actor or not callee:
        return False
    return actor.endswith(callee[-9:]) or callee.endswith(actor[-9:])

_logger = logging.getLogger(__name__)

_STRINGEE_API = 'https://api.stringee.com'
_TIMEOUT = 30

# Lower = earlier in lifecycle. Webhook may arrive out of order; we ignore
# events that would move us back.
_STATE_RANK = {
    'draft': 0,
    'initiated': 1,
    'ringing': 2,
    'answered': 3,
    'ended': 9,
    'no_answer': 9,
    'busy': 9,
    'declined': 9,
    'failed': 9,
    'cancelled': 9,
}
_TERMINAL_STATES = {'ended', 'no_answer', 'busy', 'declined', 'failed', 'cancelled'}


def _to_stringee_number(num, default_country='84'):
    """Normalise a phone number for Stringee REST: digits only, with country code, NO '+' prefix.

    Stringee rejects '+' prefix (returns FROM_NUMBER_OR_TO_NUMBER_INVALID_FORMAT).

    Vietnamese conventions handled:
    - "0xxxxxxxxx"   → "84xxxxxxxxx"  (strip leading 0, prepend 84)
    - "84xxxxxxxxx"  → "84xxxxxxxxx"  (already country-coded)
    - "+84..."       → "84..."        (strip +)
    - bare local digits → prepend default country code
    """
    if not num:
        return ''
    digits = re.sub(r'\D', '', str(num))
    if not digits:
        return ''
    if digits.startswith('00'):           # 0084... = quốc tế kèu 00
        digits = digits[2:]
    if digits.startswith('0'):
        rest = digits[1:]
        # "084xxxxxxxxx" = SĐT lưu THỪA số 0 trước E.164 (0 + 84...) → bỏ luôn,
        # không prepend 84 lần nữa (tránh nhân đôi "8484..."). len>=11 để KHÔNG
        # nhầm số Vina national 9 chữ số bắt đầu 84x (vd 0848446886 → 84848446886).
        if rest.startswith(default_country) and len(rest) >= 11:
            return rest
        return default_country + rest
    if digits.startswith(default_country):
        # Đã bị nhân đôi sẵn: 84 + 84 + 9 = 13 chữ số → bỏ 1 cái 84.
        if len(digits) == 13 and digits.startswith(default_country * 2):
            return digits[len(default_country):]
        return digits
    return default_country + digits


class StringeeCall(models.Model):
    _name = 'stringee.call'
    _description = 'Stringee Call Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    name = fields.Char(string='Call ID', index=True, copy=False)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    direction = fields.Selection([
        ('outbound', 'Gọi đi'),
        ('inbound', 'Gọi đến'),
    ], default='outbound', required=True)

    caller_number = fields.Char(string='Từ số')
    callee_number = fields.Char(string='Đến số')

    user_id = fields.Many2one(
        'res.users', string='NV phụ trách',
        default=lambda self: self.env.user, ondelete='set null',
    )
    partner_id = fields.Many2one('res.partner', string='Liên hệ', ondelete='set null')

    state = fields.Selection([
        ('draft', 'Chưa khởi tạo'),
        ('initiated', 'Đã khởi tạo'),
        ('ringing', 'Đang đổ chuông'),
        ('answered', 'Đã trả lời'),
        ('ended', 'Đã kết thúc'),
        ('no_answer', 'Không nghe máy'),
        ('busy', 'Máy bận'),
        ('declined', 'Từ chối'),
        ('cancelled', 'Đã huỷ'),
        ('failed', 'Lỗi'),
    ], default='draft', tracking=True, index=True)

    start_time = fields.Datetime(string='Bắt đầu', default=fields.Datetime.now)
    answer_time = fields.Datetime(string='Trả lời lúc')
    end_time = fields.Datetime(string='Kết thúc lúc')
    duration = fields.Integer(string='Thời lượng (giây)', default=0)

    hangup_cause = fields.Char(string='Lý do kết thúc')

    recording_url = fields.Char(string='Recording URL (Stringee)')
    recording_id = fields.Char(string='Recording ID')
    recording_attachment_id = fields.Many2one(
        'ir.attachment', string='File ghi âm', ondelete='set null',
    )
    recording_player_url = fields.Char(
        compute='_compute_recording_player_url',
        help='URL local để player phát (chỉ trả ra khi đã có attachment).',
    )

    raw_events = fields.Text(string='Raw event log', help='JSON list of all webhook payloads received.')

    # ---------- Computed ----------

    @api.depends('name', 'caller_number', 'callee_number', 'state')
    def _compute_display_name(self):
        for rec in self:
            who = rec.callee_number or rec.caller_number or rec.name or _('(no id)')
            rec.display_name = f'[{rec.state or "?"}] {who}'

    @api.depends('recording_attachment_id')
    def _compute_recording_player_url(self):
        for rec in self:
            att = rec.recording_attachment_id
            rec.recording_player_url = f'/web/content/{att.id}?download=false' if att else ''

    # ---------- State helpers ----------

    @api.model
    def _bump_state(self, current, target):
        """Return target state only if it is >= current in lifecycle."""
        if not target:
            return current
        return target if _STATE_RANK.get(target, 0) >= _STATE_RANK.get(current or 'draft', 0) else current

    # ---------- Chẩn đoán sức khỏe số tổng đài (outbound) ----------

    @api.model
    def _vd_number_health(self, from_number, carrier=None):
        """Chẩn đoán 1 số tổng đài có còn GỌI RA được không, dựa lịch sử cuộc gọi.

        Mục đích: khi 1 cuộc rớt TRƯỚC khi đổ chuông, thay vì luôn đoán mò
        "số chưa kích hoạt outbound", ta tra lịch sử số đó để báo ĐÚNG:
          - dead  : gần đây KHÔNG cuộc nào đổ chuông → số HỎNG outbound (đổi số).
          - alive : số vẫn đổ chuông/nối được → cuộc này khách không nghe/bận.

        ⚠️ Tín hiệu PHẢI là "đã đổ chuông / khách nghe máy" lấy từ raw_events
        (webhook Stringee: call_status='ringing'/'answered') hoặc answer_time —
        KHÔNG dùng `duration` vì field này hay = 0 do placeholder record không
        khớp được webhook (lỗi ghi nhận giây), KHÔNG phản ánh số có hỏng hay
        không. Một số gọi rất nhiều, khách nghe máy thật nhưng duration vẫn 0.
        """
        digits9 = re.sub(r'\D', '', from_number or '')[-9:]
        if not digits9:
            return {'state': 'alive', 'level': 'info', 'title': '', 'message': ''}
        carrier = carrier or vd_carrier_from_number(from_number)
        label = _CARRIER_LABELS.get(carrier, carrier or '')
        like = '%' + digits9
        cr = self.env.cr
        # "Đã RA TỚI nhà mạng" = webhook báo ringing/answered, hoặc có answer_time.
        # (% literal trong ILIKE phải double thành %% vì câu lệnh có param %s.)
        reached_sql = (
            "(raw_events ILIKE '%%ringing%%' "
            " OR raw_events ILIKE '%%answered%%' "
            " OR answer_time IS NOT NULL)"
        )
        # (1) Toàn lịch sử: đã bao giờ đổ chuông tới khách chưa?
        cr.execute(
            "SELECT count(*), count(*) FILTER (WHERE " + reached_sql + ") "
            "FROM stringee_call "
            "WHERE direction='outbound' AND caller_number LIKE %s",
            [like],
        )
        total_all, reached_all = cr.fetchone()
        # (2) Cửa sổ GẦN ĐÂY (3 ngày): hiện số còn đổ chuông được không?
        cr.execute(
            "SELECT count(*), count(*) FILTER (WHERE " + reached_sql + ") "
            "FROM stringee_call "
            "WHERE direction='outbound' AND caller_number LIKE %s "
            "  AND create_date > (now() at time zone 'utc') - interval '3 days'",
            [like],
        )
        recent_total, recent_reached = cr.fetchone()

        num_disp = re.sub(r'\D', '', from_number) if from_number else digits9
        common = {
            'total': total_all, 'reached': reached_all,
            'recent_total': recent_total, 'recent_reached': recent_reached,
        }
        # === Phân loại (CHỈ dead vs alive, dựa tín hiệu đổ chuông thật) ===
        never_reached = (reached_all == 0 and total_all >= 3)
        broke_recently = (recent_reached == 0 and recent_total >= 8)
        if never_reached or broke_recently:
            if never_reached:
                detail = (
                    f'đã thử {total_all} cuộc nhưng CHƯA cuộc nào đổ chuông tới '
                    f'khách. Số chưa được mở gọi ra (outbound) trên Stringee, '
                    f'hoặc đã hỏng.'
                )
            else:
                detail = (
                    f'{recent_total} cuộc gần đây KHÔNG cuộc nào đổ chuông được '
                    f'(trước đây vẫn gọi được). Số đang bị chặn/lỗi đường gọi ra.'
                )
            return {
                'state': 'dead', 'level': 'danger',
                'title': f'Số {label} không gọi ra được — kiểm tra Stringee',
                'message': (
                    f'🔴 Số tổng đài {label} {num_disp} — {detail} '
                    f'→ Báo admin đổi số / kiểm tra số này trên Stringee Dashboard.'
                ),
                **common,
            }
        # Số vẫn đổ chuông/nối được → cuộc này lỗi phía khách/tạm thời.
        return {
            'state': 'alive', 'level': 'info',
            'title': 'Khách chưa kết nối',
            'message': (
                f'Cuộc này chưa kết nối được (khách không nghe/bận hoặc nghẽn '
                f'tạm thời). Số tổng đài {label} {num_disp} vẫn gọi ra bình '
                f'thường — thử gọi lại sau.'
            ),
            **common,
        }

    @api.model
    def _vd_numbers_stats(self, numbers, alive_days=30, dead_days=4, dead_min=3):
        """Thống kê theo LÔ số tổng đài (cho bảng kho số). Trả dict:
            number -> {total, reached, reached_recent, secs, first, last,
                       active_days, per_day, health}
        - reached/reached_recent đếm cuộc ĐỔ CHUÔNG/NGHE MÁY thật (raw_events
          ringing/answered hoặc answer_time) — KHÔNG dùng duration (hay = 0).
        - health:
            'dead'   = trong `dead_days` ngày gần đây gọi >= `dead_min` cuộc mà
                       0 cuộc đổ chuông (nhà mạng chặn số) — bắt số MỚI chết kể cả
                       khi nó còn đổ chuông trong 30 ngày (fix 2026-06-23: trước
                       đây cửa sổ 30 ngày quá rộng -> số chết 16/06 vẫn 'alive').
            'alive'  = có đổ chuông gần đây HOẶC từng đổ chuông và gần đây ít dùng
                       (tránh false-dead làm tự gỡ số tốt đang nhàn).
            'unused' = chưa gọi cuộc nào.
        """
        out = {}
        nums = [n for n in (numbers or []) if n]
        if not nums:
            return out
        cr = self.env.cr
        reached = ("(raw_events ILIKE '%%ringing%%' OR raw_events ILIKE "
                   "'%%answered%%' OR answer_time IS NOT NULL)")
        # QUAN TRỌNG: tính `today` TRƯỚC execute. fields.Date.context_today có thể
        # chạy 1 query phụ (đọc timezone user) — nếu xen GIỮA execute và fetchall
        # sẽ ĐÈ kết quả con trỏ → fetchall ra rỗng (bug lộ khi cron chạy đầu
        # transaction, lúc tz chưa cache). Fix 2026-06-09.
        today = fields.Date.context_today(self)
        cr.execute(
            "SELECT caller_number, "
            "  count(*) AS total, "
            "  count(*) FILTER (WHERE " + reached + ") AS reached, "
            "  count(*) FILTER (WHERE " + reached + " AND create_date > "
            "      (now() at time zone 'utc') - (%s || ' days')::interval) AS reached_recent, "
            "  count(*) FILTER (WHERE create_date > "
            "      (now() at time zone 'utc') - (%s || ' days')::interval) AS recent_total, "
            "  count(*) FILTER (WHERE " + reached + " AND create_date > "
            "      (now() at time zone 'utc') - (%s || ' days')::interval) AS recent_reached, "
            "  COALESCE(sum(duration),0) AS secs, "
            "  min(create_date) AS first_at, max(create_date) AS last_at "
            "FROM stringee_call "
            "WHERE direction='outbound' AND caller_number IN %s "
            "GROUP BY caller_number",
            [str(alive_days), str(dead_days), str(dead_days), tuple(nums)],
        )
        rows = cr.fetchall()
        for row in rows:
            (number, total, rch, rch_recent, recent_total, recent_reached,
             secs, first_at, last_at) = row
            first_d = first_at.date() if first_at else None
            last_d = last_at.date() if last_at else None
            active_days = ((today - first_d).days + 1) if first_d else 0
            per_day = round(total / active_days, 1) if active_days else 0
            if total == 0:
                health = 'unused'
            elif recent_total >= dead_min and recent_reached == 0:
                # Gần đây gọi nhiều mà 0 đổ chuông -> nhà mạng chặn số (kể cả khi
                # 30 ngày trước còn đổ chuông).
                health = 'dead'
            elif rch_recent > 0:
                health = 'alive'
            elif rch > 0:
                # Từng đổ chuông, gần đây ít dùng -> GIỮ alive (tránh tự gỡ số tốt).
                health = 'alive'
            else:
                health = 'dead'   # gọi nhiều nhưng chưa cuộc nào đổ chuông
            out[number] = {
                'total': total, 'reached': rch, 'reached_recent': rch_recent,
                'secs': int(secs or 0),
                'first': first_d.strftime('%d/%m/%Y') if first_d else '',
                'last': last_d.strftime('%d/%m/%Y') if last_d else '',
                'active_days': active_days, 'per_day': per_day,
                'health': health,
            }
        # Số chưa có cuộc nào → unused
        for n in nums:
            out.setdefault(n, {
                'total': 0, 'reached': 0, 'reached_recent': 0, 'secs': 0,
                'first': '', 'last': '', 'active_days': 0, 'per_day': 0,
                'health': 'unused',
            })
        return out

    # ---------- REST helpers ----------

    @api.model
    def _stringee_headers(self):
        token = self.env['stringee.jwt'].gen_rest_token()
        if not token:
            raise UserError(_('Chưa cấu hình API Key SID/Secret cho Stringee.'))
        return {'X-STRINGEE-AUTH': token, 'Content-Type': 'application/json'}

    @api.model
    def _scco_actions(self, record=True, event_url=None):
        """Build SCCO actions list per Stringee docs.

        Spec: https://developer.stringee.com/docs/scco/record
        Valid fields: action, eventUrl, format (mp3|wav), recordStereo.
        Stringee stores recording server-side automatically; download via
        GET /v1/call/recording/{call_id} after webhook arrives at eventUrl.

        ⚠️ Chỉ work nếu project Stringee có ENABLE record feature ở dashboard.
        Nếu Stringee trả HTTP 400 ở download endpoint → record bị disabled,
        check Dashboard → Project Settings → Recording.
        """
        actions = []
        if record:
            # KHÔNG set eventUrl ở SCCO — Stringee dashboard project đã config
            # (per partner: "set trên project là được, không cần set vào SCCO").
            actions.append({
                'action': 'record',
                'format': 'mp3',
                'recordStereo': True,   # ghi 2 kênh riêng (caller/callee)
            })
        return actions

    # ---------- Outbound (REST callout) ----------

    def action_callout(self):
        """Trigger an outbound call via REST. Server-side initiated.

        ⚠️ KIẾN TRÚC QUAN TRỌNG (2026-05-15):
        Stringee `/v1/call2/callout` CHỈ hỗ trợ external→external (PSTN-to-PSTN).
        Endpoint này KHÔNG bridge được audio với browser. Tested:
        - `from.type=internal` → Stringee reject "Could not decode POST data"
        - `from.type=external, to.type=external` + connect external→external
          → double-call
        - `from.type=external, to.type=external` + no connect
          → Stringee IVR auto-end sau 5-9s

        Conclusion: REST callout **không phù hợp cho audio 2 chiều**. Path này
        chỉ để cho trường hợp NV không có stringee_user_id (no Web SDK
        access), và sẽ dial KH với hotline làm Caller ID, KH bắt máy nhưng
        không có ai nói chuyện (sẽ tự ngắt sau vài giây).

        For real audio: dùng action_call() ở crm.lead → return client action
        → trigger Web SDK call ở browser.
        """
        self.ensure_one()
        if not self.callee_number:
            raise UserError(_('Thiếu số đến.'))
        Param = self.env['ir.config_parameter'].sudo()
        # Ưu tiên hotline assign cho NV → fallback global config
        user_hotline = (
            self.user_id.stringee_from_number_id.number
            if (self.user_id and self.user_id.stringee_from_number_id) else ''
        )
        # Ưu tiên đầu số CÙNG MẠNG đã resolve (vd_from_number_override) — user
        # spec 2026-06-01. Fallback số đơn cũ → global config.
        from_number = _to_stringee_number(
            self.env.context.get('vd_from_number_override')
            or user_hotline or Param.get_param('vd_stringee.from_number')
        )
        callee_e164 = _to_stringee_number(self.callee_number)
        record = (Param.get_param('vd_stringee.record_calls') or 'True') in ('True', 'true', '1')
        if not from_number:
            raise UserError(_('Chưa cấu hình "From Number".'))
        if not callee_e164:
            raise UserError(_('Số gọi đến không hợp lệ.'))

        # === CHỈ GỌI NỘI MẠNG (Stringee cấm gọi ngoại mạng, 2026-06) ===
        # Số gọi đi PHẢI cùng nhà mạng với số khách. Gọi ngoại mạng bị nhà mạng
        # chặn (~97% rớt trước đổ chuông) VÀ có thể khoá số gọi đi → không bao
        # giờ fallback số khác mạng; chặn ngay + báo rõ cho NV.
        from_carrier = vd_carrier_from_number(from_number)
        callee_carrier = vd_carrier_from_number(callee_e164)
        if from_carrier != callee_carrier or callee_carrier == 'other':
            self.write({'state': 'failed', 'hangup_cause': 'CROSS_NETWORK_BLOCKED'})
            from_lbl = _CARRIER_LABELS.get(from_carrier, from_carrier)
            callee_lbl = _CARRIER_LABELS.get(callee_carrier, callee_carrier)
            if callee_carrier == 'other':
                raise UserError(_(
                    'CHẶN gọi ngoại mạng: số khách %s thuộc %s — chỉ cho gọi '
                    'NỘI MẠNG Viettel/Vinaphone/MobiFone/Vietnamobile/iTel.'
                ) % (callee_e164, callee_lbl))
            raise UserError(_(
                'CHẶN gọi ngoại mạng: số gọi đi %s (%s) KHÁC mạng với số khách '
                '%s (%s). Cần số tổng đài %s để gọi cùng mạng — báo admin gán số %s.'
            ) % (from_number, from_lbl, callee_e164, callee_lbl, callee_lbl, callee_lbl))

        base_url = (Param.get_param('web.base.url') or '').rstrip('/')

        # Body callout: CHỈ record (evidence-based decision 2026-05-16):
        # Đã verify: Stringee project 2705200 KHÔNG support SCCO `connect
        # to=internal` trong body callout — call tear down ngay tại pickup
        # (answerDuration=0). Browser NV đã online (heartbeat r=0 SUCCESS)
        # nhưng Stringee vẫn drop SCCO → đây là Stringee server config.
        # Giữ chỉ `record` để ít nhất KH có 4-5s sau bắt máy (Stringee IVR
        # default playback) trước khi auto-end. Cần Stringee support enable
        # SCCO connect-internal hoặc Web SDK App-to-Phone để có audio bridge.
        actions = self._scco_actions(
            record=record, event_url=f'{base_url}/stringee/recording_event',
        )
        body = {
            'from': {'type': 'external', 'number': from_number, 'alias': from_number},
            'to':   [{'type': 'external', 'number': callee_e164, 'alias': callee_e164}],
            'actions': actions,
        }
        if record:
            body['record'] = True
            body['recordFormat'] = 'mp3'
            body['eventUrl'] = f'{base_url}/stringee/recording_event'
        # === RACE FIX: pre-stamp 'initiated' state + commit BEFORE POST ===
        # Stringee gọi /stringee/answer SONG SONG với việc dial KH, có thể đến
        # trước khi requests.post() return (network latency). Pre-commit để
        # controller fallback tìm theo (callee_number + direction=outbound +
        # create_date < 30s) match được record → biết REST outbound → KHÔNG
        # thêm SCCO connect → tránh double-call.
        self.write({'state': 'initiated'})
        self.env.cr.commit()

        # VERBOSE LOG: SCCO body để verify record action có được gửi không
        _logger.info(
            "[Stringee callout] POST /v1/call2/callout body=%s",
            json.dumps(body, ensure_ascii=False),
        )
        try:
            resp = requests.post(
                f'{_STRINGEE_API}/v1/call2/callout',
                headers=self._stringee_headers(),
                json=body,
                timeout=_TIMEOUT,
            )
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.exception("Stringee callout failed")
            self.write({'state': 'failed', 'hangup_cause': f'callout exception: {e}'})
            raise UserError(_('Không gọi được: %s') % e)

        # VERBOSE LOG: full response để biết Stringee accept record action không
        _logger.info(
            "[Stringee callout] status=%s response=%s",
            resp.status_code, json.dumps(data, ensure_ascii=False)[:1000],
        )
        if resp.status_code != 200 or data.get('r') != 0:
            msg = data.get('message') or f'HTTP {resp.status_code}'
            self.write({'state': 'failed', 'hangup_cause': msg})
            raise UserError(_('Stringee từ chối: %s') % msg)

        call_id = data.get('call_id') or data.get('callId')
        self.write({'name': call_id or self.name, 'state': 'initiated'})
        # Commit so subsequent webhook lookups by call_id succeed even if this
        # transaction rolls back later.
        self.env.cr.commit()
        return True

    @api.model
    def make_call(self, callee_number, partner_id=None, user_id=None, from_number=None):
        """Create call record and trigger callout. Returns the record.
        from_number: đầu số CÙNG MẠNG đã resolve (truyền xuống action_callout).

        DEDUP: nếu user vừa gọi CÙNG SỐ trong 3 GIÂY (window ngắn để chỉ chặn
        accidental double-click, không chặn legitimate retry sau khi cúp).
        Trả về record cũ thay vì tạo mới.
        """
        user_id = user_id or self.env.user.id
        callee_norm = _to_stringee_number(callee_number) or callee_number
        recent = self.search([
            ('user_id', '=', user_id),
            ('callee_number', 'in', list({callee_number, callee_norm, _digits_only(callee_number)})),
            ('create_date', '>', fields.Datetime.now() - timedelta(seconds=3)),
        ], limit=1, order='create_date desc')
        if recent:
            _logger.info(
                "Stringee make_call DEDUP (3s): user=%s callee=%s reusing call %s (state=%s)",
                user_id, callee_number, recent.id, recent.state,
            )
            return recent
        rec = self.create({
            'callee_number': callee_number,
            'partner_id': partner_id,
            'user_id': user_id,
            'direction': 'outbound',
        })
        rec.with_context(vd_from_number_override=from_number).action_callout()
        return rec

    # ---------- Tra số / định tuyến (hook cho vd_crm_lead) ----------

    @api.model
    def _vd_lookup_number_owner(self, number, current_uid=None):
        """Tra 1 số điện thoại → KH đã có + NV quản lý.

        STUB ở vd_stringee (không có crm.lead). vd_crm_lead override để trả:
            {found, lead_id, lead_name, owner_id, owner_name,
             is_mine, owned_by_other}
        Mặc định trả {'found': False}.
        """
        return {'found': False}

    @api.model
    def _vd_ensure_dialed_lead(self, number, user_id):
        """Số mới (chưa có KH) gọi tay xong → tự lưu vào danh sách KH mới.

        STUB ở vd_stringee. vd_crm_lead override để tạo crm.lead.
        """
        return {'created': False}

    @api.model
    def _vd_resolve_inbound_user(self, caller, callee):
        """Cuộc gọi ĐẾN (khách gọi vào hotline `callee`) thì ring NV nào?

        Mặc định (vd_stringee): NV đang được gán số tổng đài `callee` đó và có
        stringee_user_id (browser gọi được). vd_crm_lead override để ƯU TIÊN
        NV quản lý KH theo số khách `caller` (lead.user_id), fallback về super().
        Trả về recordset res.users (rỗng nếu không xác định được).
        """
        Users = self.env['res.users']
        did9 = _digits_only(callee)[-9:]
        if not did9:
            return Users
        hotline = self.env['vd.stringee.hotline'].sudo().search([]).filtered(
            lambda h: _digits_only(h.number)[-9:] == did9
        )[:1]
        if hotline:
            cand = hotline.assigned_user_ids.filtered(
                lambda u: u.active and u.stringee_user_id
            )[:1]
            if cand:
                return cand
        return Users

    def action_transfer(self, target_user_id):
        """CHUYỂN MÁY SỐNG sang NV khác (user spec 2026-06-20).

        Gửi SCCO `connect` mới vào cuộc đang chạy qua Stringee putactions →
        Stringee ngắt leg NV hiện tại, đổ chuông browser NV-B (incomingcall2 →
        auto-answer). Khách GIỮ NGUYÊN máy, audio 2 chiều chuyển sang NV-B.
        Ref: https://developer.stringee.com/docs/rest-api-reference/call-rest-api-put-actions-scco
        """
        self.ensure_one()
        target = self.env['res.users'].sudo().browse(int(target_user_id))
        if not target.exists():
            raise UserError(_('Không tìm thấy nhân viên cần chuyển.'))
        sui = (target.stringee_user_id or '').strip()
        if not sui:
            raise UserError(_(
                'NV "%s" chưa cấu hình Stringee (stringee_user_id) → không chuyển máy được.'
            ) % target.name)
        if not self.name:
            raise UserError(_('Cuộc gọi chưa có Call ID — không chuyển được.'))
        # from = số tổng đài khách đang nối (callee của cuộc gọi đến); to = NV-B
        hotline = _to_stringee_number(self.callee_number) or _to_stringee_number(self.caller_number)
        actions = [{
            'action': 'connect',
            'from': {'type': 'external', 'number': hotline, 'alias': hotline},
            'to': {'type': 'internal', 'number': sui, 'alias': sui},
            'peerToPeerCall': False,
            'continueOnFail': True,
            'timeout': 30,
        }]
        try:
            resp = requests.post(
                f'{_STRINGEE_API}/v1/call2/putactions',
                headers=self._stringee_headers(),
                json={'callId': self.name, 'actions': actions},
                timeout=_TIMEOUT,
            )
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.warning('[Stringee transfer] %s lỗi mạng: %s', self.name, e)
            raise UserError(_('Lỗi gọi Stringee khi chuyển máy: %s') % e)
        if str(data.get('r')) != '0':
            _logger.warning('[Stringee transfer] %s từ chối: %s', self.name, data)
            raise UserError(_('Stringee từ chối chuyển máy (r=%s): %s') % (
                data.get('r'), data.get('message') or data))
        old_user = self.user_id
        self.write({'user_id': target.id})
        try:
            self.message_post(body=_('📞➡️ Chuyển máy: %s → %s') % (
                old_user.name or '—', target.name))
        except Exception:
            pass
        _logger.info('[Stringee transfer] %s: %s → %s OK', self.name,
                     old_user.name, target.name)
        return {'success': True, 'target_name': target.name}

    def action_hangup(self):
        """Stop an active call via REST. Idempotent — silent if already ended."""
        self.ensure_one()
        if self.state in _TERMINAL_STATES:
            return True
        if not self.name:
            self.write({'state': 'cancelled', 'end_time': fields.Datetime.now()})
            return True
        try:
            resp = requests.post(
                f'{_STRINGEE_API}/v1/call2/stop',
                headers=self._stringee_headers(),
                json={'callId': self.name},
                timeout=_TIMEOUT,
            )
            data = resp.json() if resp.content else {}
        except Exception:
            _logger.warning("Stringee stop network error for %s", self.name, exc_info=True)
            data = {'r': -1}
        # r=0 ok, r=1 already ended, r=2 not found — all map to "ended" locally.
        # We log unknown codes but never block the user from continuing.
        if data.get('r') not in (0, 1, 2):
            _logger.info("Stringee stop returned r=%s msg=%s for %s",
                         data.get('r'), data.get('message'), self.name)
        self.write({'state': 'ended', 'end_time': fields.Datetime.now()})
        return True

    # ---------- Webhook handler ----------

    @api.model
    def handle_event(self, payload):
        """Process a webhook event from Stringee. Idempotent.

        Stringee call event payload (we care about):
            call_id, call_status (created|ringing|answered|ended), event_id,
            direction (OUTBOUND|INBOUND), from (dict), to (dict),
            answerDuration, duration, endCallCause, endedBy
        """
        call_id = payload.get('call_id') or payload.get('callId')
        if not call_id:
            _logger.warning("Stringee event without call_id: %s", payload)
            return

        # Idempotency: skip if we've seen this exact event_id before
        event_id = payload.get('event_id')
        from_payload = payload.get('from') or payload.get('caller')
        to_payload = payload.get('to') or payload.get('callee')
        from_phone = _phone_field(from_payload)
        to_phone = _phone_field(to_payload)
        # Stringee KHÔNG luôn có field `direction` trong payload. Suy ra
        # từ các tín hiệu khác: to.type='external' = outbound từ App→PSTN,
        # callCreatedReason='CLIENT_MAKE_CALL' = chắc chắn outbound từ Web SDK.
        is_outbound = (
            (payload.get('direction') or '').upper() == 'OUTBOUND'
            or (isinstance(to_payload, dict) and to_payload.get('type') == 'external')
            or payload.get('callCreatedReason') == 'CLIENT_MAKE_CALL'
        )

        rec = self.search([('name', '=', call_id)], limit=1)
        # If no record yet, try to claim a recent same-direction stub created by
        # action_callout (before the Stringee callId came back). So sánh callee
        # bằng SUFFIX 9 chữ số cuối (chấp nhận 0348886375 ≡ 84348886375).
        if not rec and is_outbound and to_phone:
            to_norm9 = _digits_only(to_phone)[-9:]
            recent_cutoff = fields.Datetime.now() - timedelta(seconds=60)
            candidates = self.search([
                ('name', '=', False),
                ('direction', '=', 'outbound'),
                ('create_date', '>', recent_cutoff),
            ], order='create_date desc', limit=20)
            _logger.info(
                "[Stringee matcher] call_id=%s to=%s norm9=%s candidates=%s",
                call_id, to_phone, to_norm9,
                [(s.id, s.callee_number, s.state) for s in candidates],
            )
            for stub in candidates:
                stub_norm9 = _digits_only(stub.callee_number)[-9:]
                if stub_norm9 and stub_norm9 == to_norm9:
                    vals_claim = {'name': call_id}
                    # Nếu stub đã bị self-heal trước khi event đến → reset
                    # state về 'initiated' để event flow bump bình thường
                    if stub.hangup_cause == 'SELF_HEAL_ON_NEW_CALL':
                        vals_claim.update({
                            'state': 'initiated',
                            'end_time': False,
                            'hangup_cause': False,
                        })
                    stub.write(vals_claim)
                    rec = stub
                    _logger.info(
                        "Stringee claim stub id=%s for call_id=%s (callee %s ≡ %s) state_reset=%s",
                        stub.id, call_id, stub.callee_number, to_phone,
                        'SELF_HEAL_ON_NEW_CALL' in vals_claim.values(),
                    )
                    break
        if not rec:
            rec = self.create({
                'name': call_id,
                'direction': 'outbound' if is_outbound else 'inbound',
                'caller_number': from_phone,
                'callee_number': to_phone,
                'state': 'initiated',
            })

        # Skip duplicate event
        if event_id and rec.raw_events:
            try:
                seen = json.loads(rec.raw_events)
                if any(e.get('event_id') == event_id for e in seen):
                    return rec
            except ValueError:
                pass

        call_status = payload.get('call_status') or ''
        new_state = self._event_to_state(call_status, payload)

        # ============ FILTER FALSE-POSITIVE 'answered' EVENTS ============
        # Stringee đôi khi fire 'answered' KHÔNG phải vì KH bắt máy:
        #   1. Bridge/from-number leg (IVR mode): actor không phải callee
        #   2. Voicemail / carrier auto-answer signal: arrival > 25s sau ringing
        #   3. Event với answerDuration=0 trong cùng payload (rare)
        # Bỏ qua hết 3 case này để UI không kẹt "Đang gọi" sai.
        if new_state == 'answered':
            reasons_to_skip = []
            # Case 1: không phải customer leg
            if not _is_customer_event(payload, rec.callee_number):
                reasons_to_skip.append('not_customer_leg')
            # Case 2: answered đến QUÁ MUỘN sau ringing (voicemail/carrier)
            # 25s = typical voicemail timeout. Real customer thường bắt máy < 15s.
            if rec.start_time:
                # start_time = create_date của record (set default). Stringee fire
                # 'ringing' nhanh nên dùng làm anchor đủ chính xác.
                from datetime import datetime
                ts_ms = payload.get('timestamp_ms')
                if ts_ms:
                    event_dt = datetime.utcfromtimestamp(int(ts_ms) / 1000)
                    delta = (event_dt - rec.start_time).total_seconds()
                    if delta > 25:
                        reasons_to_skip.append(f'late_answered_{delta:.0f}s')
            # Case 3: payload có answerDuration=0 (sometimes Stringee includes it)
            ans_dur = payload.get('answerDuration') or payload.get('answer_duration')
            try:
                if ans_dur is not None and int(ans_dur) == 0:
                    reasons_to_skip.append('zero_answer_duration')
            except (TypeError, ValueError):
                pass
            if reasons_to_skip:
                _logger.info(
                    "Stringee FALSE-positive 'answered' filtered for call %s (actor=%s reasons=%s)",
                    rec.name, payload.get('actor'), ','.join(reasons_to_skip),
                )
                new_state = None

        bumped = self._bump_state(rec.state, new_state)

        vals = {}
        if bumped != rec.state:
            vals['state'] = bumped
        # Chỉ set answer_time khi new_state thật sự được accept (đã pass tất cả filter)
        if (new_state == 'answered'
                and not rec.answer_time):
            # Use the event's own timestamp so the timer starts from when the
            # customer actually picked up (not when our webhook handler ran).
            ts_ms = payload.get('timestamp_ms')
            if ts_ms:
                from datetime import datetime
                vals['answer_time'] = datetime.utcfromtimestamp(int(ts_ms) / 1000)
            else:
                vals['answer_time'] = fields.Datetime.now()
        if bumped in _TERMINAL_STATES and not rec.end_time:
            vals['end_time'] = fields.Datetime.now()
            # ⚡ Ưu tiên answerDuration (TALK time — sau khi KH bắt máy).
            # Nếu = 0 (KH không bắt máy) → fallback duration (ring time).
            # Stringee `duration` = ring + talk; `answerDuration` = chỉ talk.
            try:
                ans_dur = int(payload.get('answerDuration') or 0)
            except (TypeError, ValueError):
                ans_dur = 0
            try:
                total_dur = int(payload.get('duration') or 0)
            except (TypeError, ValueError):
                total_dur = 0
            vals['duration'] = ans_dur if ans_dur > 0 else total_dur
            cause = (payload.get('endCallCause') or payload.get('reason')
                     or payload.get('hangupReason') or payload.get('sipCode'))
            if cause:
                vals['hangup_cause'] = str(cause)
            # CRITICAL: nếu terminal + KH KHÔNG bắt máy thật (answerDuration=0)
            # → CLEAR answer_time để UI không tiếp tục đếm giây "Đang gọi 0:XX".
            # Đây là case Stringee fire fake 'answered' rồi mới ended với 0s.
            try:
                real_ans_dur = int(payload.get('answerDuration') or 0)
            except (TypeError, ValueError):
                real_ans_dur = 0
            if real_ans_dur <= 0 and rec.answer_time:
                vals['answer_time'] = False
                _logger.info(
                    "Clear answer_time on terminal for %s (answerDuration=0 → KH chưa bắt máy thật)",
                    rec.name,
                )
        # Repair from/to if they were stored as dict-strings
        if from_phone and (not rec.caller_number or rec.caller_number.startswith('{')):
            vals['caller_number'] = from_phone
        if to_phone and (not rec.callee_number or rec.callee_number.startswith('{')):
            vals['callee_number'] = to_phone

        # Append to raw_events (capped)
        history = []
        if rec.raw_events:
            try:
                history = json.loads(rec.raw_events)
            except ValueError:
                history = []
        history.append(payload)
        if len(history) > 50:
            history = history[-50:]
        vals['raw_events'] = json.dumps(history, ensure_ascii=False, default=str)

        # Recording URL may arrive in a recording event
        if payload.get('recording_url') and not rec.recording_url:
            vals['recording_url'] = payload['recording_url']
        if payload.get('recording_id') and not rec.recording_id:
            vals['recording_id'] = payload['recording_id']

        if vals:
            rec.write(vals)
        # Try eager recording fetch on terminal state
        if bumped in _TERMINAL_STATES and not rec.recording_attachment_id:
            try:
                rec._download_recording()
            except Exception:
                _logger.warning("Eager recording fetch failed for %s", rec.name, exc_info=True)
        return rec

    @staticmethod
    def _event_to_state(call_status, payload):
        """Map Stringee `call_status` → our state.

        Stringee call_status values seen: created, ringing, answered, ended
        For ended, refine using answerDuration + endCallCause.
        """
        if not call_status:
            return None
        s = str(call_status).lower()
        if s in ('created', 'calling', 'initiated'):
            return 'initiated'
        if s == 'ringing':
            return 'ringing'
        if s == 'answered':
            return 'answered'
        if s == 'busy':
            return 'busy'
        if s in ('ended', 'end'):
            answer_dur = payload.get('answerDuration') or payload.get('answer_duration') or 0
            cause = (payload.get('endCallCause') or '').upper()
            ended_by = (payload.get('endedBy') or '').upper()
            try:
                ans = int(answer_dur)
            except (TypeError, ValueError):
                ans = 0
            if ans <= 0:
                # Never answered. Distinguish by cause when possible.
                if cause == 'BUSY' or 'BUSY' in cause:
                    return 'busy'
                if cause in ('DECLINED', 'CALL_REJECT', 'REJECTED', 'CALLEE_REJECT'):
                    return 'declined'
                if cause in ('CALL_CANCEL', 'CANCEL', 'CANCELLED', 'REST_API_STOP'):
                    return 'cancelled'
                if cause in ('NO_ANSWER', 'TIMEOUT', 'NOT_ANSWER'):
                    return 'no_answer'
                # When endedBy=EXTERNAL with no clear cause, customer hung up
                # while ringing → treat as declined.
                if ended_by == 'EXTERNAL':
                    return 'declined'
                return 'no_answer' if cause != 'USER_END_CALL' else 'ended'
            return 'ended'
        if s in ('failed', 'error'):
            return 'failed'
        return None

    # ---------- Recording download ----------

    def _vd_audio_seconds(self, raw):
        """Đo ĐỘ DÀI THẬT của file ghi âm (giây) bằng ffprobe.

        Lý do (2026-06-11): Stringee KHÔNG gửi answerDuration/duration về webhook
        (payload rỗng) → field `duration` kẹt = 0 dù cuộc gọi có nói chuyện thật.
        Độ dài file ghi âm mới là con số đúng → dùng nó cho `duration`.
        Trả 0 nếu không đo được (ffprobe thiếu / file lỗi)."""
        if not raw:
            return 0
        import subprocess
        import tempfile
        import os as _os
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(raw)
                path = f.name
            out = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'csv=p=0', path],
                capture_output=True, timeout=20,
            )
            val = (out.stdout or b'').decode().strip()
            return int(round(float(val))) if val else 0
        except Exception:
            _logger.warning("ffprobe duration failed for %s", self.name, exc_info=True)
            return 0
        finally:
            if path:
                try:
                    _os.unlink(path)
                except OSError:
                    pass

    def _download_recording(self):
        """Download the call's recording from Stringee REST and attach it.

        Endpoint (per official docs):
            GET https://api.stringee.com/v1/call/recording/{RECORD_ID}
            Header: X-STRINGEE-AUTH: <JWT REST token>
        Ref: https://developer.stringee.com/docs/rest-api-reference/call-rest-api-download-recorded-file
        """
        self.ensure_one()
        if self.recording_attachment_id:
            return self.recording_attachment_id
        if not self.name:
            _logger.info("Recording download skipped: no call_id for record %s", self.id)
            return False
        # Stringee accepts call_id at this endpoint; recording_id (if Stringee
        # sent a different one via webhook) takes priority.
        rid = self.recording_id or self.name
        url = f'{_STRINGEE_API}/v1/call/recording/{rid}'
        try:
            resp = requests.get(
                url,
                headers={'X-STRINGEE-AUTH': self.env['stringee.jwt'].gen_rest_token()},
                timeout=_TIMEOUT,
            )
        except Exception:
            _logger.warning("Recording download network error for %s", self.name, exc_info=True)
            return False
        # Stringee response codes:
        #   200 + audio bytes: OK
        #   200 nhưng size < 500: recording đang process (chưa sẵn sàng)
        #   400 (empty/{"r":N}): call_id không có recording (Stringee không record call này)
        #   401: JWT sai/hết hạn
        #   404: recording đã bị xoá / hết retention
        #   429: rate limit (30 req/period) — đợi 'retry-after' header
        if resp.status_code == 429:
            retry_after = resp.headers.get('retry-after', '?')
            _logger.warning(
                "Recording RATE LIMITED for %s (retry after %ss)",
                self.name, retry_after,
            )
            return False
        if resp.status_code != 200:
            ct = resp.headers.get('Content-Type', '')
            body = resp.text[:500] if 'json' in ct or 'text' in ct else f'<binary {len(resp.content)}B>'
            _logger.info(
                "Recording download FAILED for %s: url=%s status=%s body=%s headers=%s",
                self.name, url, resp.status_code, body,
                dict((k, resp.headers[k]) for k in resp.headers if k.lower().startswith(('x-', 'stringee', 'retry'))),
            )
            return False
        if len(resp.content) < 500:
            _logger.info(
                "Recording NOT READY for %s (size=%sB) — Stringee đang process, retry sau",
                self.name, len(resp.content),
            )
            return False
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'recording_{rid}.mp3',
            'type': 'binary',
            'raw': resp.content,
            'res_model': 'stringee.call',
            'res_id': self.id,
            'mimetype': 'audio/mpeg',
        })
        rec_vals = {
            'recording_url': url,
            'recording_id': rid,
            'recording_attachment_id': attachment.id,
        }
        # Stringee không gửi thời lượng → đo từ chính file ghi âm (đúng thực tế).
        secs = self._vd_audio_seconds(resp.content)
        if secs > 0:
            rec_vals['duration'] = secs
        self.write(rec_vals)
        _logger.info("Recording DOWNLOADED for %s: %sB → attachment %s (dur=%ss)",
                     self.name, len(resp.content), attachment.id, secs)
        return attachment

    @api.model
    def _vd_backfill_durations(self, limit=5000):
        """Backfill `duration` từ độ dài file ghi âm cho các cuộc cũ (duration=0).
        Chạy 1 lần qua odoo shell sau khi deploy. Trả số bản ghi đã cập nhật."""
        recs = self.search([
            ('recording_attachment_id', '!=', False),
            ('duration', '<=', 0),
        ], limit=limit)
        n = 0
        for rec in recs:
            att = rec.recording_attachment_id
            secs = rec._vd_audio_seconds(att.raw if att else None)
            if secs > 0:
                rec.duration = secs
                n += 1
        _logger.info("Backfill recording durations: updated %s/%s", n, len(recs))
        return n

    def action_download_recording(self):
        """🎵 Button: Force-retry download recording từ Stringee.
        Hiển thị notification nếu fail để user biết lý do."""
        self.ensure_one()
        result = self._download_recording()
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Đã tải bản ghi',
                    'message': f'File ghi âm của cuộc gọi {self.name} đã được tải về.',
                    'type': 'success',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '⚠️ Chưa tải được bản ghi',
                'message': (
                    'Stringee chưa trả về file ghi âm. Lý do thường gặp:\n'
                    '• Project chưa bật "Recording" ở Stringee Dashboard\n'
                    '• Cuộc gọi quá ngắn / không answered → không có recording\n'
                    '• Recording đang được process (đợi 1-2 phút rồi thử lại)\n'
                    '• Recording đã hết retention (>30 ngày)'
                ),
                'type': 'warning',
                'sticky': True,
            },
        }

    @api.model
    def cron_retry_recording_download(self):
        """Retry download chỉ cho calls Stringee đã CONFIRM có recording
        (recording_url được set bởi webhook). Tránh spam API request cho
        calls không có recording → đỡ hit rate limit 429."""
        candidates = self.search([
            ('state', 'in', list(_TERMINAL_STATES)),
            ('duration', '>', 0),
            ('recording_url', '!=', False),         # Stringee đã thông báo có
            ('recording_attachment_id', '=', False), # nhưng chưa tải về
            ('create_date', '>', fields.Datetime.now() - timedelta(days=2)),  # chỉ retry call < 48h
        ], limit=20, order='create_date desc')
        _logger.info("Cron retry recording download: %s candidates", len(candidates))
        for rec in candidates:
            try:
                rec._download_recording()
                self.env.cr.commit()
            except Exception:
                _logger.exception("Retry download failed for %s", rec.name)
                self.env.cr.rollback()

    @api.model
    def cron_finalize_stale_calls(self):
        """Chặn UI kẹt khi Stringee không gửi event ended (webhook miss).
        Stringee SCCO timeout = 50s nên ringing > 70s là bất thường.
        Call answered > 30 phút mà chưa end là bất thường (cuộc sales thường <15ph).

        Run every 1 minute (xem ir_cron.xml).
        """
        now = fields.Datetime.now()

        # (1) Pre-answered states kẹt > 60s → no_answer (Stringee timeout=50 + 10s buffer)
        ringing_cutoff = now - timedelta(seconds=60)
        stale_ringing = self.search([
            ('state', 'in', ['draft', 'initiated', 'ringing']),
            ('create_date', '<', ringing_cutoff),
        ], limit=100)
        for call in stale_ringing:
            _logger.info(
                "Stringee stale-RINGING finalize: id=%s name=%s state=%s create=%s",
                call.id, call.name, call.state, call.create_date,
            )
            try:
                call.write({
                    'state': 'no_answer',
                    'end_time': now,
                    'hangup_cause': 'STALE_AUTO_FINALIZE',
                })
                self.env.cr.commit()
            except Exception:
                _logger.exception("Stale ringing finalize failed for %s", call.id)
                self.env.cr.rollback()

        # (2) Answered nhưng không có end_time + answer_time > 10 phút → ended
        # 10 phút đủ rộng cho cuộc sales thực, đủ ngắn để cleanup UI nhanh.
        answered_cutoff = now - timedelta(minutes=10)
        stale_answered = self.search([
            ('state', '=', 'answered'),
            ('end_time', '=', False),
            '|',
                ('answer_time', '<', answered_cutoff),
                '&', ('answer_time', '=', False), ('create_date', '<', answered_cutoff),
        ], limit=100)
        for call in stale_answered:
            _logger.info(
                "Stringee stale-ANSWERED finalize: id=%s name=%s answer=%s create=%s",
                call.id, call.name, call.answer_time, call.create_date,
            )
            try:
                call.write({
                    'state': 'ended',
                    'end_time': now,
                    'hangup_cause': 'STALE_ANSWERED_AUTO_FINALIZE',
                })
                self.env.cr.commit()
            except Exception:
                _logger.exception("Stale answered finalize failed for %s", call.id)
                self.env.cr.rollback()
