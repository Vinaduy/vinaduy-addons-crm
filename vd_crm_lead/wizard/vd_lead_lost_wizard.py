"""Wizard hỏi lý do khi NV đánh dấu Khách KHÔNG có nhu cầu.
Sau khi NV nhập lý do + xác nhận → set stage = lost + lưu lý do."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdLeadLostWizard(models.TransientModel):
    _name = 'vd.lead.lost.wizard'
    _description = 'Wizard đánh dấu khách không có nhu cầu'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)

    reason_category = fields.Selection([
        ('no_budget', '💸 Không đủ ngân sách'),
        ('not_ready', '⏰ Chưa sẵn sàng / chưa khởi công'),
        ('competitor', '🏗️ Đã chọn bên khác'),
        ('postpone', '🕐 Hoãn dự án vô thời hạn'),
        ('cant_contact', '📵 Không liên lạc được nhiều lần'),
        ('wrong_lead', '❌ Sai số / nhầm lead'),
        ('other', '🔖 Lý do khác'),
    ], string='Nhóm lý do', required=True, default='no_budget')

    reason_detail = fields.Text(
        string='Chi tiết / ghi chú', required=True,
        help='Mô tả cụ thể vì sao KH không có nhu cầu. Càng chi tiết càng giúp '
             'phân tích, sau này có thể call lại nếu hoàn cảnh KH đổi.',
    )

    callback_3m = fields.Boolean(
        string='Đặt lịch gọi lại sau 3 tháng?',
        help='Nếu lý do là tài chính / chưa sẵn sàng → có thể gọi lại sau 3 tháng.',
    )

    def action_confirm_lost(self):
        """Set stage lead = lost + lưu lý do + tạo callback nếu cần."""
        self.ensure_one()
        if not self.reason_detail or not self.reason_detail.strip():
            raise UserError(_('Vui lòng nhập chi tiết lý do.'))

        lost_stage = self.env.ref('vd_crm_lead.stage_lost', raise_if_not_found=False)
        if not lost_stage:
            lost_stage = self.env['crm.stage'].search([('code', '=', 'lost')], limit=1)
        if not lost_stage:
            raise UserError(_('Không tìm thấy stage "Khách hủy".'))

        # Đóng gói lý do thành 1 chuỗi
        cat_label = dict(self._fields['reason_category'].selection).get(
            self.reason_category, self.reason_category
        )
        full_reason = f'[{cat_label}] {self.reason_detail.strip()}'

        old_stage = self.lead_id.stage_id.name or ''
        vals = {
            'stage_id': lost_stage.id,
            'vd_lost_reason': full_reason,
            'vd_lost_date': fields.Datetime.now(),
            'vd_lost_user_id': self.env.user.id,
            'vd_lost_is_auto': False,
        }

        # Đặt callback 3 tháng (nếu chọn) — không archive ngay để cron có thể nhắc
        from dateutil.relativedelta import relativedelta
        if self.callback_3m:
            vals['callback_date'] = fields.Datetime.now() + relativedelta(months=3)

        # mail_notrack + tracking_disable → bỏ qua auto-email khi đổi stage
        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write(vals)
        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "❌ <b>Khách KHÔNG có nhu cầu</b> — chuyển từ <i>%s</i> sang "
                "<b>%s</b>.<br/><b>Lý do:</b> %s%s"
            ) % (
                old_stage,
                lost_stage.name,
                full_reason,
                _("<br/>📅 Đã đặt lịch gọi lại sau 3 tháng.") if self.callback_3m else "",
            ),
        )
        # Reload form parent → stage = Lost hiển thị ngay (không cần F5)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'main',
        }
