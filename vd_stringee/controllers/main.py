"""Stringee public endpoints.

- /stringee/answer            → Stringee fetches SCCO actions (answer URL)
- /stringee/event             → Stringee posts call lifecycle events
- /stringee/recording_event   → Stringee posts recording-ready notifications
- /stringee/click_to_call     → Browser → server: place outbound call
- /stringee/user_token        → Browser → server: get short-lived user JWT
"""
import json
import logging
import time

from psycopg2 import errors as pg_errors

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Lỗi PostgreSQL có thể RETRY an toàn (race condition giữa concurrent updates).
_RETRYABLE_PG_ERRORS = (
    pg_errors.SerializationFailure,
    pg_errors.DeadlockDetected,
)


def _read_payload():
    """Stringee sends JSON; some events arrive as form-encoded. Be lenient."""
    try:
        if request.httprequest.is_json:
            return request.get_json_data()
    except Exception:
        pass
    raw = request.httprequest.get_data(as_text=True) or ''
    if raw.strip().startswith('{'):
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return dict(request.httprequest.values.items())


def _run_with_retry(label, fn, *, max_attempts=4, base_delay=0.1):
    """Chạy ``fn()`` với retry exponential khi gặp SerializationFailure /
    DeadlockDetected.

    Stringee gửi nhiều webhook event (created → ringing → ended) cách nhau ~ms
    cho cùng 1 call_id. 2 process Odoo cùng UPDATE 1 record → PostgreSQL ném
    SerializationFailure. Vì handler idempotent (chỉ ghi state mới), retry an
    toàn — vài ms là đủ để process khác commit xong.

    Trả về kết quả của ``fn()`` hoặc None nếu thất bại sau ``max_attempts``.
    """
    cr = request.env.cr
    for attempt in range(max_attempts):
        try:
            result = fn()
            cr.commit()
            return result
        except _RETRYABLE_PG_ERRORS as e:
            cr.rollback()
            # Reset env cache (records bị invalidate sau rollback)
            request.env.clear()
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)  # 0.1, 0.2, 0.4, 0.8s
                _logger.info(
                    "[Stringee %s] PG retryable error (attempt %d/%d), retry in %.2fs: %s",
                    label, attempt + 1, max_attempts, delay, type(e).__name__,
                )
                time.sleep(delay)
                continue
            _logger.warning(
                "[Stringee %s] giving up after %d retries: %s",
                label, max_attempts, e,
            )
        except Exception:
            cr.rollback()
            _logger.exception("[Stringee %s] handler failed (non-retryable)", label)
            return None
    return None


class StringeeController(http.Controller):

    # ----- SCCO answer URL (public, no auth) -----
    @http.route('/stringee/answer', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def answer_url(self, **kwargs):
        """Return SCCO actions for an inbound or Web-SDK-initiated call.

        Stringee passes from/to/callId as query string. We connect to whatever
        number was dialled and record by default.
        """
        params = dict(request.httprequest.values.items())
        call_id = params.get('callId') or params.get('call_id')
        from_num = params.get('from')
        to_num = params.get('to')

        Param = request.env['ir.config_parameter'].sudo()
        record = (Param.get_param('vd_stringee.record_calls') or 'True') in ('True', 'true', '1')
        base_url = (Param.get_param('web.base.url') or '').rstrip('/')
        from_number = (Param.get_param('vd_stringee.from_number') or '').strip()

        # Pre-create record so the next webhook can find it.
        if call_id:
            Call = request.env['stringee.call'].sudo()
            existing = Call.search([('name', '=', call_id)], limit=1)
            if not existing:
                Call.create({
                    'name': call_id,
                    'caller_number': from_num,
                    'callee_number': to_num,
                    'direction': 'outbound',
                    'state': 'initiated',
                })

        actions = request.env['stringee.call'].sudo()._scco_actions(
            record=record, event_url=f'{base_url}/stringee/recording_event',
        )
        # Connect to PSTN: the dialled number is `to`. If the call origin is a
        # Stringee user (Web SDK), we still bridge to PSTN; from_number sets caller ID.
        if to_num:
            actions.append({
                'action': 'connect',
                'from': {'type': 'external', 'number': from_number or from_num, 'alias': from_number or from_num},
                'to': [{'type': 'external', 'number': to_num, 'alias': to_num}],
                'maxConnectTime': -1,
                'timeout': 60,
                'eventUrl': f'{base_url}/stringee/event',
            })

        return request.make_response(
            json.dumps(actions, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')],
        )

    # ----- Event webhook (public, no auth) -----
    @http.route('/stringee/event', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def event(self, **kwargs):
        payload = _read_payload()
        _logger.info("[Stringee event] %s", payload)

        def _do():
            return request.env['stringee.call'].sudo().handle_event(payload)

        _run_with_retry('event', _do)
        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])

    @http.route('/stringee/recording_event', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def recording_event(self, **kwargs):
        payload = _read_payload()
        _logger.info("[Stringee recording] %s", payload)

        def _do():
            rec = request.env['stringee.call'].sudo().handle_event(payload)
            if rec and not rec.recording_attachment_id:
                rec._download_recording()
            return rec

        _run_with_retry('recording', _do)
        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])

    # ----- Browser → server (authenticated) -----
    @http.route('/stringee/click_to_call', type='json', auth='user')
    def click_to_call(self, callee, partner_id=None):
        """Place an outbound call from the server. Used by buttons in Odoo UI."""
        if not callee:
            return {'error': 'missing callee'}
        rec = request.env['stringee.call'].sudo().make_call(
            callee_number=callee,
            partner_id=int(partner_id) if partner_id else None,
            user_id=request.env.user.id,
        )
        return {
            'id': rec.id,
            'call_id': rec.name,
            'state': rec.state,
        }

    @http.route('/stringee/user_token', type='json', auth='user')
    def user_token(self):
        """Return a short-lived Stringee user token for the current user.

        Empty string if user has no `stringee_user_id` configured.
        """
        user = request.env.user
        if not user.stringee_user_id:
            return {'token': '', 'user_id': '', 'reason': 'no stringee_user_id on user'}
        token = request.env['stringee.jwt'].sudo().gen_user_token(user.stringee_user_id)
        return {'token': token, 'user_id': user.stringee_user_id}
