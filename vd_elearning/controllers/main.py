# -*- coding: utf-8 -*-
"""Phuc vu FILE PDF noi dung khoa hoc cho NV xem trong khung hoc.
Route auth='user' + sudo: NV chua la member van xem duoc (app kiem soat quyen),
KHONG lo file ra ngoai (phai dang nhap). User spec 2026-07-31."""
import base64
from urllib.parse import quote

from odoo import http
from odoo.http import request


class VdElearningController(http.Controller):

    @http.route('/vd_elearning/course_pdf/<int:channel_id>', type='http',
                auth='user', website=False)
    def course_pdf(self, channel_id, **kw):
        ch = request.env['slide.channel'].sudo().browse(channel_id)
        if not ch.exists() or not ch.vd_pdf:
            return request.not_found()
        try:
            data = base64.b64decode(ch.vd_pdf)
        except Exception:  # noqa: BLE001
            return request.not_found()
        name = ch.vd_pdf_name or 'noidung.pdf'
        return request.make_response(data, headers=[
            ('Content-Type', 'application/pdf'),
            # inline -> hien trong iframe; KHONG cho download tu dong.
            ('Content-Disposition', "inline; filename*=UTF-8''%s" % quote(name)),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    @http.route('/vd_elearning/question_template', type='http', auth='user',
                website=False)
    def question_template(self, **kw):
        """Tai FILE MAU Excel nhap cau hoi: 1 dong 1 cau, cot cuoi = so dap an dung."""
        import io
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'CauHoi'
        ws.append(['Câu hỏi', 'Đáp án 1', 'Đáp án 2', 'Đáp án 3', 'Đáp án 4',
                   'Số đáp án đúng (1-4)'])
        ws.append(['Móng băng dùng cho công trình nào?', 'Nhà 1-3 tầng nền tốt',
                   'Nhà cao tầng', 'Nền đất yếu', 'Nhà tiền chế', 1])
        ws.append(['Bê tông mác 250 nghĩa là gì?', 'Cường độ 250 daN/cm2',
                   'Nặng 250kg', 'Dày 250mm', '', 1])
        for col, w in zip('ABCDEF', (42, 22, 22, 22, 22, 18)):
            ws.column_dimensions[col].width = w
        buf = io.BytesIO()
        wb.save(buf)
        return request.make_response(buf.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', "attachment; filename=mau_cau_hoi.xlsx"),
            ('Cache-Control', 'no-store'),
        ])
