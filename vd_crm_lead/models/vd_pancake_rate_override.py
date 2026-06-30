# -*- coding: utf-8 -*-
"""SỬA TAY số liệu "Tỷ lệ xin số" theo ngày.

Số auto-đếm từ Pancake đôi khi lệch thực tế (khách TikTok lưu nhầm page, dữ liệu
đồng bộ muộn...). Admin/quản lý được sửa tay con số "Khách nhắn" và "Xin được số"
cho từng ngày qua icon cây bút trên biểu đồ. Khi có dòng sửa tay cho 1 ngày, báo
cáo dùng số sửa tay thay cho số auto-đếm.
"""
from odoo import api, fields, models
from odoo.exceptions import AccessError


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
    def vd_save_rate_override(self, day, khach_nhan, xin_duoc):
        """Lưu/sửa số liệu tay cho 1 ngày. day = 'YYYY-MM-DD'. Chỉ admin/quản lý."""
        if not self._vd_can_edit():
            raise AccessError('Chỉ admin / quản lý mới được sửa số liệu.')
        d = fields.Date.to_date(day)
        if not d:
            return False
        kn = max(0, int(khach_nhan or 0))
        xd = max(0, int(xin_duoc or 0))
        rec = self.sudo().search([('day', '=', d)], limit=1)
        if rec:
            rec.write({'khach_nhan': kn, 'xin_duoc': xd})
        else:
            self.sudo().create({'day': d, 'khach_nhan': kn, 'xin_duoc': xd})
        return True

    @api.model
    def vd_clear_rate_override(self, day):
        """Xoá dòng sửa tay → quay lại số auto-đếm."""
        if not self._vd_can_edit():
            raise AccessError('Chỉ admin / quản lý mới được sửa số liệu.')
        d = fields.Date.to_date(day)
        if d:
            self.sudo().search([('day', '=', d)]).unlink()
        return True

    @api.model
    def _vd_overrides_map(self):
        """Trả {iso_date: {'khach': n, 'xin': m}} cho mọi ngày đã sửa tay."""
        res = {}
        for r in self.sudo().search([]):
            res[r.day.isoformat()] = {'khach': r.khach_nhan, 'xin': r.xin_duoc}
        return res
