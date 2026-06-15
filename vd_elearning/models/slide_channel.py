# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    # Khu vuc theo chuc vu — quyet dinh khoa hoc hien o KHU nao tren trang tong quan.
    vd_role_zone = fields.Selection(
        [('sales', 'Nhan vien kinh doanh'),
         ('leader', 'Truong nhom')],
        string='Khu vuc chuc vu', default='sales', index=True,
        help='Khoa hoc nay thuoc khu nao tren trang Tong quan eLearning theo chuc vu.')

    @api.model
    def vd_get_overview(self):
        """Tra du lieu cho trang OWL: 2 khu (NV kinh doanh / Truong nhom),
        moi khu gom danh sach nhan vien (theo vd_crm_role) + danh sach khoa hoc."""
        Users = self.env['res.users']
        internal = Users.search([('share', '=', False), ('active', '=', True)])

        def emp_list(role):
            us = internal.filtered(lambda u: u.vd_crm_role == role)
            return [{
                'id': u.id,
                'name': u.name or '',
                'team': u.vd_team_label or '',
            } for u in us.sorted('name')]

        def course_list(zone):
            chans = self.search([('vd_role_zone', '=', zone)], order='id')
            return [{
                'id': c.id,
                'name': c.name or '',
                'total_slides': c.total_slides,
                'has_image': bool(c.image_512),
                'published': bool(c.is_published),
            } for c in chans]

        return [
            {'key': 'sales', 'title': 'NHAN VIEN KINH DOANH',
             'employees': emp_list('employee'), 'courses': course_list('sales')},
            {'key': 'leader', 'title': 'TRUONG NHOM',
             'employees': emp_list('team_leader'), 'courses': course_list('leader')},
        ]
