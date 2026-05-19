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
from datetime import timedelta

from psycopg2 import errors as pg_errors

from odoo import fields, http
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

        ⚠️ DOUBLE-CALL + MIC FIX:
        Stringee fetches answer_url cho MỌI call routed qua project — bao gồm cả
        call originated từ Web SDK (StringeeCall2 trên browser).

        Vấn đề:
        - Web SDK call cần SCCO `connect` action để Stringee biết cách bridge
          browser audio → PSTN. KHÔNG có connect → mic không stream tới KH
          (lỗi 1-way audio).
        - Nhưng connect kiểu `from external → to external` sẽ tạo PSTN leg riêng
          → KH bị reo 2 cuộc (double-call).

        Giải pháp đúng — connect với `from: internal user_id`:
        - Tells Stringee: dùng audio stream của user (browser WebRTC) làm `from`,
          bridge sang external PSTN ở `to`.
        - Stringee KHÔNG dial PSTN riêng cho `from` → không double-call.
        - Audio bridge giữ nguyên → mic NV stream tới KH được.

        Phân loại:
        - `from` match `res_users.stringee_user_id` → Web SDK → connect internal→external.
        - REST callout (stringee.call existing, direction=outbound) → KHÔNG thêm
          connect (body đã có rồi, thêm sẽ double).
        - PSTN inbound (`from` là phone) → connect external→external như cũ.
        """
        params = dict(request.httprequest.values.items())
        call_id = params.get('callId') or params.get('call_id')
        from_num = (params.get('from') or '').strip()
        to_num = (params.get('to') or '').strip()

        Param = request.env['ir.config_parameter'].sudo()
        record = (Param.get_param('vd_stringee.record_calls') or 'True') in ('True', 'true', '1')
        base_url = (Param.get_param('web.base.url') or '').rstrip('/')
        from_number = (Param.get_param('vd_stringee.from_number') or '').strip()

        # === Hotline pool: global config + tất cả vd.stringee.hotline ===
        # Với multi-hotline (mỗi NV 1 số khác nhau theo nhà mạng), từ_num từ
        # Stringee có thể là BẤT KỲ số nào trong pool — không chỉ global.
        import re as _re
        def _digits(s):
            return _re.sub(r'\D', '', s or '')
        hotline_digits_set = set()
        global_digits = _digits(from_number)
        if global_digits:
            hotline_digits_set.add(global_digits)
        for _h in request.env['vd.stringee.hotline'].sudo().search([]):
            _hd = _digits(_h.number)
            if _hd:
                hotline_digits_set.add(_hd)

        Call = request.env['stringee.call'].sudo()
        existing = Call.search([('name', '=', call_id)], limit=1) if call_id else Call.browse()

        # === Web SDK detect TRƯỚC ===
        # JS pass hotline number làm fromNumber → from_num match hotline POOL
        # = Web SDK call. Fallback: from_num có thể là stringee_user_id.
        # Detect TRƯỚC khi check existing để KHÔNG misclassify Web SDK
        # placeholder (do action_call tạo trước) thành REST outbound.
        is_web_sdk_origin = False
        from_num_digits = _digits(from_num)
        if from_num:
            if from_num_digits and from_num_digits in hotline_digits_set:
                is_web_sdk_origin = True
            else:
                user_match = request.env['res.users'].sudo().search([
                    ('stringee_user_id', '=', from_num),
                ], limit=1)
                is_web_sdk_origin = bool(user_match)

        # Effective from-number để dùng làm caller-id trong SCCO connect:
        # nếu from_num match 1 hotline trong pool → dùng chính hotline đó
        # (NV này dùng số riêng), else fallback global.
        effective_from = from_number
        if from_num_digits and from_num_digits in hotline_digits_set:
            effective_from = from_num_digits

        # === Fallback lookup stub by callee suffix-9 (chỉ để STAMP call_id) ===
        # action_call tạo placeholder với callee raw '0348886375', Stringee
        # gửi 84348886375 → suffix-9 mới khớp. KHÔNG dùng kết quả này để
        # override is_web_sdk_origin (vì nó được set ở trên).
        if not existing and to_num:
            import re
            from datetime import datetime, timedelta
            recent_threshold = datetime.utcnow() - timedelta(seconds=60)
            to_norm9 = re.sub(r'\D', '', to_num)[-9:]
            candidates = Call.search([
                ('direction', '=', 'outbound'),
                ('create_date', '>=', recent_threshold),
                ('state', 'in', ['draft', 'initiated', 'ringing']),
            ], order='create_date desc', limit=20)
            for cand in candidates:
                cand_norm9 = re.sub(r'\D', '', cand.callee_number or '')[-9:]
                if cand_norm9 and cand_norm9 == to_norm9:
                    existing = cand
                    if call_id and not existing.name:
                        existing.write({'name': call_id})
                    break

        # REST outbound = existing record + KHÔNG phải Web SDK origin.
        # action_call placeholder cũng có direction='outbound' nhưng KHÔNG
        # phải REST (browser tự makeCall) → loại trừ bằng is_web_sdk_origin.
        is_rest_outbound = (
            bool(existing) and existing.direction == 'outbound'
            and not is_web_sdk_origin
        )

        # Pre-create record để webhook tiếp theo find được.
        if call_id and not existing:
            Call.create({
                'name': call_id,
                'caller_number': from_num,
                'callee_number': to_num,
                'direction': 'outbound' if (is_rest_outbound or is_web_sdk_origin) else 'inbound',
                'state': 'initiated',
            })

        # SCCO record action standalone.
        actions = Call._scco_actions(
            record=record, event_url=f'{base_url}/stringee/recording_event',
        )

        # Build connect action — đúng theo Stringee SCCO docs + sample đối tác:
        # https://developer.stringee.com/docs/server/stringee-call-control-object
        # - `to` là OBJECT (không phải array)
        # - `to.alias` rỗng
        # - `peerToPeerCall: false` (cần để record work)
        # - `timeout: 30` + `continueOnFail: true` (per partner sample)
        # - KHÔNG có maxConnectTime, eventUrl (set ở project level)
        def _build_connect(from_endpoint, to_number):
            action = {
                'action': 'connect',
                'to': {'type': 'external', 'number': to_number, 'alias': ''},
                'peerToPeerCall': False,
                'timeout': 30,
                'continueOnFail': True,
            }
            if from_endpoint is not None:
                action['from'] = from_endpoint
            return action

        if to_num:
            if is_rest_outbound:
                # === HYBRID BRIDGE: REST dial KH PSTN xong → connect to internal NV ===
                # KH bắt máy → answer_url được gọi. Ta thêm SCCO connect to=internal:
                # NV's stringee_user_id để Stringee ring browser NV (incomingcall2).
                # Browser auto-answer → bridge audio KH ↔ NV.
                nv_sui = (existing.user_id.stringee_user_id or '').strip() if existing else ''
                if nv_sui:
                    actions.append({
                        'action': 'connect',
                        'to': {'type': 'internal', 'number': nv_sui, 'alias': ''},
                        'peerToPeerCall': False,
                        'timeout': 30,
                        'continueOnFail': True,
                    })
                # Nếu NV không có stringee_user_id → KHÔNG add connect (giữ flow cũ,
                # KH bắt máy nhưng không nghe được, sẽ tự ngắt sau vài giây).
            elif is_web_sdk_origin:
                # === STRINGEE FLOW 2: App-to-Phone (theo official docs) ===
                # https://developer.stringee.com/docs/call-api-overview
                # SCCO connect: from={type:internal, number:hotline}
                #               to=  {type:external, number:customer}
                # Browser StringeeCall2 đã init call, answer_url bridge audio.
                # Dùng effective_from (matched từ pool hotline NV) thay vì
                # global → caller-id đúng số NV gọi ra.
                actions.append(_build_connect(
                    {'type': 'internal', 'number': effective_from, 'alias': effective_from},
                    to_num,
                ))
            else:
                # PSTN inbound (KH gọi vào hotline) hoặc unknown origin.
                actions.append(_build_connect(
                    {'type': 'external', 'number': effective_from or from_num,
                     'alias': effective_from or from_num},
                    to_num,
                ))

        _logger.info(
            "[Stringee answer_url] callId=%s from=%s to=%s rest_out=%s web_sdk=%s actions=%s",
            call_id, from_num, to_num, is_rest_outbound, is_web_sdk_origin,
            json.dumps(actions, ensure_ascii=False),
        )

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

    @http.route('/stringee/js_event', type='json', auth='user')
    def js_event(self, event='', data=None, call_id=''):
        """JS log events lên server log để debug call flow khi user không mở
        được DevTools console. Mọi signalingstate/mediastate/error/answer/
        hangup event đều push qua đây."""
        _logger.info("[JS-CALL] user=%s call=%s event=%s data=%s",
                     request.env.user.login, call_id or '', event, data or {})
        return {'ok': True}

    @http.route('/stringee/finalize_my_active', type='json', auth='user')
    def finalize_my_active(self, call_id='', hangup_cause='JS_CLIENT_ENDED'):
        """Khi JS thấy signalingstate terminal (4 BUSY / 5 REJECTED / 6 ENDED),
        notify server để finalize active call placeholder NGAY — không chờ cron
        60s. Lý do: placeholder được tạo trước khi Stringee assign call_id, nên
        Stringee webhook event không match được → record kẹt state='initiated'.

        Effect: set state='ended', end_time=now → trigger compute
        `vd_active_call_state` trên CRM lead → bus broadcast → UI auto-update
        (FAB + banner clear, action_call cho phép gọi mới).
        """
        Call = request.env['stringee.call'].sudo()
        user = request.env.user
        active_states = ('draft', 'initiated', 'ringing', 'answered')

        # Strategy: ưu tiên match theo call_id (Stringee ID) nếu JS gửi.
        # Fallback: tất cả placeholder ACTIVE của user trong 5 phút gần đây
        # (chặn risk wipe call cũ kẹt từ session khác cùng user).
        recent_cutoff = fields.Datetime.now() - timedelta(minutes=5)
        domain = [('user_id', '=', user.id), ('state', 'in', active_states),
                  ('create_date', '>', recent_cutoff)]
        if call_id:
            # Stringee callId có thể đã được save vào `name` qua event matcher,
            # hoặc chưa — ta dùng OR để chắc chắn match.
            records = Call.search(
                ['|', ('name', '=', call_id), '&'] + domain, limit=5,
            )
        else:
            records = Call.search(domain, limit=5)

        if not records:
            _logger.info(
                "[JS-FINALIZE] user=%s call_id=%r → no active placeholder",
                user.login, call_id,
            )
            return {'ok': True, 'finalized': 0}

        now = fields.Datetime.now()
        for rec in records:
            try:
                vals = {
                    'state': 'ended',
                    'end_time': now,
                    'hangup_cause': hangup_cause or 'JS_CLIENT_ENDED',
                }
                # Lưu call_id vào name nếu placeholder chưa có — giúp event
                # webhook đến sau (recording_event…) match đúng record.
                if call_id and not rec.name:
                    vals['name'] = call_id
                rec.write(vals)
                _logger.info(
                    "[JS-FINALIZE] user=%s record id=%s name=%r → ended (cause=%s)",
                    user.login, rec.id, rec.name, hangup_cause,
                )
            except Exception:
                _logger.exception(
                    "[JS-FINALIZE] failed for record id=%s", rec.id,
                )
        request.env.cr.commit()
        return {'ok': True, 'finalized': len(records)}

    @http.route('/stringee/heartbeat', type='json', auth='user')
    def heartbeat(self, ok=False, r_code=None, message='', userId=''):
        """Browser JS ping sau event `authen` để confirm Stringee đã connect.
        Dùng cho debug — verify browser thật sự online với Stringee."""
        user = request.env.user
        _logger.info(
            "[Stringee heartbeat] uid=%s login=%s authen_ok=%s r=%s msg=%r sui=%r",
            user.id, user.login, ok, r_code, message, userId,
        )
        return {'ok': True}

    @http.route('/stringee/user_token', type='json', auth='user')
    def user_token(self):
        """Return a short-lived Stringee user token for the current user.

        Also returns `from_number` — the hotline number purchased on Stringee,
        used as fromNumber in StringeeCall2 constructor for App-to-Phone calls.

        Empty string token if user has no `stringee_user_id` configured.
        """
        user = request.env.user
        Param = request.env['ir.config_parameter'].sudo()
        # Ưu tiên hotline assign cho NV → fallback global config.
        # NV được set hotline riêng (vd Viettel/Mobi/Vina) sẽ caller-id đúng
        # nhà mạng, KH dễ bắt máy + cước rẻ intra-network.
        user_hotline = (
            user.stringee_from_number_id.number
            if user.stringee_from_number_id else ''
        )
        from_number = (user_hotline or Param.get_param('vd_stringee.from_number') or '').strip()
        _logger.info(
            "[Stringee user_token] called by uid=%s login=%s stringee_user_id=%r from_number=%r (user_specific=%s)",
            user.id, user.login, user.stringee_user_id, from_number,
            bool(user_hotline),
        )
        if not user.stringee_user_id:
            _logger.warning(
                "[Stringee user_token] uid=%s login=%s HAS NO stringee_user_id → empty token",
                user.id, user.login,
            )
            return {
                'token': '', 'user_id': '', 'from_number': from_number,
                'reason': 'no stringee_user_id on user',
            }
        try:
            token = request.env['stringee.jwt'].sudo().gen_user_token(user.stringee_user_id)
            _logger.info(
                "[Stringee user_token] generated token for %s len=%s",
                user.stringee_user_id, len(token or ''),
            )
        except Exception as e:
            _logger.exception("[Stringee user_token] gen_user_token FAILED: %s", e)
            raise
        return {
            'token': token,
            'user_id': user.stringee_user_id,
            'from_number': from_number,
        }
