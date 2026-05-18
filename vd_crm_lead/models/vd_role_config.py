# -*- coding: utf-8 -*-
"""Cấu hình phân quyền CRM cho 4 vị trí: Nhân viên, Trưởng nhóm, Phó GĐ, Admin.

Module này lưu CHÍNH SÁCH phân quyền (admin xem/sửa qua UI).
Enforcement thực tế dùng kết hợp:
- Standard ir.model.access (CRUD per group) — load 1 lần khi cài/upgrade
- Standard ir.rule (record-level scope) — load 1 lần khi cài/upgrade
- Override write() trên crm.lead — runtime check quyền chuyển KH
"""
from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class VdCrmRoleConfig(models.Model):
    _name = 'vd.crm.role.config'
    _description = 'Cấu hình phân quyền CRM'
    _order = 'sequence, id'

    name = fields.Char(string='Tên vị trí', required=True)
    sequence = fields.Integer(default=10)
    role_code = fields.Selection([
        ('employee', '1. Nhân viên'),
        ('team_leader', '2. Trưởng nhóm'),
        ('deputy', '3. Phó Giám đốc'),
        ('admin', '4. Admin'),
    ], string='Mã vị trí', required=True)
    group_id = fields.Many2one(
        'res.groups', string='Security Group',
        required=True, ondelete='cascade',
        help='Group Odoo gán cho vị trí này. Để gán user vào vị trí, '
             'thêm họ vào group này (qua Settings > Users).')
    member_count = fields.Integer(
        'Số NV',
        compute='_compute_member_count', store=False)

    # ============ CRUD trên crm.lead ============
    can_read = fields.Boolean('👁️ Xem', default=True,
                               help='Cho phép NV đọc thông tin KH.')
    can_create = fields.Boolean('➕ Thêm mới', default=True,
                                 help='Cho phép tạo KH mới.')
    can_write = fields.Boolean('✏️ Sửa', default=True,
                                help='Cho phép sửa thông tin KH (trừ chuyển KH — xem can_reassign_lead).')
    can_unlink = fields.Boolean('🗑️ Xoá', default=False,
                                 help='Cho phép XOÁ KH khỏi hệ thống.')

    # ============ Quyền đặc biệt ============
    can_reassign_lead = fields.Boolean(
        '🔄 Gán/đổi/chuyển KH cho NV khác',
        default=False,
        help='Cho phép thay đổi field "Phụ trách" (user_id) → chuyển KH cho NV khác. '
             'Mặc định Trưởng nhóm + Phó GĐ + Admin có quyền này.')

    # ============ Phạm vi xem ============
    scope = fields.Selection([
        ('own', 'Chỉ KH của mình'),
        ('team', 'KH của cả team'),
        ('all', 'Tất cả KH trong hệ thống'),
    ], string='Phạm vi xem KH', default='own', required=True,
        help='Phạm vi xem dựa trên record rule. NV: own, Trưởng nhóm: team, Phó GĐ + Admin: all.')

    # ============ Ghi chú ============
    note = fields.Text('Ghi chú nội bộ')

    @api.depends('group_id', 'group_id.users')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.group_id.users) if rec.group_id else 0

    def action_view_members(self):
        """Mở danh sách NV trong vị trí này (popup)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('👥 NV trong vị trí: %s') % self.name,
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'domain': [('groups_id', '=', self.group_id.id)],
            'target': 'new',
            'context': {'create': False},
        }

    @api.model
    def get_role_for_user(self, user=None):
        """Trả role_code (cao nhất) của user. Dùng cho runtime check."""
        user = user or self.env.user
        if user.has_group('vd_crm_lead.vd_crm_group_admin'):
            return 'admin'
        if user.has_group('vd_crm_lead.vd_crm_group_deputy_director'):
            return 'deputy'
        if user.has_group('vd_crm_lead.vd_crm_group_team_leader'):
            return 'team_leader'
        if user.has_group('vd_crm_lead.vd_crm_group_employee'):
            return 'employee'
        return False

    @api.model
    def can_user_reassign(self, user=None):
        """Check user hiện tại có quyền chuyển KH không.
        Trả True nếu group user thuộc về có can_reassign_lead = True."""
        user = user or self.env.user
        if user.has_group('vd_crm_lead.vd_crm_group_admin'):
            return True
        # Tìm config cao nhất user thuộc về
        cfg = self.sudo().search([
            ('group_id', 'in', user.groups_id.ids),
        ], order='sequence desc', limit=1)
        return bool(cfg and cfg.can_reassign_lead)
