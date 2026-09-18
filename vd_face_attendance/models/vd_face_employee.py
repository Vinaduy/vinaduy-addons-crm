# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VdFaceEmployee(models.Model):
    _name = 'vd.face.employee'
    _description = 'Nhân viên đã đăng ký khuôn mặt'
    _order = 'code'

    code = fields.Char(
        string='Mã số NV', readonly=True, copy=False, index=True, default='/')
    name = fields.Char(string='Tên nhân viên', required=True)
    gender = fields.Selection(
        [('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')],
        string='Giới tính')
    user_id = fields.Many2one(
        'res.users', string='Tài khoản', index=True, ondelete='cascade',
        default=lambda s: s.env.user)
    photo = fields.Binary(string='Ảnh đăng ký', attachment=True)
    descriptor = fields.Text(string='Vector khuôn mặt', copy=False)
    enrolled_date = fields.Datetime(
        string='Ngày đăng ký', default=fields.Datetime.now)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('user_uniq', 'unique(user_id)',
         'Mỗi tài khoản chỉ đăng ký 1 khuôn mặt.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', '/') in (False, '/', ''):
                vals['code'] = (self.env['ir.sequence']
                                .next_by_code('vd.face.employee') or '/')
        return super().create(vals_list)
