# -*- coding: utf-8 -*-
from odoo import fields, models


class VdLearningPath(models.Model):
    _name = 'vd.learning.path'
    _description = 'Lo trinh dao tao'
    _order = 'sequence, id'

    name = fields.Char(string='Tên lộ trình', required=True, default='Lộ trình mới')
    zone = fields.Selection(
        [('sales', 'Đào tạo nhân viên'),
         ('leader', 'Đào tạo trưởng nhóm')],
        string='Khu đào tạo', required=True, default='sales')
    sequence = fields.Integer(string='Thứ tự', default=10)
    course_ids = fields.One2many('slide.channel', 'vd_path_id', string='Khóa học')
