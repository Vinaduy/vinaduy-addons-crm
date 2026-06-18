# -*- coding: utf-8 -*-
"""Landing "Dịch vụ xây nhà" (LadiPage) + endpoint thu lead vào CRM.

- GET  /dich-vu-xay-nha       -> trả nguyên trang LadiPage (static/landing/index.html)
- POST /dich-vu-xay-nha/lead  -> tạo crm.lead từ form đăng ký trên trang

Trang LadiPage là 1 tài liệu HTML standalone (có sẵn <html><head><body>, CSS
inline, JS hiệu ứng riêng) nên KHÔNG nhúng vào layout/website của Odoo — phục
vụ y nguyên để giữ giao diện + hiệu ứng pixel-perfect như bản demo.
"""
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_HTML_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'landing', 'index.html')


class VdWebsiteLanding(http.Controller):

    def _serve_landing(self):
        with open(_HTML_PATH, 'rb') as f:
            html = f.read()
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
        ])

    # Trang chủ: ghi đè route '/' của module website để serve landing.
    @http.route('/', type='http', auth='public', website=True,
                sitemap=True, csrf=False)
    def index(self, **kw):
        return self._serve_landing()

    @http.route('/dich-vu-xay-nha', type='http', auth='public',
                website=True, sitemap=True, csrf=False)
    def landing(self, **kw):
        return self._serve_landing()

    @http.route('/dich-vu-xay-nha/lead', type='http', auth='public',
                methods=['POST'], csrf=False)
    def landing_lead(self, **post):
        name = (post.get('name') or '').strip()
        phone = (post.get('phone') or '').strip()
        email = (post.get('email') or '').strip()
        message = (post.get('message') or '').strip()
        if not (name or phone):
            return request.make_json_response(
                {'ok': False, 'error': 'Thiếu họ tên / số điện thoại.'})
        title = name or phone or 'Khách landing'
        desc_lines = ['Nguồn: Landing "Dịch vụ xây nhà" (/dich-vu-xay-nha)']
        if email:
            desc_lines.append('Email: %s' % email)
        if message:
            desc_lines.append('Lời nhắn: %s' % message)
        try:
            lead = request.env['crm.lead'].sudo().create({
                'name': 'Landing xây nhà - %s' % title,
                'contact_name': name or False,
                'partner_name': name or False,
                'phone': phone or False,
                'email_from': email or False,
                'type': 'lead',
                'description': '\n'.join(desc_lines),
            })
            _logger.info('Landing lead created id=%s phone=%s', lead.id, phone)
        except Exception:
            _logger.exception('Landing lead create failed')
            return request.make_json_response(
                {'ok': False, 'error': 'Lỗi hệ thống, vui lòng gọi hotline.'})
        return request.make_json_response({'ok': True})
