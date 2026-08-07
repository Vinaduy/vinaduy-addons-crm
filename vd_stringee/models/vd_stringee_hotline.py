"""Pool số tổng đài Stringee — admin quản lý, assign cho từng NV.

Mỗi NV chỉ dùng 1 hotline (res.users.stringee_from_number_id).
Khi NV gọi ra:
- Ưu tiên dùng số hotline assign cho NV
- Fallback global config 'vd_stringee.from_number' nếu NV chưa assign

Đặt model trong vd_stringee để không phụ thuộc vd_crm_lead.
"""
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

# Thứ tự + label cột nhà mạng hiển thị trên bảng kéo-thả.
_CARRIER_ORDER = [
    ('viettel', 'Viettel'),
    ('mobi', 'MobiFone'),
    ('vina', 'Vinaphone'),
    ('vietnamobile', 'Vietnamobile'),
    ('itelecom', 'iTel'),
    ('gmobile', 'Gmobile'),
    ('other', 'Số cố định'),
]


def _digits_only(s):
    return ''.join(c for c in (s or '') if c.isdigit())


# Map đầu số (prefix 2 chữ số national, đã bỏ 0/84) → nhà mạng.
# Nguồn: quy hoạch số di động VN sau chuyển đổi 11→10 số.
_CARRIER_PREFIX = {
    'viettel': {'96', '97', '98', '86', '32', '33', '34', '35', '36', '37', '38', '39'},
    'vina':    {'91', '94', '88', '81', '82', '83', '84', '85'},
    'mobi':    {'90', '93', '89', '70', '76', '77', '78', '79'},
    'vietnamobile': {'92', '52', '56', '58'},
    'gmobile': {'99', '59'},
    'itelecom': {'87'},
}


def vd_carrier_from_number(number):
    """Suy nhà mạng từ số điện thoại theo đầu số. Trả carrier code hoặc 'other'.
    Chuẩn hoá: bỏ ký tự lạ, bỏ '84'/'0' đầu để lấy prefix national 2 chữ số."""
    d = _digits_only(number)
    if not d:
        return 'other'
    if d.startswith('84'):
        nat = d[2:]
    elif d.startswith('0'):
        nat = d[1:]
    else:
        nat = d
    pref = nat[:2]
    for carrier, prefixes in _CARRIER_PREFIX.items():
        if pref in prefixes:
            return carrier
    return 'other'


class VdStringeeHotline(models.Model):
    _name = 'vd.stringee.hotline'
    _description = 'Số tổng đài Stringee'
    _order = 'team_label, carrier, name'

    name = fields.Char(
        string='Tên gọi', required=True,
        help='Label nội bộ. Vd: "HCM1 - Viettel hotline".',
    )
    number = fields.Char(
        string='Số tổng đài', required=True,
        help='Số phone đã mua trên Stringee (format E.164, vd: 84917690625).',
    )
    carrier = fields.Selection([
        ('viettel', 'Viettel'),
        ('mobi', 'MobiFone'),
        ('vina', 'Vinaphone'),
        ('vietnamobile', 'Vietnamobile'),
        ('gmobile', 'Gmobile'),
        ('itelecom', 'iTel'),
        ('other', 'Khác'),
    ], required=True, default='viettel', string='Nhà mạng')
    team_label = fields.Char(
        string='Team',
        help='HCM1/HCM2/HN/QN... — chỉ để admin filter, không ràng buộc logic.',
    )
    note = fields.Text(string='Ghi chú nội bộ')
    active = fields.Boolean(default=True)
    # Admin ÉP đánh dấu số CÒN SỐNG (xanh) dù lịch sử gọi chưa có/đứt — dùng cho
    # số mới gắn SIM còn hoạt động nhưng chưa phát sinh cuộc nối trong hệ thống.
    vd_force_alive = fields.Boolean(
        string='Đánh dấu còn sống (ép xanh)', default=False,
        help='Bật: số luôn hiện CÒN SỐNG trên bảng kho số + được tính khi "Chia số", '
             'bất kể lịch sử cuộc gọi. Dùng cho số mới/SIM còn sống chưa có cuộc nối.',
    )
    # Sức khoẻ số — cron _vd_cron_sync_hotline_health ghi định kỳ. Nguồn:
    # stringee.call._vd_numbers_stats (alive/dead/unused theo raw_events đổ chuông,
    # KHÔNG dùng duration). Số 'dead' (không vd_force_alive) bị TỰ GỠ khỏi mọi NV
    # + chặn gán lại tới khi đổ chuông trở lại (user spec 2026-06-09).
    vd_health = fields.Selection([
        ('alive', 'Còn sống'),
        ('dead', 'CHẾT'),
        ('unused', 'Chưa dùng'),
    ], string='Sức khoẻ số', default='unused', readonly=True, copy=False, index=True)
    vd_health_at = fields.Datetime(
        string='Cập nhật sức khoẻ lúc', readonly=True, copy=False)

    # Legacy: số đơn cũ (1 NV = 1 số). Giữ để tương thích + migration.
    user_ids = fields.One2many(
        'res.users', 'stringee_from_number_id', string='NV (số đơn cũ)',
    )
    # Gán theo mạng (mới): 1 NV có nhiều số (mỗi mạng 1), 1 số dùng chung nhiều NV.
    assigned_user_ids = fields.Many2many(
        'res.users', 'vd_stringee_hotline_user_rel', 'hotline_id', 'user_id',
        string='NV được gán',
    )
    user_count = fields.Integer(
        string='Số NV dùng', compute='_compute_user_count',
    )
    assigned_user_names = fields.Char(
        string='NV đã gán', compute='_compute_assigned_user_names',
        help='Danh sách NV đang dùng số này (1 số có thể gán cho nhiều NV).',
    )

    @api.depends('assigned_user_ids', 'assigned_user_ids.name')
    def _compute_assigned_user_names(self):
        for rec in self:
            rec.assigned_user_names = ', '.join(
                rec.assigned_user_ids.sorted('name').mapped('name')
            ) or '—'

    _sql_constraints = [
        ('number_unique', 'unique(number)',
         'Số tổng đài này đã được tạo trước đó — kiểm tra lại danh sách.'),
    ]

    @api.depends('assigned_user_ids')
    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.assigned_user_ids)

    @api.constrains('number')
    def _check_number_e164(self):
        for rec in self:
            digits = _digits_only(rec.number)
            if len(digits) < 9:
                raise ValidationError(_(
                    'Số tổng đài "%s" không hợp lệ — cần ít nhất 9 chữ số.'
                ) % rec.number)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number'):
                # Normalize: chỉ giữ chữ số
                vals['number'] = _digits_only(vals['number'])
                # Auto phân loại nhà mạng theo đầu số (user spec 2026-06-01):
                # admin không cần tự chọn — đầu số là nguồn chuẩn.
                vals['carrier'] = vd_carrier_from_number(vals['number'])
        return super().create(vals_list)

    def write(self, vals):
        if 'number' in vals and vals['number']:
            vals['number'] = _digits_only(vals['number'])
            # Số đổi → tự cập nhật lại nhà mạng theo đầu số mới.
            vals['carrier'] = vd_carrier_from_number(vals['number'])
        return super().write(vals)

    def _vd_is_dead(self):
        """True nếu số coi như CHẾT (chặn gọi ra + chặn gán). vd_force_alive
        (admin ép xanh) luôn được coi an toàn."""
        self.ensure_one()
        return self.vd_health == 'dead' and not self.vd_force_alive

    @api.model
    def _vd_cron_sync_hotline_health(self):
        """Cron (~1h): cập nhật vd_health mọi hotline + TỰ GỠ số CHẾT khỏi mọi NV.

        Nguồn health: stringee.call._vd_numbers_stats (alive/dead/unused theo
        raw_events đổ chuông). Số 'dead' (không vd_force_alive) → bỏ khỏi
        assigned_user_ids (m2m) + user_ids (legacy 1-1) → NV chỉ còn gọi bằng số
        sống. Khi số đổ chuông trở lại → health về 'alive', admin chia lại qua
        bảng kho số (đã lọc số sống). User spec 2026-06-09: chỉ gỡ + báo admin,
        KHÔNG tự cấp số thay.
        """
        hotlines = self.with_context(active_test=False).search([])
        if not hotlines:
            return True
        Call = self.env['stringee.call']
        stats = Call._vd_numbers_stats(hotlines.mapped('number'))
        now = fields.Datetime.now()
        stripped = []          # [(số, [tên NV bị gỡ])] để log + gán bù
        for h in hotlines:
            health = (stats.get(h.number) or {}).get('health') or 'unused'
            # ===== ĐÃ CHẾT THÌ Ở LẠI CHẾT (user spec 2026-08-07) =====
            # Trước đây số bị chặn chỉ cần NẰM IM vài ngày là cửa sổ đánh giá
            # rỗng → tự chấm 'alive' → lại chia cho NV → NV gọi vào hư không →
            # chết lại → gỡ lại. Nay muốn sống lại phải có cuộc ĐỔ CHUÔNG THẬT
            # phát sinh SAU mốc chấm chết, hoặc admin ép xanh / chốt tay sau khi
            # gọi thử.
            if h.vd_health == 'dead' and health != 'dead' and not h.vd_force_alive:
                if not Call._vd_has_ring_after(h.number, h.vd_health_at):
                    health = 'dead'
            vals = {'vd_health': health}
            if health != h.vd_health:
                vals['vd_health_at'] = now
            # ===== BẰNG CHỨNG THẮNG CỜ "ÉP XANH" (user 2026-08-07) =====
            # Ép xanh sinh ra cho số MỚI chưa có lịch sử gọi. Nhưng nó đang bị
            # dùng như tấm khiên vĩnh viễn: 84917690658 ép xanh, 0 đổ chuông từ
            # 23/07 mà NV vẫn phải cầm gọi. Nay khi đã đủ bằng chứng chết (chuỗi
            # dài, nhiều ngày/nhiều NV) thì TỰ TẮT ép xanh.
            if health == 'dead' and h.vd_force_alive:
                vals['vd_force_alive'] = False
                _logger.warning(
                    "[VD hotline] %s: tắt ÉP XANH vì đủ bằng chứng chết.", h.number)
            h.write(vals)
            # Số CHẾT (không ép xanh) → gỡ khỏi tất cả NV ngay.
            if health == 'dead' and not h.vd_force_alive:
                users = h.assigned_user_ids
                if users:
                    stripped.append((h, users.mapped('name')))
                    for u in users:
                        self._vd_replace_dead_number(u, h)
                if h.assigned_user_ids:
                    h.assigned_user_ids = [(5, 0, 0)]
                if h.user_ids:
                    h.user_ids.write({'stringee_from_number_id': False})
        for h, names in stripped:
            _logger.warning(
                "[VD hotline] GỠ SỐ CHẾT %s (%s) khỏi %d NV: %s",
                h.number, h.carrier, len(names), ', '.join(names))
        return True

    def _vd_replace_dead_number(self, user, dead_hotline):
        """Gỡ số chết thì GÁN BÙ ngay số cùng mạng đang sống (user spec
        2026-08-07). Trước đây chỉ gỡ rồi thôi → NV mất kênh gọi mà không ai
        biết, có người ngồi bấm 30 phút không ra cuộc nào. Chọn số ít NV dùng
        nhất cho đỡ dồn tải; không còn số sống cùng mạng thì ghi cảnh báo."""
        carrier = dead_hotline.carrier
        alive = self.search([
            ('active', '=', True), ('carrier', '=', carrier),
            ('id', '!=', dead_hotline.id),
        ]).filtered(lambda x: not x._vd_is_dead())
        if not alive:
            _logger.warning(
                "[VD hotline] %s mất số %s (%s) mà KHO KHÔNG CÒN SỐ SỐNG cùng mạng.",
                user.name, dead_hotline.number, carrier)
            return False
        target = min(alive, key=lambda x: (len(x.assigned_user_ids), x.number))
        user.sudo().stringee_hotline_ids = [(4, target.id)]
        _logger.warning(
            "[VD hotline] %s: thay số chết %s -> %s (%s).",
            user.name, dead_hotline.number, target.number, carrier)
        return True

    # ========================= GỌI THỬ 1 SỐ (admin) =========================
    # Bệnh trước đó: số bị nhà mạng chặn → 4 ngày không ai gọi → cửa sổ đánh giá
    # RỖNG → tự chấm 'alive' trở lại → chia cho NV → chết tiếp → cron gỡ. Admin
    # không có cách nào KIỂM CHỨNG số còn sống hay không ngoài việc thả cho NV
    # gọi thật. Bộ 3 method dưới cho admin tự gọi thử 1 số bất kỳ rồi CHỐT kết quả.
    @api.model
    def vd_test_call_begin(self, hotline_id):
        """Mốc trước khi gọi thử: trả id cuộc gọi cuối của số này để lát nữa chỉ
        soi những cuộc SINH RA SAU mốc (khỏi nhầm với lịch sử cũ)."""
        self._check_board_access()
        h = self.browse(hotline_id)
        if not h.exists():
            return {'error': 'Không tìm thấy số.'}
        last = self.env['stringee.call'].sudo().search(
            [('caller_number', '=', h.number)], order='id desc', limit=1)
        return {'number': h.number, 'carrier': h.carrier, 'last_id': last.id or 0}

    @api.model
    def vd_number_daily_report(self, hotline_id, days=15):
        """Báo cáo NGÀY của 1 số, neo vào NGÀY ĐỔ CHUÔNG CUỐI CÙNG.

        Vì sao neo kiểu này (user spec 2026-08-07): nhìn 15 ngày cuối theo lịch
        thì số đã chết cả tháng chỉ ra toàn số 0 — vô nghĩa. Neo vào lần đổ
        chuông cuối thì thấy ngay KHOẢNH KHẮC CHẾT: ngày cuối còn chuông, rồi
        các ngày sau gọi rát mà 0 chuông = nhà mạng chặn.

        Cửa sổ: từ ngày đổ chuông cuối → +14 ngày (không quá hôm nay). Nếu chưa
        đủ 15 ngày (số vẫn đang sống) thì lùi mốc đầu về trước cho đủ 15 dòng.
        """
        self._check_board_access()
        h = self.browse(hotline_id)
        if not h.exists():
            return {'rows': [], 'anchor': False}
        n = max(1, int(days or 15))
        # Tính SẴN mọi thứ TRƯỚC cr.execute — query ORM xen giữa execute và
        # fetchall sẽ đè con trỏ làm fetchall rỗng (đã dính bug này 2026-06-09).
        tz = self.env.user.tz or 'Asia/Ho_Chi_Minh'
        today = fields.Date.context_today(self)
        number = h.number
        reached = ("(raw_events ILIKE '%%ringing%%' OR raw_events ILIKE "
                   "'%%answered%%' OR answer_time IS NOT NULL)")
        local_date = ("((create_date AT TIME ZONE 'UTC') AT TIME ZONE %s)::date")
        cr = self.env.cr
        cr.execute(
            "SELECT " + local_date + " AS d, count(*) AS total, "
            "  count(*) FILTER (WHERE " + reached + ") AS ring, "
            "  count(*) FILTER (WHERE answer_time IS NOT NULL) AS answered, "
            "  COALESCE(sum(duration), 0) AS secs "
            "FROM stringee_call "
            "WHERE direction='outbound' AND caller_number = %s "
            "GROUP BY 1 ORDER BY 1",
            [tz, number],
        )
        rows = cr.fetchall()
        if not rows:
            return {'rows': [], 'anchor': False, 'number': number}
        by_day = {r[0]: r for r in rows}
        ring_days = [r[0] for r in rows if r[2]]
        anchor = ring_days[-1] if ring_days else rows[-1][0]
        # Cửa sổ 15 ngày bắt đầu từ mốc; nếu đụng hôm nay thì lùi lại cho đủ.
        start = anchor
        end = min(start + timedelta(days=n - 1), today)
        if (end - start).days < n - 1:
            start = end - timedelta(days=n - 1)
        out = []
        d = start
        while d <= end:
            r = by_day.get(d)
            total = r[1] if r else 0
            ring = r[2] if r else 0
            out.append({
                'date': d.strftime('%d/%m'),
                'dow': ('T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN')[d.weekday()],
                'total': total,
                'ring': ring,
                'answered': r[3] if r else 0,
                'minutes': round((r[4] if r else 0) / 60.0),
                'rate': round(ring * 100.0 / total) if total else 0,
                'is_anchor': d == anchor,
                # Ngày "báo động": có gọi kha khá mà 0 đổ chuông = dấu hiệu bị chặn.
                'bad': bool(total >= 3 and ring == 0),
            })
            d += timedelta(days=1)
        return {
            'rows': out,
            'anchor': anchor.strftime('%d/%m/%Y'),
            'anchor_ring': bool(ring_days),
            'number': number,
        }

    @api.model
    def vd_test_call_candidates(self, hotline_id, limit=24):
        """Gợi ý số KHÁCH CÙNG MẠNG với số đang test (user spec 2026-08-07).

        Test số Viettel thì phải gọi vào số Viettel mới biết nó có bị chặn nội
        mạng hay không — bắt admin tự nhớ số khách nào mạng nào là vô lý. Lọc
        theo ĐẦU SỐ ngay trong SQL (LIKE '09xx%') cho nhanh, khỏi tải cả bảng.
        """
        self._check_board_access()
        h = self.browse(hotline_id)
        if not h.exists():
            return {'carrier': '', 'label': '', 'leads': []}
        label = dict(_CARRIER_ORDER).get(h.carrier, h.carrier)
        prefixes = _CARRIER_PREFIX.get(h.carrier)
        if not prefixes:
            # Số cố định / mạng lạ: không suy được đầu số khách → khỏi gợi ý.
            return {'carrier': h.carrier, 'label': label, 'leads': []}
        # KH lưu SĐT dạng '09xxxxxxxx' (write() đã normalize 84 → 0).
        domain = [('phone', '!=', False)]
        or_terms = ['|'] * (len(prefixes) - 1)
        domain += or_terms + [('phone', '=like', '0%s%%' % p) for p in sorted(prefixes)]
        leads = self.env['crm.lead'].sudo().search(
            domain, order='id desc', limit=int(limit) * 3)
        seen, out = set(), []
        for lead in leads:
            phone = _digits_only(lead.phone)
            if not phone or phone in seen:
                continue
            seen.add(phone)
            out.append({
                'name': lead.partner_name or lead.name or '(KH)',
                'phone': lead.phone,
                'user': lead.user_id.name or '',
            })
            if len(out) >= int(limit):
                break
        return {'carrier': h.carrier, 'label': label, 'leads': out}

    @api.model
    def vd_test_call_status(self, hotline_id, last_id=0):
        """Soi cuộc gọi thử vừa bấm. Tiêu chí ĐỔ CHUÔNG dùng ĐÚNG nguồn mà cron
        sức khoẻ dùng (raw_events ringing/answered / answer_time) — KHÔNG dùng
        duration (hay = 0 dù cuộc nối thật)."""
        self._check_board_access()
        h = self.browse(hotline_id)
        if not h.exists():
            return {'error': 'Không tìm thấy số.'}
        call = self.env['stringee.call'].sudo().search([
            ('caller_number', '=', h.number),
            ('id', '>', int(last_id or 0)),
        ], order='id desc', limit=1)
        if not call:
            return {'found': False}
        raw = (call.raw_events or '').lower()
        return {
            'found': True,
            'state': call.state or '',
            'rang': bool(call.answer_time) or 'ringing' in raw or 'answered' in raw,
            'answered': 'answered' in raw or bool(call.answer_time),
            'hangup_cause': call.hangup_cause or '',
            'callee': call.callee_number or '',
        }

    @api.model
    def vd_test_call_verdict(self, hotline_id, rang):
        """Admin CHỐT kết quả gọi thử → ghi thẳng sức khoẻ số.

        - rang=True  → 'alive': số dùng được, bảng kho hết gạch đỏ, chia được ngay.
        - rang=False → 'dead' : cron sẽ gỡ số khỏi mọi NV (không để NV gọi vào
          hư không). Trả kèm danh sách NV đang dùng số để admin biết ai mất số.
        """
        self._check_board_access()
        h = self.browse(hotline_id)
        if not h.exists():
            return {'ok': False, 'message': 'Không tìm thấy số.'}
        users = h.assigned_user_ids.mapped('name')
        # Chốt SỐNG mà hệ thống KHÔNG ghi nhận cuộc đổ chuông nào gần đây → đây
        # là admin khẳng định bằng tai, phải ÉP XANH thì cron mới không chấm chết
        # lại sau 1 tiếng. Có đổ chuông thật rồi thì khỏi ép — số liệu tự nói.
        force = False
        if rang:
            since = fields.Datetime.now() - timedelta(hours=2)
            force = not self.env['stringee.call']._vd_has_ring_after(h.number, since)
        h.write({
            'vd_health': 'alive' if rang else 'dead',
            'vd_health_at': fields.Datetime.now(),
            'vd_force_alive': force,
        })
        if rang:
            msg = 'Đã chốt: %s CÒN SỐNG.' % h.number
            if force:
                msg += (' Hệ thống chưa ghi nhận cuộc đổ chuông nào nên đã ÉP XANH '
                        'theo xác nhận của bạn.')
            return {'ok': True, 'message': msg}
        msg = 'Đã chốt: %s CHẾT.' % h.number
        if users:
            msg += ' Cron sẽ gỡ khỏi %d NV: %s.' % (len(users), ', '.join(users))
        return {'ok': True, 'message': msg}

    # ===================== BẢNG KÉO-THẢ (OWL client action) =====================
    def _check_board_access(self):
        """Chỉ admin / quản lý sale được thao tác bảng phân số."""
        if not (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('sales_team.group_sale_manager')):
            raise AccessError(_('Bạn không có quyền phân bổ số tổng đài.'))

    @api.model
    def _board_call_stats(self, numbers):
        """Thống kê gọi theo (số tổng đài, NV): tổng giây + số cuộc + lần gọi ĐẦU.
        Dùng cho popover hover. Bọc try/except để lỗi thống kê không làm sập bảng."""
        stats = {}
        if not numbers:
            return stats
        try:
            groups = self.env['stringee.call'].read_group(
                [('caller_number', 'in', list(numbers)), ('user_id', '!=', False)],
                ['duration:sum', 'create_date:min'],
                ['caller_number', 'user_id'],
                lazy=False,
            )
            for g in groups:
                uid = g['user_id'][0] if g.get('user_id') else False
                stats[(g['caller_number'], uid)] = {
                    'seconds': g.get('duration') or 0,
                    'count': g.get('__count') or 0,
                    'first': g.get('create_date'),
                }
        except Exception:
            return {}
        return stats

    @api.model
    def get_assignment_board(self):
        """Dữ liệu cho bảng kéo-thả: kho số gom theo mạng + danh sách NV kèm số đã gán.
        Mỗi số kèm 'detail' = NV nào / dùng từ bao giờ / tổng phút gọi / số cuộc."""
        self._check_board_access()
        hotlines = self.search([('active', '=', True)])
        all_numbers = hotlines.mapped('number')
        stats = self._board_call_stats(all_numbers)
        num_stats = self.env['stringee.call']._vd_numbers_stats(all_numbers)
        today = fields.Date.context_today(self)

        def _detail(h):
            rows = []
            for u in h.assigned_user_ids.sorted('name'):
                st = stats.get((h.number, u.id)) or {}
                secs = st.get('seconds') or 0
                first = st.get('first')
                first_date = None
                if first:
                    first_date = (first.date() if hasattr(first, 'date')
                                  else fields.Datetime.to_datetime(first).date())
                rows.append({
                    'user': u.name,
                    'minutes': int(round(secs / 60.0)),
                    'count': st.get('count') or 0,
                    'first': first_date.strftime('%d/%m/%Y') if first_date else '',
                    'days': (today - first_date).days if first_date else None,
                })
            return rows

        def _fmt_hm(secs):
            secs = int(secs or 0)
            h = secs // 3600
            m = (secs % 3600) // 60
            if h:
                return f'{h}h{m:02d}'
            return f'{m} phút'

        by_carrier = {}
        for h in hotlines:
            ns = num_stats.get(h.number) or {}
            by_carrier.setdefault(h.carrier, []).append({
                'id': h.id,
                'number': h.number,
                'name': h.name or '',
                'user_count': len(h.assigned_user_ids),
                'detail': _detail(h),
                # --- Thống kê + sức khoẻ số (cho chip màu + bảng hover) ---
                # force_alive: admin ép xanh dù lịch sử chưa có cuộc nối.
                'health': 'alive' if h.vd_force_alive else (ns.get('health') or 'unused'),
                'total_calls': ns.get('total') or 0,
                'reached': ns.get('reached') or 0,
                'talk_hm': _fmt_hm(ns.get('secs')),
                'first': ns.get('first') or '',
                'last': ns.get('last') or '',
                'active_days': ns.get('active_days') or 0,
                'per_day': ns.get('per_day') or 0,
                # Bằng chứng chấm chết — popover hiện ra để admin tự soi, khỏi
                # phải tin suông vào cái chấm đỏ.
                'streak_calls': ns.get('streak_calls') or 0,
                'streak_days': ns.get('streak_days') or 0,
                'streak_users': ns.get('streak_users') or 0,
                'dead_streak': ns.get('dead_streak') or 0,
            })
        carriers = []
        for code, label in _CARRIER_ORDER:
            nums = by_carrier.get(code)
            if nums:
                carriers.append({
                    'code': code,
                    'label': label,
                    # SỐ CHẾT dồn xuống CUỐI danh sách (user spec 2026-08-07) —
                    # admin nhìn từ trên xuống toàn số dùng được, khỏi phải nhặt.
                    'numbers': sorted(
                        nums, key=lambda x: (x['health'] == 'dead', x['number'])),
                })

        def _eff_health(h):
            return ('alive' if h.vd_force_alive
                    else ((num_stats.get(h.number) or {}).get('health') or 'unused'))

        # Mạng mà CÔNG TY còn ít nhất 1 số SỐNG (để biết NV nào đang thiếu).
        company_alive_carriers = {h.carrier for h in hotlines if _eff_health(h) == 'alive'}

        users = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)], order='name')
        user_list = []
        carrier_labels = dict(_CARRIER_ORDER)
        alerts = []  # NV thiếu số sống theo mạng (user spec 2026-06-09: báo admin)
        for u in users:
            assigned = [
                {'id': h.id, 'number': h.number, 'carrier': h.carrier,
                 'health': _eff_health(h)}
                for h in u.stringee_hotline_ids if h.active
            ]
            assigned.sort(key=lambda x: x['carrier'])
            # Mạng NV đang có số SỐNG; thiếu = công ty có số sống mà NV không có.
            user_alive = {a['carrier'] for a in assigned if a['health'] == 'alive'}
            missing = sorted(company_alive_carriers - user_alive)
            missing_labels = [carrier_labels.get(c, c) for c in missing]
            if missing_labels and not u.vd_no_number_share:
                alerts.append({'user': u.name, 'carriers': missing_labels})
            user_list.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'hotlines': assigned,
                'no_share': bool(u.vd_no_number_share),
                'missing_carriers': missing_labels,
            })
        return {'carriers': carriers, 'users': user_list, 'alerts': alerts}

    @api.model
    def toggle_user_no_share(self, user_id, value):
        """Bật/tắt cờ 'không tham gia chia số' cho 1 NV (từ bảng kho số)."""
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        if user.exists():
            user.vd_no_number_share = bool(value)
        return True

    @api.model
    def distribute_numbers_to_users(self, number_ids, user_ids):
        """Chia ĐỀU các số ĐÃ CHỌN cho các NV ĐÃ CHỌN (popup chia số).

        Gom số theo nhà mạng → round-robin từng mạng cho danh sách NV: mỗi NV
        nhận 1 số/mạng, thay số CÙNG MẠNG đang có. (1 mạng 1 số / NV.)
        """
        self._check_board_access()
        # Chặn gán SỐ CHẾT (user spec 2026-06-09): chỉ chia số active + không chết.
        numbers = self.browse(number_ids or []).filtered(
            lambda h: h.active and not h._vd_is_dead())
        users = self.env['res.users'].browse(user_ids or []).filtered('active')
        if not numbers:
            return {'ok': False, 'message':
                    'Các số đã chọn đều CHẾT (không đổ chuông) hoặc không hợp lệ — '
                    'không chia được. Mở outbound trên Stringee hoặc ép xanh trước.'}
        if not users:
            return {'ok': False, 'message': 'Chưa chọn nhân viên nào.'}
        by_carrier = {}
        for h in numbers.sorted('number'):
            by_carrier.setdefault(h.carrier, []).append(h)
        users_sorted = users.sorted('name')
        for carrier, hs in by_carrier.items():
            n = len(hs)
            for idx, u in enumerate(users_sorted):
                target = hs[idx % n]
                same = u.stringee_hotline_ids.filtered(
                    lambda h: h.active and h.carrier == carrier and h.id != target.id
                )
                cmds = [(3, h.id) for h in same]
                cmds.append((4, target.id))
                u.sudo().stringee_hotline_ids = cmds
        labels = ', '.join(
            dict(_CARRIER_ORDER).get(c, c) for c in by_carrier
        )
        return {'ok': True, 'message':
                'Đã chia %d số (%s) cho %d NV.'
                % (len(numbers), labels, len(users))}

    @api.model
    def distribute_carrier_evenly(self, carrier='viettel'):
        """Chia ĐỀU các số CÒN SỐNG của 1 nhà mạng cho NV đủ điều kiện.

        - NV đủ điều kiện: active, không phải share-user, KHÔNG tick
          vd_no_number_share (admin/quản lý/Thành đã tick sẵn).
        - Số tham gia: hotline active của mạng đó VÀ đang 'alive' (đổ chuông
          gần đây — theo _vd_numbers_stats). Tránh gán số chết.
        - Round-robin: xoá số cũ CÙNG MẠNG của NV đủ điều kiện rồi gán lại đều.
        Trả {'ok', 'message'} để client toast.
        """
        self._check_board_access()
        hotlines = self.search([('active', '=', True), ('carrier', '=', carrier)])
        if not hotlines:
            return {'ok': False, 'message': 'Không có số %s nào trong kho.' % carrier}
        stats = self.env['stringee.call']._vd_numbers_stats(hotlines.mapped('number'))
        alive = hotlines.filtered(
            lambda h: h.vd_force_alive
            or (stats.get(h.number) or {}).get('health') == 'alive'
        )
        if not alive:
            return {'ok': False, 'message':
                    'Không có số %s nào CÒN SỐNG (đổ chuông gần đây) để chia. '
                    'Kiểm tra/mở outbound trên Stringee trước.' % carrier}
        users = self.env['res.users'].search([
            ('share', '=', False), ('active', '=', True),
            ('vd_no_number_share', '=', False),
        ], order='name')
        if not users:
            return {'ok': False, 'message': 'Không có NV đủ điều kiện để chia số.'}

        alive_sorted = alive.sorted('number')
        n_alive = len(alive_sorted)
        for idx, u in enumerate(users):
            target = alive_sorted[idx % n_alive]
            # bỏ mọi số cùng mạng đang gán, gán đúng 1 số target
            same = u.stringee_hotline_ids.filtered(
                lambda h: h.active and h.carrier == carrier and h.id != target.id
            )
            cmds = [(3, h.id) for h in same]
            cmds.append((4, target.id))
            u.sudo().stringee_hotline_ids = cmds
        _lbl = dict(_CARRIER_ORDER).get(carrier, carrier)
        return {'ok': True, 'message':
                'Đã chia đều %d số %s (còn sống) cho %d NV.'
                % (n_alive, _lbl, len(users))}

    @api.model
    def assign_user_hotline(self, user_id, hotline_id):
        """Gán số cho NV. 1 mạng 1 số → bỏ số cùng mạng cũ trước khi gán số mới.

        Trả {'ok', 'message'} — TRƯỚC ĐÂY trả False im lặng khi gặp số chết nên
        admin kéo số vào NV, bảng không báo gì, tưởng xong mà thực ra không ăn
        (user 2026-08-07: NV ngồi gọi cả buổi không có đầu số).
        """
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        hotline = self.browse(hotline_id)
        if not user.exists() or not hotline.exists() or not hotline.active:
            return {'ok': False, 'message': 'Số hoặc nhân viên không hợp lệ.'}
        # Chặn gán SỐ CHẾT (user spec 2026-06-09).
        if hotline._vd_is_dead():
            return {'ok': False, 'message':
                    'KHÔNG gán được: %s đang là SỐ CHẾT (không đổ chuông). '
                    'Bấm nút điện thoại để GỌI THỬ, nếu thật sự còn sống thì '
                    'chốt "Số SỐNG" rồi gán lại.' % hotline.number}
        same_carrier = user.stringee_hotline_ids.filtered(
            lambda h: h.active and h.carrier == hotline.carrier and h.id != hotline.id
        )
        cmds = [(3, h.id) for h in same_carrier]
        cmds.append((4, hotline.id))
        user.stringee_hotline_ids = cmds
        msg = 'Đã gán %s cho %s' % (hotline.number, user.name)
        if same_carrier:
            msg += ' (thay %s)' % ', '.join(same_carrier.mapped('number'))
        return {'ok': True, 'message': msg}

    @api.model
    def unassign_user_hotline(self, user_id, hotline_id):
        """Gỡ 1 số khỏi NV."""
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        if not user.exists():
            return False
        user.stringee_hotline_ids = [(3, hotline_id)]
        return True

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gán NV cho %s') % (self.name or self.number or ''),
            'res_model': 'vd.stringee.hotline.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hotline_id': self.id,
                'active_id': self.id,
                'active_model': 'vd.stringee.hotline',
            },
        }
