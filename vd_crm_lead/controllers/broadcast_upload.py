# -*- coding: utf-8 -*-
"""Upload ảnh/video cho Chiến dịch Spam Zalo — controller HTTP riêng để có
thanh tiến trình (progress) khi tải file lớn, tự hiện ngay không cần reload."""
import json

from odoo import http
from odoo.http import request


class VdBroadcastUploadController(http.Controller):

    @http.route('/vd_broadcast/upload', type='http', auth='user',
                methods=['POST'], csrf=True)
    def upload(self, campaign_id=None, **kw):
        """Nhận multipart 1 (hoặc nhiều) file 'ufile', tạo ir.attachment gắn vào
        chiến dịch, trả JSON danh sách attachment vừa tạo."""
        user = request.env.user
        if not (user.has_group('sales_team.group_sale_manager')
                or user.has_group('base.group_system')):
            return request.make_response(
                json.dumps({'error': 'Không có quyền tải lên.'}),
                headers=[('Content-Type', 'application/json')])
        try:
            camp = request.env['vd.broadcast.campaign'].sudo().browse(int(campaign_id))
            if not camp.exists():
                raise ValueError('camp')
        except (TypeError, ValueError):
            return request.make_response(
                json.dumps({'error': 'Chiến dịch không tồn tại.'}),
                headers=[('Content-Type', 'application/json')])

        files = request.httprequest.files.getlist('ufile')
        Att = request.env['ir.attachment'].sudo()
        out = []
        for f in files:
            data = f.read()
            att = Att.create({
                'name': f.filename or 'tep-tai-len',
                'raw': data,
                'res_model': 'vd.broadcast.campaign',
                'res_id': camp.id,
                'mimetype': f.content_type or False,
            })
            camp.write({'attachment_ids': [(4, att.id)]})
            mimetype = att.mimetype or ''
            kind = ('video' if mimetype.startswith('video')
                    else 'image' if mimetype.startswith('image') else 'file')
            out.append({
                'id': att.id,
                'name': att.name,
                'mimetype': mimetype,
                'kind': kind,
                'url': '/web/content/%s?download=true' % att.id,
                'src': '/web/content/%s' % att.id,
            })
        return request.make_response(
            json.dumps({'attachments': out}),
            headers=[('Content-Type', 'application/json')])
