"""Wizard CHUYỂN KH cho NV khác (user spec 2026-07-26).

Admin / người chia số / trưởng nhóm bấm nút "Chuyển" trên header form KH →
mở hộp thoại chọn NV mới → bấm "Chuyển ngay" là đổi user_id quản lý KH.
Quyền khớp can_user_reassign (giống write() + dashboard_bulk_reassign)."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class VdLeadReassignWizard(models.TransientModel):
    _name = 'vd.lead.reassign.wizard'
    _description = 'Chuyển khách hàng cho nhân viên khác'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True,
                            string='Khách hàng')
    current_user_id = fields.Many2one(
        related='lead_id.user_id', readonly=True,
        string='NV đang phụ trách')
    new_user_id = fields.Many2one(
        'res.users', string='Chuyển cho NV', required=True,
        domain=[('share', '=', False), ('active', '=', True)],
        help='Chọn nhân viên sẽ tiếp nhận và quản lý khách hàng này.')

    def action_do_reassign(self):
        """Đổi NV quản lý KH sau khi kiểm tra quyền."""
        self.ensure_one()
        role_model = self.env['vd.crm.role.config'].sudo()
        if not (self.env.user._is_superuser()
                or role_model.can_user_reassign(self.env.user)):
            raise AccessError(_(
                'Bạn không có quyền chuyển KH cho NV khác. '
                'Chỉ Admin, người chia số hoặc trưởng nhóm mới được làm.'))
        if not self.new_user_id:
            raise UserError(_('Hãy chọn nhân viên nhận khách.'))
        lead = self.lead_id
        old_user = lead.user_id
        if old_user.id == self.new_user_id.id:
            raise UserError(_('Khách hàng này đang do "%s" phụ trách rồi.')
                            % (self.new_user_id.name))
        # Đã kiểm tra quyền ở trên → bypass check trong write() + record rule.
        lead.sudo().with_context(vd_skip_reassign_check=True).write(
            {'user_id': self.new_user_id.id})
        # Ghi chú vào chatter (user_id đã có tracking, đây là note rõ ràng thêm).
        lead.message_post(body=_(
            '🔄 <b>Chuyển KH</b> từ <b>%s</b> sang <b>%s</b> — thực hiện bởi %s.'
        ) % (old_user.name or '(chưa giao)', self.new_user_id.name,
             self.env.user.name))
        return {'type': 'ir.actions.act_window_close'}
