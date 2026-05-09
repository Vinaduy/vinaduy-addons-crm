"""Friendly wrapper over Odoo's standard CRM groups.

Exposes a single Selection `vd_crm_role` so admins can assign permissions
from a simple list view without navigating Settings → Users → Access Rights.

Roles map 1:1 to standard `sales_team` groups — no custom record rules,
so existing Odoo CRM security still applies.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    vd_crm_role = fields.Selection([
        ('none', 'Không có quyền CRM'),
        ('own', 'NV thường — chỉ xem KH của mình'),
        ('all', 'NV xem tất cả KH'),
        ('admin', 'Quản trị CRM — toàn quyền'),
    ], string='Quyền CRM',
        compute='_compute_vd_crm_role',
        inverse='_inverse_vd_crm_role',
        store=False,
        help='Gán nhanh quyền CRM. Tương ứng với group Sales chuẩn của Odoo.',
    )

    @api.model
    def _vd_crm_groups(self):
        return {
            'admin': self.env.ref('sales_team.group_sale_manager'),
            'all': self.env.ref('sales_team.group_sale_salesman_all_leads'),
            'own': self.env.ref('sales_team.group_sale_salesman'),
        }

    def _compute_vd_crm_role(self):
        groups = self._vd_crm_groups()
        for u in self:
            if groups['admin'] in u.groups_id:
                u.vd_crm_role = 'admin'
            elif groups['all'] in u.groups_id:
                u.vd_crm_role = 'all'
            elif groups['own'] in u.groups_id:
                u.vd_crm_role = 'own'
            else:
                u.vd_crm_role = 'none'

    def _inverse_vd_crm_role(self):
        # Only admins / sales managers may change roles. Without this guard,
        # a user with write access to res.users (e.g. HR) could escalate
        # themselves by ticking the field.
        if not (
            self.env.user.has_group('base.group_system')
            or self.env.user.has_group('sales_team.group_sale_manager')
        ):
            raise UserError(_('Chỉ Admin / Quản trị Sales mới được phân quyền CRM.'))

        groups = self._vd_crm_groups()
        # Drop all 3 sales groups, then add the one matching the chosen role.
        # Implied groups handle the hierarchy (admin → all → own).
        remove_ops = [(3, g.id) for g in groups.values()]
        for u in self:
            ops = list(remove_ops)
            target = groups.get(u.vd_crm_role)
            if target:
                ops.append((4, target.id))
            u.sudo().write({'groups_id': ops})
