# -*- coding: utf-8 -*-
"""Webhook Meta (Facebook) — nhận tin nhắn + bình luận trực tiếp từ Facebook.

  GET  /vd_crm/fb/webhook  → Meta verify (hub.challenge).
  POST /vd_crm/fb/webhook  → Meta gửi event (messages / feed comments).

Verify token so khớp với vd.fb.app.verify_token. Khi cấu hình trên Meta,
dán URL này + Verify Token (hiện trong màn App).
"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VdFbWebhookController(http.Controller):

    @http.route('/vd_crm/fb/webhook', type='http', auth='public',
                methods=['GET', 'POST'], csrf=False, save_session=False)
    def fb_webhook(self, **kwargs):
        # ----- GET: Meta verify subscription -----
        if request.httprequest.method == 'GET':
            mode = kwargs.get('hub.mode')
            token = kwargs.get('hub.verify_token')
            challenge = kwargs.get('hub.challenge', '')
            App = request.env['vd.fb.app'].sudo()
            valid = App.search_count([('verify_token', '=', token), ('active', '=', True)])
            if mode == 'subscribe' and token and valid:
                return request.make_response(challenge, headers=[('Content-Type', 'text/plain')])
            _logger.warning('[FB webhook] verify FAIL mode=%s token_ok=%s', mode, bool(valid))
            return request.make_response('forbidden', status=403)

        # ----- POST: event payload -----
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            payload = json.loads(raw)
        except Exception:
            _logger.warning('[FB webhook] payload không parse được')
            payload = {}
        _logger.info('[FB webhook] %s', json.dumps(payload)[:1500])
        try:
            request.env['vd.fb.app'].sudo().handle_webhook(payload)
        except Exception:
            _logger.exception('[FB webhook] handle_webhook lỗi')
        # Meta yêu cầu trả 200 nhanh, nếu không sẽ retry/ngắt subscription.
        return request.make_response('EVENT_RECEIVED', headers=[('Content-Type', 'text/plain')])
