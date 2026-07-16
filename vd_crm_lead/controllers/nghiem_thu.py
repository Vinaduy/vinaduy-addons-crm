# -*- coding: utf-8 -*-
"""THƯ VIỆN tài liệu (Google Drive) — Hướng A+ (dùng Drive API để có nút TẢI từng file).

Gồm nhiều kho (key -> folder Drive):
  - nghiem_thu   : Video nghiệm thu (Móng / Xây thô / Hoàn thiện là thư mục con)
  - cong_nang_3d : Công năng 3D
  - hop_dong     : Hợp đồng

Cách hoạt động:
  - Controller gọi Google Drive API (API KEY + folder id, đều SERVER-SIDE) để liệt
    kê file trong folder + thư mục con → trả JSON cho popup dựng LƯỚI có nút TẢI
    từng file (không cần mở xem).
  - API key + folder id KHÔNG nằm trong bundle client. Route auth='user' → người
    ngoài không gọi được. Chỉ nhận `key` trong danh sách trắng.
  - Nút Tải trỏ /vd_drive_lib/dl?key=..&id=.. → redirect tới link tải trực tiếp
    của Drive (file nặng >100MB Google chèn 1 trang xác nhận — bấm thêm 1 lần).

YÊU CẦU: mỗi folder Drive phải share "Bất kỳ ai có đường liên kết → Người xem"
(API key không đăng nhập nên chỉ đọc được folder public). NV chỉ xem/tải, không xóa.
"""
import json
import logging

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# key -> folder id. Override qua System Parameter 'vd_crm_lead.drive_lib_folder_<key>'.
_LIB_FOLDERS = {
    'nghiem_thu': '1MW9BYFZsirgcnyeuzaMTM1_2ciDm3XFW',
    'cong_nang_3d': '1-PUp_K3vv-Bk0fZiLvgdR_8ROEQDuuN2',
    'hop_dong': '1-VBqkAsF0v8M96OUH6OXJ1eHkvRpeECb',
}
# API key (server-side). Override qua System Parameter 'vd_crm_lead.drive_lib_api_key'.
_API_KEY = 'AIzaSyCHkGs3J3QKnSTC-RQCGxIH3yHCEJxnel0'

_FOLDER_MIME = 'application/vnd.google-apps.folder'
_DRIVE_API = 'https://www.googleapis.com/drive/v3/files'


class VdDriveLibController(http.Controller):

    # ---- helpers ---------------------------------------------------------
    def _api_key(self):
        return (request.env['ir.config_parameter'].sudo()
                .get_param('vd_crm_lead.drive_lib_api_key') or _API_KEY)

    def _folder_id(self, key):
        return (request.env['ir.config_parameter'].sudo()
                .get_param('vd_crm_lead.drive_lib_folder_' + key)
                or _LIB_FOLDERS.get(key))

    def _list_children(self, folder_id, api_key):
        """Liệt kê con TRỰC TIẾP của 1 folder (cả file + thư mục con)."""
        params = {
            'q': "'%s' in parents and trashed=false" % folder_id,
            'key': api_key,
            'fields': 'files(id,name,mimeType)',
            'pageSize': 1000,
            'orderBy': 'folder,name',
            'supportsAllDrives': 'true',
            'includeItemsFromAllDrives': 'true',
        }
        r = requests.get(_DRIVE_API, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get('files', [])

    def _json(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Cache-Control', 'no-store')],
            status=status,
        )

    # ---- routes ----------------------------------------------------------
    @http.route('/vd_drive_lib/list', type='http', auth='user', website=False)
    def vd_drive_lib_list(self, key=None, **kw):
        if key not in _LIB_FOLDERS:
            return self._json({'error': 'Kho không hợp lệ.'}, status=404)
        api_key = self._api_key()
        root = self._folder_id(key)
        if not (api_key and root):
            return self._json({'error': 'Chưa cấu hình API key hoặc folder.'})
        try:
            children = self._list_children(root, api_key)
            folders = [c for c in children if c.get('mimeType') == _FOLDER_MIME]
            root_files = [c for c in children if c.get('mimeType') != _FOLDER_MIME]
            groups = []
            if root_files:
                groups.append({'name': 'Tất cả',
                               'files': [{'id': f['id'], 'name': f['name']}
                                         for f in root_files]})
            for fo in folders:
                sub = self._list_children(fo['id'], api_key)
                subfiles = [c for c in sub if c.get('mimeType') != _FOLDER_MIME]
                groups.append({'name': fo['name'],
                               'files': [{'id': f['id'], 'name': f['name']}
                                         for f in subfiles]})
            return self._json({'groups': groups})
        except requests.HTTPError as e:
            _logger.warning('Drive list lỗi HTTP: %s', e)
            return self._json({'error': 'Không đọc được thư mục Drive. '
                               'Kiểm tra: folder đã chia sẻ "ai có link → Người xem" '
                               'và API key còn hạn/đúng quyền Drive API.'})
        except Exception as e:  # noqa: BLE001
            _logger.exception('Drive list lỗi: %s', e)
            return self._json({'error': 'Lỗi tải danh sách tài liệu.'})

    @http.route('/vd_drive_lib/dl', type='http', auth='user', website=False)
    def vd_drive_lib_dl(self, key=None, id=None, **kw):
        # Chỉ cho tải khi key hợp lệ (auth='user' đã chặn người ngoài).
        if key not in _LIB_FOLDERS or not id:
            return request.not_found()
        url = ('https://drive.google.com/uc?export=download&id=%s&confirm=t'
               % id)
        return request.redirect(url, code=302, local=False)

    # Giữ route nhúng (dự phòng) — hiện popup dùng lưới nút Tải là chính.
    @http.route('/vd_drive_lib/embed', type='http', auth='user', website=False)
    def vd_drive_lib_embed(self, key=None, **kw):
        if key not in _LIB_FOLDERS:
            return request.not_found()
        folder_id = self._folder_id(key)
        src = 'https://drive.google.com/embeddedfolderview?id=%s#grid' % folder_id
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<style>html,body{margin:0;height:100%;overflow:hidden;}'
            'iframe{border:0;width:100%;height:100%;}</style></head>'
            '<body oncontextmenu="return false"><iframe src="' + src + '"'
            ' referrerpolicy="no-referrer"></iframe></body></html>'
        )
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8'),
                           ('X-Frame-Options', 'SAMEORIGIN')])
