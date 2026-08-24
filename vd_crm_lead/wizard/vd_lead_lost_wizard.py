"""Wizard ĐỀ XUẤT HỦY — ĐƠN GIẢN HOÁ (user spec 2026-08-24):
Bỏ hết 4 nhóm lý do + form khai thác rườm rà. Khi bấm Hủy chỉ cần 1 ô ghi chú
lý do hủy. Submit → KH vào thùng rác (stage=lost), lý do lưu ở vd_lost_reason
và hiện lại khi xem KH hủy.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdLeadLostWizard(models.TransientModel):
    _name = 'vd.lead.lost.wizard'
    _description = 'Wizard đề xuất hủy khách'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)

    cancel_note = fields.Text(
        string='Lý do hủy',
        help='Ghi chú ngắn lý do hủy khách này (KH đã chọn bên khác, hủy kế '
             'hoạch xây, nhầm số...).',
    )

    def action_confirm_lost(self):
        """Set stage lead = lost + lưu lý do (ghi chú)."""
        self.ensure_one()
        # Chặn nếu NV đã tồn >= ngưỡng KH chờ duyệt hủy.
        self.lead_id._vd_check_cancel_block()
        note = (self.cancel_note or '').strip()
        if not note:
            raise UserError(_('Vui lòng ghi lý do hủy.'))

        lost_stage = self.env.ref('vd_crm_lead.stage_lost', raise_if_not_found=False)
        if not lost_stage:
            lost_stage = self.env['crm.stage'].search([('code', '=', 'lost')], limit=1)
        if not lost_stage:
            raise UserError(_('Không tìm thấy stage "Khách hủy".'))

        old_stage = self.lead_id.stage_id.name or ''
        vals = {
            'stage_id': lost_stage.id,
            'vd_lost_reason': note,
            'vd_lost_date': fields.Datetime.now(),
            'vd_lost_user_id': self.env.user.id,
            'vd_lost_is_auto': False,
            # Đề xuất hủy CHỜ admin duyệt — chưa archive.
            'vd_cancel_state': 'proposed',
            'vd_cancel_category': False,
        }
        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write(vals)
        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "🗑️ <b>ĐỀ XUẤT HỦY</b> — chuyển từ <i>%s</i> sang <b>%s</b>."
                "<br/><b>Lý do:</b> %s"
            ) % (old_stage, lost_stage.name, note),
        )
        return {'type': 'ir.actions.act_window_close'}
