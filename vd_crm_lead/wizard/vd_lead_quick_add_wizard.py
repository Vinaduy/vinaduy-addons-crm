# -*- coding: utf-8 -*-
"""Quick-add lead wizard — popup nhỏ chỉ điền tên + SĐT.

Dùng từ nút "Thêm KH thủ công" trên dashboard. Sau khi tạo:
- Nếu user là Manager/Admin → round-robin chọn NV nhận
- Nếu user là NV → tự gán cho chính mình
- Mở luôn form lead vừa tạo để bổ sung intake info
"""
from odoo import models, fields, api, _


class VdLeadQuickAddWizard(models.TransientModel):
    _name = 'vd.lead.quick.add.wizard'
    _description = 'Thêm KH nhanh (chỉ tên + SĐT)'

    name = fields.Char(
        string='Tên khách hàng',
        required=True,
        help='Vd: Nguyễn Văn An — sẽ dùng cho cả lead name và partner_name.',
    )
    phone = fields.Char(
        string='Số điện thoại',
        required=True,
        help='Vd: 0901234567 — bắt buộc để NV gọi được.',
    )

    def action_create_lead(self):
        """Tạo lead + auto-assign + mở form lead."""
        self.ensure_one()
        Lead = self.env['crm.lead']
        ResUsers = self.env['res.users']

        # Quyết định assignee
        user = self.env.user
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')  # leader/deputy/admin
        if is_leader:
            # Leader trở lên → round-robin chia cho NV thuần
            picked = ResUsers.sudo()._vd_pick_next_assignee()
            assignee = picked or user  # fallback chính mình nếu không có NV eligible
        else:
            # NV → tự gán cho mình (ghi nhận KH gọi đến trực tiếp)
            assignee = user

        lead = Lead.with_context(vd_skip_reassign_check=True).create({
            'name': self.name,
            'partner_name': self.name,
            'phone': self.phone,
            'user_id': assignee.id,
            'type': 'lead',
        })

        # Đóng popup + show notification + reload trang dashboard hiện tại
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã tạo KH'),
                'message': _('%s (%s) — phụ trách: %s') % (lead.name, self.phone, assignee.name),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
