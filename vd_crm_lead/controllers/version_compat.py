# -*- coding: utf-8 -*-
"""Tương thích app Odoo Mobile native với Odoo 18 (user spec 2026-06-12).

App "Odoo Mobile" (iOS/Android) chê Odoo 18 ngay ở cổng đăng nhập:
"Unsupported Odoo Version". Bằng chứng: app gọi /web/webclient/version_info,
đọc server_version=18.0 → từ chối, không cho login (dù webview sau khi vào CHẠY
bình thường với 18.0).

Giải pháp SCOPED: CHỈ với request từ app (User-Agent chứa "Odoo Mobile"),
endpoint version_info báo version GIẢ (mặc định 16.0) để qua cổng. Mọi client
khác (trình duyệt — vốn dùng session_info, KHÔNG dùng endpoint này) nhận version
THẬT 18.0 → không ảnh hưởng. Đổi version giả qua System Parameter
'vd_crm_lead.mobile_app_version' (không cần deploy lại).
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
            return info  # trình duyệt / client khác → version THẬT
        ver = '16.0'
        try:
            ver = (request.env['ir.config_parameter'].sudo()
                   .get_param('vd_crm_lead.mobile_app_version', '16.0')) or '16.0'
        except Exception:
            pass
        try:
            major = int(str(ver).split('.')[0])
        except Exception:
            major, ver = 16, '16.0'
        info = dict(info or {})
        info['server_version'] = ver
        info['server_serie'] = ver
        info['server_version_info'] = [major, 0, 0, 'final', 0, '']
        return info
