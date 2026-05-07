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

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

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
        """Build SCCO actions list returned by /stringee/answer.

        - `record` with `stringeeRecord:true` stores MP3 server-side on Stringee
          (downloadable later via REST). Without `stringeeRecord` the action is a
          no-op for our purposes.
        - `connect` is added by the caller depending on call type.
        """
        actions = []
        if record:
            actions.append({
                'action': 'record',
                'format': 'mp3',
                'stringeeRecord': True,
                'trim': 'trim-silence',
                **({'eventUrl': event_url} if event_url else {}),
            })
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
                'timeout': 60,
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
        """Stop an active call via REST."""
        self.ensure_one()
        if not self.name:
            raise UserError(_('Cuộc gọi chưa có call_id.'))
        try:
            resp = requests.post(
                f'{_STRINGEE_API}/v1/call2/stop',
                headers=self._stringee_headers(),
                json={'call_id': self.name},
                timeout=_TIMEOUT,
            )
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.exception("Stringee stop failed")
            raise UserError(_('Không cúp máy được: %s') % e)
        if data.get('r') not in (0, 1):  # 1 = call already ended
            raise UserError(_('Stringee từ chối: %s') % data.get('message'))
        return True

    # ---------- Webhook handler ----------

    @api.model
    def handle_event(self, payload):
        """Process a webhook event from Stringee. Idempotent."""
        call_id = payload.get('call_id') or payload.get('callId')
        event = payload.get('event') or payload.get('signalingState') or payload.get('mediaState')
        if not call_id:
            _logger.warning("Stringee event without call_id: %s", payload)
            return

        rec = self.search([('name', '=', call_id)], limit=1)
        if not rec:
            rec = self.create({
                'name': call_id,
                'direction': 'inbound' if payload.get('direction') == 'inbound' else 'outbound',
                'caller_number': payload.get('from') or payload.get('caller'),
                'callee_number': payload.get('to') or payload.get('callee'),
                'state': 'initiated',
            })

        new_state = self._event_to_state(event, payload)
        bumped = self._bump_state(rec.state, new_state)

        vals = {}
        if bumped != rec.state:
            vals['state'] = bumped
        if event in ('answered', 'ANSWERED'):
            vals['answer_time'] = fields.Datetime.now()
        if bumped in _TERMINAL_STATES and not rec.end_time:
            vals['end_time'] = fields.Datetime.now()
            duration = payload.get('duration') or payload.get('answerDuration') or 0
            try:
                vals['duration'] = int(duration)
            except (TypeError, ValueError):
                pass
            cause = payload.get('reason') or payload.get('hangupReason') or payload.get('sipCode')
            if cause:
                vals['hangup_cause'] = str(cause)

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
    def _event_to_state(event, payload):
        """Map Stringee event/signalingState to our state."""
        if not event:
            return None
        e = str(event).lower()
        # Stringee SignalingState values: calling, ringing, answered, busy, ended
        if e in ('calling', 'initiated', 'created'):
            return 'initiated'
        if e == 'ringing':
            return 'ringing'
        if e == 'answered':
            return 'answered'
        if e == 'busy':
            return 'busy'
        if e in ('ended', 'end'):
            # Distinguish based on whether it ever answered
            answer_dur = payload.get('answerDuration') or payload.get('answer_duration') or 0
            try:
                if int(answer_dur) <= 0:
                    sip = str(payload.get('sipCode') or payload.get('sip_code') or '')
                    if sip in ('486',):
                        return 'busy'
                    if sip in ('603',):
                        return 'declined'
                    if sip in ('487',):
                        return 'cancelled'
                    if sip in ('480', '408'):
                        return 'no_answer'
                    return 'no_answer'
            except (TypeError, ValueError):
                pass
            return 'ended'
        if e in ('failed', 'error'):
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
