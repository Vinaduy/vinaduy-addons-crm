# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Vector 128 chiều mô tả khuôn mặt (JSON list) — dùng để nhận diện khi chấm
    # công. Lưu ở phía user, ghi qua method sudo (vd_enroll_face) nên KHÔNG mở
    # SELF_WRITEABLE (tránh NV tự sửa vector bừa).
    vd_face_descriptor = fields.Text(
        string='Dữ liệu khuôn mặt', copy=False,
        help='Vector 128 số mô tả khuôn mặt NV — tạo khi đăng ký, dùng để nhận diện.')
    vd_face_enrolled = fields.Boolean(
        string='Đã đăng ký khuôn mặt',
        compute='_compute_vd_face_enrolled', store=True)

    @api.depends('vd_face_descriptor')
    def _compute_vd_face_enrolled(self):
        for u in self:
            u.vd_face_enrolled = bool(u.vd_face_descriptor)
