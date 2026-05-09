"""3-tier role system for VINADUY CRM.

Maps a single Selection field to Odoo's standard groups, plus auto-strips
"noisy" groups (recruitment, accounting, website…) for non-admin roles so
NV/TP only see the menus they actually need.

Roles:
    admin → base.group_system + sale_manager   (full system, sees everything)
    tp    → sale_manager only                  (all leads, no system access)
    nv    → sale_salesman only                 (own leads, minimal menu)
    none  → no CRM groups
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


# Groups that NV / TP don't need — explicitly removed when role is set.
# Admin keeps these (they need full system access).
NOISY_GROUPS = [
    'base.group_no_one',
    'account.group_delivery_invoice_address',
    'account.group_account_invoice',
    'account.group_account_manager',
    'account.group_validate_bank_account',
    'base.group_allow_export',
    'base.group_erp_manager',
    'base.group_partner_manager',
    'base.group_sanitize_override',
    'hr.group_hr_user',
    'hr.group_hr_manager',
    'hr_recruitment.group_applicant_cv_display',
    'hr_recruitment.group_hr_recruitment_user',
    'hr_recruitment.group_hr_recruitment_interviewer',
    'hr_recruitment.group_hr_recruitment_manager',
    'mail.group_mail_canned_response_admin',
    'mail.group_mail_template_editor',
    'product.group_product_manager',
    'spreadsheet_dashboard.group_dashboard_manager',
    'website.group_website_designer',
    'website.group_website_restricted_editor',
    'website_slides.group_website_slides_manager',
    'website_slides.group_website_slides_officer',
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    vd_crm_role = fields.Selection([
        ('none', 'Không có quyền CRM'),
        ('nv', 'Nhân viên — chỉ xem KH của mình'),
        ('tp', 'Trưởng phòng — xem/sửa tất cả KH'),
        ('admin', 'Admin — toàn quyền hệ thống'),
    ], string='Vai trò',
        compute='_compute_vd_crm_role',
        inverse='_inverse_vd_crm_role',
        store=False,
        help='Gán nhanh quyền theo 3 vai trò chuẩn của VINADUY CRM. '
             'Khi đổi sang NV/TP, các group thừa (kế toán, tuyển dụng, web…) sẽ tự được gỡ.',
    )

    @api.model
    def _vd_role_groups(self):
        """Return refs to the 3 sales-related groups."""
        return {
            'sale_manager': self.env.ref('sales_team.group_sale_manager'),
            'sale_all_leads': self.env.ref('sales_team.group_sale_salesman_all_leads'),
            'sale_salesman': self.env.ref('sales_team.group_sale_salesman'),
            'system': self.env.ref('base.group_system'),
        }

    def _compute_vd_crm_role(self):
        g = self._vd_role_groups()
        for u in self:
            if g['system'] in u.groups_id:
                u.vd_crm_role = 'admin'
            elif g['sale_manager'] in u.groups_id:
                u.vd_crm_role = 'tp'
            elif g['sale_salesman'] in u.groups_id:
                u.vd_crm_role = 'nv'
            else:
                u.vd_crm_role = 'none'

    def _inverse_vd_crm_role(self):
        # Only admins / sales managers may change roles. Without this,
        # any user with write access to res.users could escalate themselves.
        if not (
            self.env.user.has_group('base.group_system')
            or self.env.user.has_group('sales_team.group_sale_manager')
        ):
            raise UserError(_('Chỉ Admin / Trưởng phòng mới được phân quyền.'))

        g = self._vd_role_groups()
        for u in self:
            ops = []

            # Always remove all 3 sales groups + system first (clean slate
            # so role downgrade works — implied groups handle re-adding).
            for grp_key in ('sale_manager', 'sale_all_leads', 'sale_salesman', 'system'):
                ops.append((3, g[grp_key].id))

            # Strip noisy groups for non-admin roles
            if u.vd_crm_role in ('nv', 'tp', 'none'):
                for xmlid in NOISY_GROUPS:
                    grp = self.env.ref(xmlid, raise_if_not_found=False)
                    if grp:
                        ops.append((3, grp.id))

            # Add the role's groups
            if u.vd_crm_role == 'admin':
                ops.append((4, g['system'].id))
                ops.append((4, g['sale_manager'].id))
            elif u.vd_crm_role == 'tp':
                ops.append((4, g['sale_manager'].id))
            elif u.vd_crm_role == 'nv':
                ops.append((4, g['sale_salesman'].id))
            # 'none': no add — user has zero CRM access

            u.sudo().write({'groups_id': ops})
