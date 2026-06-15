# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    # Khu vuc theo chuc vu — quyet dinh khoa hoc hien o KHU nao tren trang tong quan.
    vd_role_zone = fields.Selection(
        [('sales', 'Nhan vien kinh doanh'),
         ('leader', 'Truong nhom')],
        string='Khu vuc chuc vu', default='sales', index=True,
        help='Khoa hoc nay thuoc khu nao tren trang Tong quan eLearning theo chuc vu.')

    # Thu tu trong lo trinh hoc (admin keo-tha de sap xep).
    vd_seq = fields.Integer(string='Thu tu lo trinh', default=10, index=True)

    # ------------------------------------------------------------------
    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

    @api.model
    def vd_get_overview(self):
        """Du lieu cho trang OWL.
        - 2 khu theo chuc vu (NV kinh doanh / Truong nhom).
        - Moi khu: nhan vien nhom theo phong ban (leader vang len dau) + lo trinh khoa hoc."""
        Users = self.env['res.users']
        internal = Users.search([('share', '=', False), ('active', '=', True)])

        def zone_employees(roles):
            us = internal.filtered(lambda u: u.vd_crm_role in roles)
            us = us.sorted(lambda u: (u.vd_team_label or 'KHAC', u.name or ''))
            return [{'id': u.id, 'name': u.name or ''} for u in us]

        def course_list(zone):
            chans = self.search([('vd_role_zone', '=', zone)], order='vd_seq, id')
            return [{
                'id': c.id,
                'name': c.name or '',
                'total_slides': c.total_slides,
                'has_image': bool(c.image_512),
                'published': bool(c.is_published),
            } for c in chans]

        return {
            'is_admin': self._vd_is_admin(),
            'zones': [
                {'key': 'sales', 'title': 'NHAN VIEN KINH DOANH',
                 'employees': zone_employees(['employee', 'team_leader', 'collaborator']),
                 'courses': course_list('sales')},
                {'key': 'leader', 'title': 'TRUONG NHOM',
                 'employees': zone_employees(['team_leader']),
                 'courses': course_list('leader')},
            ],
        }

    @api.model
    def vd_save_order(self, zone, ordered_ids):
        """Luu lai thu tu lo trinh sau khi admin keo-tha. Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc sap xep lo trinh khoa hoc.')
        seq = 10
        for cid in ordered_ids:
            self.browse(cid).write({'vd_seq': seq, 'vd_role_zone': zone})
            seq += 10
        return True
