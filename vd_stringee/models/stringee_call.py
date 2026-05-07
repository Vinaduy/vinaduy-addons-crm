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
    if digits.startswith(default_country):
        return digits
    if digits.startswith('0'):
        return default_country + digits[1:]
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
        """
        actions = []
        if record:
            action = {'action': 'record', 'format': 'mp3'}
            if event_url:
                action['eventUrl'] = event_url
            actions.append(action)
        return actions

    # ---------- Outbound (REST callout) ----------

    def action_callout(self):
        """Trigger an outbound call via REST. Server-side initiated."""
        self.ensure_one()
        if not self.callee_number:
            raise UserError(_('Thiếu số đến.'))
        Param = self.env['ir.config_parameter'].sudo()
        from_number = _to_stringee_number(Param.get_param('vd_stringee.from_number'))
        callee_e164 = _to_stringee_number(self.callee_number)
        record = (Param.get_param('vd_stringee.record_calls') or 'True') in ('True', 'true', '1')
        if not from_number:
            raise UserError(_('Chưa cấu hình "From Number".'))
        if not callee_e164:
            raise UserError(_('Số gọi đến không hợp lệ.'))
        base_url = (Param.get_param('web.base.url') or '').rstrip('/')

        actions = self._scco_actions(record=record, event_url=f'{base_url}/stringee/recording_event') + [
            {
                'action': 'connect',
                'from': {'type': 'external', 'number': from_number, 'alias': from_number},
                'to': [{'type': 'external', 'number': callee_e164, 'alias': callee_e164}],
                'maxConnectTime': -1,
                'timeout': 50,        # ring tối đa 50s nếu KH không bắt máy
                'dialAttempts': 1,    # KHÔNG auto-redial
                'retries': 0,         # phòng trường hợp Stringee dùng tên khác
                'eventUrl': f'{base_url}/stringee/event',
            },
        ]
        body = {
            'from': {'type': 'external', 'number': from_number, 'alias': from_number},
            'to': [{'type': 'external', 'number': callee_e164, 'alias': callee_e164}],
            'actions': actions,
        }
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
    def make_call(self, callee_number, partner_id=None, user_id=None):
        """Create call record and trigger callout. Returns the record."""
        rec = self.create({
            'callee_number': callee_number,
            'partner_id': partner_id,
            'user_id': user_id or self.env.user.id,
            'direction': 'outbound',
        })
        rec.action_callout()
        return rec

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
        from_phone = _phone_field(payload.get('from') or payload.get('caller'))
        to_phone = _phone_field(payload.get('to') or payload.get('callee'))
        is_outbound = (payload.get('direction') or '').upper() == 'OUTBOUND'

        rec = self.search([('name', '=', call_id)], limit=1)
        # If no record yet, try to claim a recent same-direction stub created by
        # action_callout (before the Stringee callId came back).
        if not rec and is_outbound and to_phone:
            stub = self.search([
                ('callee_number', '=', to_phone),
                ('name', '=', False),
                ('direction', '=', 'outbound'),
                ('create_date', '>', fields.Datetime.now() - timedelta(seconds=60)),
            ], limit=1, order='create_date desc')
            if stub:
                stub.write({'name': call_id})
                rec = stub
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

        # Ignore 'answered' events that don't come from the customer leg.
        # Stringee call2 (IVR mode) fires duplicate 'answered' events for
        # the bridge/from-number leg; trusting them would start the timer
        # before the customer has actually picked up.
        if new_state == 'answered' and not _is_customer_event(payload, rec.callee_number):
            _logger.info("Ignored non-customer 'answered' event for call %s (actor=%s)",
                         rec.name, payload.get('actor'))
            new_state = None

        bumped = self._bump_state(rec.state, new_state)

        vals = {}
        if bumped != rec.state:
            vals['state'] = bumped
        if (call_status == 'answered'
                and _is_customer_event(payload, rec.callee_number)
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
            duration = payload.get('duration') or payload.get('answerDuration') or 0
            try:
                vals['duration'] = int(duration)
            except (TypeError, ValueError):
                pass
            cause = (payload.get('endCallCause') or payload.get('reason')
                     or payload.get('hangupReason') or payload.get('sipCode'))
            if cause:
                vals['hangup_cause'] = str(cause)
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

    def _download_recording(self):
        """Download the call's recording from Stringee REST and attach it."""
        self.ensure_one()
        if self.recording_attachment_id:
            return self.recording_attachment_id
        if not self.name:
            return False
        # Stringee accepts call_id at this endpoint; recording_id also works.
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
        if resp.status_code != 200 or len(resp.content) < 500:
            _logger.info(
                "Recording not ready for %s (status=%s, size=%s)",
                self.name, resp.status_code, len(resp.content),
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
        self.write({
            'recording_url': url,
            'recording_id': rid,
            'recording_attachment_id': attachment.id,
        })
        return attachment

    @api.model
    def cron_retry_recording_download(self):
        """Pick up calls whose recording wasn't downloaded yet."""
        candidates = self.search([
            ('state', 'in', list(_TERMINAL_STATES)),
            ('duration', '>', 0),
            ('recording_attachment_id', '=', False),
        ], limit=50, order='create_date desc')
        for rec in candidates:
            try:
                rec._download_recording()
                self.env.cr.commit()
            except Exception:
                _logger.exception("Retry download failed for %s", rec.name)
                self.env.cr.rollback()
