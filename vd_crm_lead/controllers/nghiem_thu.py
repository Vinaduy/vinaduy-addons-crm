# -*- coding: utf-8 -*-
"""THƯ VIỆN tài liệu (nhúng Google Drive, BẢO MẬT link) — Hướng A.

Gồm nhiều kho (key -> folder Drive):
  - nghiem_thu   : Video nghiệm thu (Móng / Xây thô / Hoàn thiện)
  - cong_nang_3d : Công năng 3D
  - hop_dong     : Hợp đồng

Bảo mật (best-effort — không tuyệt đối vì bản chất nhúng):
  - Folder ID Google KHÔNG nằm trong JS/template client. Chỉ ở PYTHON server-side
    (map dưới, có thể override qua System Parameter) → NV không thấy ID trong bundle.
  - Nút trong CRM trỏ iframe tới URL NỘI BỘ `/vd_drive_lib/embed?key=...` (không
    phải URL Google). Route auth='user' → người ngoài không mở được.
  - Controller CHỈ nhận `key` nằm trong danh sách trắng (không cho truyền folder id
    tùy ý) + iframe LỒNG + chặn chuột phải để khó copy link.

LƯU Ý: mỗi folder Drive phải chia sẻ "Bất kỳ ai có đường liên kết → Người xem"
thì embeddedfolderview mới render (NV chỉ xem/tải, KHÔNG xóa/sửa được).
"""
from odoo import http
from odoo.http import request

# key -> folder id mặc định. Đổi folder: sửa đây HOẶC set System Parameter
# 'vd_crm_lead.drive_lib_folder_<key>' (không cần sửa code).
_LIB_FOLDERS = {
    'nghiem_thu': '1MW9BYFZsirgcnyeuzaMTM1_2ciDm3XFW',
    'cong_nang_3d': '1-PUp_K3vv-Bk0fZiLvgdR_8ROEQDuuN2',
    'hop_dong': '1-VBqkAsF0v8M96OUH6OXJ1eHkvRpeECb',
}


class VdDriveLibController(http.Controller):

    @http.route('/vd_drive_lib/embed', type='http', auth='user', website=False)
    def vd_drive_lib_embed(self, key=None, **kw):
        # Chỉ chấp nhận key trong danh sách trắng (tránh nhúng folder tùy ý).
        if key not in _LIB_FOLDERS:
            return request.not_found()
        ICP = request.env['ir.config_parameter'].sudo()
        folder_id = (ICP.get_param('vd_crm_lead.drive_lib_folder_' + key)
                     or _LIB_FOLDERS[key])
        src = 'https://drive.google.com/embeddedfolderview?id=%s#grid' % folder_id
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<meta name="referrer" content="no-referrer">'
            '<style>html,body{margin:0;padding:0;height:100%;overflow:hidden;'
            'background:#fff;}iframe{border:0;width:100%;height:100%;}</style>'
            '</head><body oncontextmenu="return false" '
            'onselectstart="return false">'
            '<iframe src="' + src + '" referrerpolicy="no-referrer" '
            'allow="autoplay"></iframe>'
            '<script>document.addEventListener("contextmenu",'
            'function(e){e.preventDefault();});</script>'
            '</body></html>'
        )
        return request.make_response(
            html,
            headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
                ('X-Frame-Options', 'SAMEORIGIN'),
                ('Cache-Control', 'no-store'),
            ],
        )
