# -*- coding: utf-8 -*-
"""Tương thích app Odoo Mobile native với Odoo 18 Community (user spec 2026-06-12).

App "Odoo Mobile" (iOS/Android) chỉ hỗ trợ **Odoo >= 16 + bản ENTERPRISE**. Server
vinaduy.com là **Community** → app báo "Unsupported Odoo Version" ngay cổng đăng
nhập (dù webview sau khi vào CHẠY bình thường với Community 18).

Cách app phân biệt edition: phần tử CUỐI của `server_version_info` = 'e' (Enterprise)
hay '' (Community). Xem web/static/src/start.js:
    isEnterprise: session.server_version_info.slice(-1)[0] === "e"

Giải pháp SCOPED: CHỈ với request từ app (User-Agent chứa "Odoo Mobile"), endpoint
version_info GIẢ cờ Enterprise ('e') để qua cổng. Mọi client khác (trình duyệt —
dùng session_info, KHÔNG dùng endpoint này) nhận thông tin THẬT (Community 18) →
KHÔNG ảnh hưởng. Webview app sau khi vào cũng dùng session_info thật → chạy đúng 18.

Tuỳ chọn ép thêm major version qua System Parameter
'vd_crm_lead.mobile_app_version' (vd '17.0') nếu cần — mặc định giữ version thật.
"""
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.webclient import WebClient


class VdWebClientVersionCompat(WebClient):

    @http.route()
    def version_info(self):
        info = super().version_info()
        try:
            ua = request.httprequest.headers.get('User-Agent', '') or ''
        except Exception:
            ua = ''
        if 'Odoo Mobile' not in ua:
            return info  # trình duyệt / client khác → THẬT (Community 18)
        try:
            info = dict(info or {})
            vi = list(info.get('server_version_info') or [18, 0, 0, 'final', 0, ''])
            # Tuỳ chọn ép major version (mặc định '' = giữ thật)
            forced = ''
            try:
                forced = (request.env['ir.config_parameter'].sudo()
                          .get_param('vd_crm_lead.mobile_app_version', '')) or ''
            except Exception:
                forced = ''
            if forced:
                try:
                    parts = [int(x) for x in str(forced).split('.')[:2]]
                    major = parts[0]
                    minor = parts[1] if len(parts) > 1 else 0
                    vi[0], vi[1] = major, minor
                    info['server_serie'] = '%d.%d' % (major, minor)
                except Exception:
                    pass
            # GIẢ cờ Enterprise: phần tử cuối = 'e'
            if vi:
                vi[-1] = 'e'
            info['server_version_info'] = vi
            sv = str(info.get('server_version') or info.get('server_serie') or '18.0')
            if not sv.endswith('e'):
                info['server_version'] = sv.rstrip('+') + '+e'
        except Exception:
            pass
        return info
