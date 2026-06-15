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

        # Map khoa hoc theo zone (theo thu tu lo trinh).
        zone_recs = {
            'sales': self.search([('vd_role_zone', '=', 'sales')], order='vd_seq, id'),
            'leader': self.search([('vd_role_zone', '=', 'leader')], order='vd_seq, id'),
        }

        # ----- Tien do hoc cua tung NV de gan avatar vao dung "cua ai" -----
        SCP = self.env['slide.channel.partner'].sudo()
        all_chan_ids = (zone_recs['sales'] | zone_recs['leader']).ids
        progress = {}  # partner_id -> {channel_id: member_status}
        if all_chan_ids and internal:
            for p in SCP.search([('partner_id', 'in', internal.partner_id.ids),
                                 ('channel_id', 'in', all_chan_ids)]):
                progress.setdefault(p.partner_id.id, {})[p.channel_id.id] = p.member_status

        def current_course_id(user, recs):
            """Khoa hoc NV dang dung ('cua ai' hien tai)."""
            if not recs:
                return False
            ids = recs.ids
            mine = progress.get(user.partner_id.id, {})
            if not mine:
                return ids[0]                       # chua hoc gi -> dung o cua dau
            for cid in ids:                          # cua dang hoc dang do
                if mine.get(cid) in ('joined', 'ongoing'):
                    return cid
            for cid in ids:                          # cua tiep theo chua hoan thanh
                if mine.get(cid) != 'completed':
                    return cid
            return ids[-1]                           # da pha dao het

        def zone_employees(roles, recs):
            us = internal.filtered(lambda u: u.vd_crm_role in roles)
            us = us.sorted(lambda u: (u.vd_team_label or 'KHAC', u.name or ''))
            return [{'id': u.id, 'name': u.name or '',
                     'course_id': current_course_id(u, recs)} for u in us]

        def course_list(recs):
            return [{
                'id': c.id,
                'name': c.name or '',
                'total_slides': c.total_slides,
                'has_image': bool(c.image_512),
                'published': bool(c.is_published),
            } for c in recs]

        # Thong tin user hien tai — NV/CTV/TN dang nhap se vao thang giao dien cua minh.
        u = self.env.user
        role = u.vd_crm_role
        my_zone = ('sales' if role in ('employee', 'collaborator')
                   else 'leader' if role == 'team_leader' else False)
        me = ({'id': u.id, 'name': u.name or '', 'zone_key': my_zone,
               'course_id': current_course_id(u, zone_recs[my_zone])}
              if my_zone else False)

        return {
            'is_admin': self._vd_is_admin(),
            'me': me,
            'zones': [
                {'key': 'sales', 'title': 'NHAN VIEN KINH DOANH',
                 'employees': zone_employees(['employee', 'team_leader', 'collaborator'], zone_recs['sales']),
                 'courses': course_list(zone_recs['sales'])},
                {'key': 'leader', 'title': 'TRUONG NHOM',
                 'employees': zone_employees(['team_leader'], zone_recs['leader']),
                 'courses': course_list(zone_recs['leader'])},
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
