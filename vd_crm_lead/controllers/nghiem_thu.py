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
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from werkzeug.wrappers import Response

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
_API_KEY = 'AIzaSyCnG0g9C9EHZ41JMHl364pzLo_auEkLKlk'

_FOLDER_MIME = 'application/vnd.google-apps.folder'
_DRIVE_API = 'https://www.googleapis.com/drive/v3/files'

# Cache theo folder id (mỗi worker giữ riêng) → mở lại nhanh, đỡ gọi Google lặp.
_LIST_CACHE = {}      # folder_id -> (expire_ts, payload_dict)
_CACHE_TTL = 600      # 10 phút


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
        """Liệt kê con TRỰC TIẾP của 1 folder (cả file + thư mục con). 1 API call,
        timeout ngắn để KHÔNG giữ worker lâu (tránh treo cả server)."""
        params = {
            'q': "'%s' in parents and trashed=false" % folder_id,
            'key': api_key,
            'fields': 'files(id,name,mimeType)',
            'pageSize': 1000,
            'orderBy': 'folder,name',
            'supportsAllDrives': 'true',
            'includeItemsFromAllDrives': 'true',
        }
        r = requests.get(_DRIVE_API, params=params, timeout=12)
        r.raise_for_status()
        return r.json().get('files', [])

    def _safe_list(self, folder_id, api_key):
        try:
            return self._list_children(folder_id, api_key)
        except Exception:  # noqa: BLE001
            return []

    def _collect_all_files(self, root_id, api_key, cap=300):
        """Gom TẤT CẢ file dưới root (đệ quy) — quét thư mục con SONG SONG (nhanh).
        cap = số thư mục tối đa quét (chống nổ). Lỗi root -> ném (route bắt)."""
        root_children = self._list_children(root_id, api_key)  # có thể ném lỗi
        files, queue, scanned = [], [], 0

        def sort_children(children):
            for c in children:
                if c.get('mimeType') == _FOLDER_MIME:
                    queue.append(c['id'])
                else:
                    files.append({'id': c['id'], 'name': c.get('name', ''),
                                  'mime': c.get('mimeType', '')})

        sort_children(root_children)
        with ThreadPoolExecutor(max_workers=8) as ex:
            while queue and scanned < cap:
                batch = queue[:8]
                del queue[:8]
                scanned += len(batch)
                for children in ex.map(lambda fid: self._safe_list(fid, api_key), batch):
                    sort_children(children)
        files.sort(key=lambda f: (f.get('name') or '').lower())
        return files

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
        """Trả file theo NHÓM = thư mục con cấp 1. Mỗi nhóm gom hết file bên trong
        (đệ quy, quét song song). Cache 10'. Mỗi file: {id,name,mime}."""
        if key not in _LIB_FOLDERS:
            return self._json({'error': 'Kho không hợp lệ.'}, status=404)
        api_key = self._api_key()
        root = self._folder_id(key)
        if not (api_key and root):
            return self._json({'error': 'Chưa cấu hình API key hoặc folder.'})
        hit = _LIST_CACHE.get(root)
        if hit and hit[0] > time.time():
            return self._json(hit[1])
        try:
            root_children = self._list_children(root, api_key)
        except requests.HTTPError:
            return self._json({'error': 'Không đọc được thư mục Drive. Kiểm tra: '
                               'folder đã chia sẻ "ai có link → Người xem" và đã BẬT '
                               'Google Drive API.'})
        except Exception as e:  # noqa: BLE001
            _logger.warning('Drive list lỗi (key=%s): %s', key, e)
            return self._json({'error': 'Mạng tới Google chập chờn, thử lại sau ít giây.'})

        def fobj(f):
            return {'id': f['id'], 'name': f.get('name', ''),
                    'mime': f.get('mime') or f.get('mimeType', '')}

        top_folders = [c for c in root_children if c.get('mimeType') == _FOLDER_MIME]
        root_files = [c for c in root_children if c.get('mimeType') != _FOLDER_MIME]
        groups = []
        if root_files:
            groups.append({'name': 'Tất cả',
                           'files': sorted([fobj(f) for f in root_files],
                                           key=lambda x: x['name'].lower())})

        # Quét MỌI thư mục cấp 1 SONG SONG (trước đây tuần tự → chậm: mỗi kho
        # ~6-8 folder × Drive API = cộng dồn). Chỉ dùng `requests` + api_key trong
        # thread (KHÔNG đụng request.env) nên an toàn. ex.map giữ đúng thứ tự.
        def _one_group(fo):
            try:
                allf = self._collect_all_files(fo['id'], api_key)
            except Exception:  # noqa: BLE001
                allf = []
            return {'name': fo['name'], 'files': [fobj(f) for f in allf]}

        if top_folders:
            with ThreadPoolExecutor(max_workers=min(8, len(top_folders))) as ex:
                groups.extend(ex.map(_one_group, top_folders))
        payload = {'groups': groups}
        _LIST_CACHE[root] = (time.time() + _CACHE_TTL, payload)
        return self._json(payload)

    @http.route('/vd_drive_lib/thumb', type='http', auth='user', website=False)
    def vd_drive_lib_thumb(self, key=None, id=None, **kw):
        """Proxy ảnh thumbnail của Drive qua server → ảnh SAME-ORIGIN (tránh lỗi
        cross-origin làm đơ trang + không phụ thuộc NV có đăng nhập Google)."""
        if key not in _LIB_FOLDERS or not id:
            return request.not_found()
        try:
            r = requests.get('https://drive.google.com/thumbnail',
                             params={'id': id, 'sz': 'w400'}, timeout=15, stream=True)
            r.raise_for_status()
        except Exception:  # noqa: BLE001
            return request.not_found()
        return Response(
            r.iter_content(8192),
            headers=[('Content-Type', r.headers.get('Content-Type', 'image/jpeg')),
                     ('Cache-Control', 'public, max-age=86400')],
            direct_passthrough=True,
        )

    @http.route('/vd_drive_lib/dl', type='http', auth='user', website=False)
    def vd_drive_lib_dl(self, key=None, id=None, **kw):
        """Tải file: PROXY-STREAM qua Odoo (Drive API alt=media) → tải SẠCH trong
        Odoo (same-origin, có nút Tải/attribute download hoạt động), KHÔNG lộ Google,
        KHÔNG dính trang xác nhận virus. Stream chunk → nhẹ RAM."""
        if key not in _LIB_FOLDERS or not id:
            return request.not_found()
        api_key = self._api_key()
        try:
            meta = requests.get(
                '%s/%s' % (_DRIVE_API, id),
                params={'key': api_key, 'fields': 'name,mimeType,size',
                        'supportsAllDrives': 'true'}, timeout=15)
            meta.raise_for_status()
            meta = meta.json()
            name = meta.get('name') or (id + '.bin')
            mime = meta.get('mimeType') or 'application/octet-stream'
            upstream = requests.get(
                '%s/%s' % (_DRIVE_API, id),
                params={'key': api_key, 'alt': 'media', 'supportsAllDrives': 'true'},
                stream=True, timeout=120)
            upstream.raise_for_status()
        except Exception:  # noqa: BLE001
            _logger.exception('Drive dl lỗi (id=%s)', id)
            return request.not_found()
        headers = [
            ('Content-Type', mime),
            ('Content-Disposition', "attachment; filename*=UTF-8''%s" % quote(name)),
            ('Cache-Control', 'no-store'),
        ]
        cl = upstream.headers.get('Content-Length')
        if cl:
            headers.append(('Content-Length', cl))
        return Response(upstream.iter_content(chunk_size=262144),
                        headers=headers, direct_passthrough=True)

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
