# -*- coding: utf-8 -*-
"""SỬA TAY số liệu "Tỷ lệ xin số" theo ngày.

Số auto-đếm từ Pancake đôi khi lệch thực tế (khách TikTok lưu nhầm page, dữ liệu
đồng bộ muộn...). Admin/quản lý được sửa tay con số "Khách nhắn" và "Xin được số"
cho từng ngày qua icon cây bút trên biểu đồ. Khi có dòng sửa tay cho 1 ngày, báo
cáo dùng số sửa tay thay cho số auto-đếm.
"""
from odoo import api, fields, models


class VdPancakeRateOverride(models.Model):
    _name = 'vd.pancake.rate.override'
    _description = 'Sửa tay số liệu tỷ lệ xin số theo ngày'
    _order = 'day desc'

    day = fields.Date(string='Ngày', required=True, index=True)
    khach_nhan = fields.Integer(string='Khách nhắn')
    xin_duoc = fields.Integer(string='Xin được số')

    _sql_constraints = [
        ('uniq_day', 'unique(day)', 'Mỗi ngày chỉ có 1 dòng sửa tay.'),
    ]

    def _vd_can_edit(self):
        u = self.env.user
        return bool(
            u._is_admin()
            or u.has_group('base.group_system')
            or u.has_group('sales_team.group_sale_manager')
            or u.has_group('vd_crm_lead.vd_crm_group_team_leader')
        )

    @api.model
    def _vd_overrides_map(self):
        """Trả {iso_date: {'khach': n, 'xin': m}} cho mọi ngày đã sửa tay."""
        res = {}
        for r in self.sudo().search([]):
            res[r.day.isoformat()] = {'khach': r.khach_nhan, 'xin': r.xin_duoc}
        return res
