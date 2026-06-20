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

    def _gads_snippet(self):
        """Sinh đoạn <script> Google Ads để chèn vào <head> của landing.

        Đọc cấu hình admin (ir.config_parameter) -> nếu chưa bật hoặc thiếu ID
        thì trả về chuỗi rỗng (không chèn gì). Gồm:
          - Code 1: gtag.js + config
          - Code 2: hàm gtag_report_conversion (dùng nhãn 'Nhấp để gọi')
          - Tự gắn onclick cho MỌI link tel: (khỏi sửa tay từng số)
        """
        ICP = request.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('vd_website_landing.gads_enabled')
        conv_id = (ICP.get_param(
            'vd_website_landing.gads_conversion_id') or '').strip()
        label = (ICP.get_param(
            'vd_website_landing.gads_call_label') or '').strip()
        if not enabled or not conv_id:
            return ''
        send_to = conv_id
        if label:
            send_to = '%s/%s' % (conv_id, label)
        return """
<!-- Google tag (gtag.js) - Vinaduy landing -->
<script async src="https://www.googletagmanager.com/gtag/js?id={conv_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{conv_id}');
</script>
<!-- Event snippet: Nhap de goi -->
<script>
function gtag_report_conversion(url) {{
  var callback = function () {{
    if (typeof(url) != 'undefined') {{ window.location = url; }}
  }};
  gtag('event', 'conversion', {{
    'send_to': '{send_to}',
    'value': 1.0,
    'currency': 'VND',
    'event_callback': callback
  }});
  return false;
}}
// Tu gan tracking cho moi link tel: (ke ca them so moi sau nay).
document.addEventListener('DOMContentLoaded', function () {{
  // Bỏ qua link đã tự khai onclick (vd nut vd-call) de tranh ban 2 lan.
  var links = document.querySelectorAll('a[href^="tel:"]:not([onclick])');
  for (var i = 0; i < links.length; i++) {{
    (function (a) {{
      a.addEventListener('click', function (e) {{
        e.preventDefault();
        return gtag_report_conversion(a.getAttribute('href'));
      }});
    }})(links[i]);
  }}
}});
</script>
""".format(conv_id=conv_id, send_to=send_to)

    def _serve_landing(self):
        with open(_HTML_PATH, 'rb') as f:
            html = f.read()
        snippet = self._gads_snippet()
        if snippet:
            # Chèn ngay trước </head> để gtag nằm trong <head> như Google yêu cầu.
            snippet_b = snippet.encode('utf-8')
            idx = html.lower().find(b'</head>')
            if idx != -1:
                html = html[:idx] + snippet_b + html[idx:]
            else:
                html = snippet_b + html
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

    @http.route('/dich-vu-xay-nha/login', type='http', auth='public',
                methods=['POST'], csrf=False)
    def landing_login(self, login=None, password=None, **post):
        """Đăng nhập từ landing. NV -> vào thẳng CRM, admin -> /odoo (toàn quyền)."""
        login = (login or '').strip()
        db = request.session.db
        if not (login and password):
            return request.make_json_response(
                {'ok': False, 'error': 'Nhập tên đăng nhập và mật khẩu.'})
        try:
            request.session.authenticate(
                db, {'login': login, 'password': password, 'type': 'password'})
        except Exception:
            return request.make_json_response(
                {'ok': False, 'error': 'Sai tên đăng nhập hoặc mật khẩu.'})
        uid = request.session.uid
        if not uid:
            return request.make_json_response(
                {'ok': False, 'error': 'Sai tên đăng nhập hoặc mật khẩu.'})
        env = request.env(user=uid)
        # Admin (toàn quyền) -> trang chủ Odoo như cũ; còn lại (NV) -> thẳng CRM.
        if env.user.has_group('base.group_system'):
            target = '/odoo'
        else:
            target = '/odoo/crm'
            try:
                act = env.ref('crm.crm_lead_action_pipeline')
                target = '/odoo/action-%s' % act.id
            except Exception:
                pass
        return request.make_json_response({'ok': True, 'redirect': target})
