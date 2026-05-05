from odoo import _, fields, models


class VinaduyCrmCloseWizard(models.TransientModel):
    _name = 'vinaduy.crm.close.wizard'
    _description = 'Wizard nhập lý do đóng lead'

    lead_id = fields.Many2one('crm.lead', required=True)
    close_type = fields.Selection(
        [('no_need', 'Khách không có nhu cầu'),
         ('cancelled', 'Khách hủy')],
        required=True,
    )
    reason = fields.Text(string='Lý do', required=True)

    def action_confirm(self):
        self.ensure_one()
        # Lưu lý do vào lead
        self.lead_id.write({'vd_close_reason': self.reason})
        # Gọi action đóng tương ứng
        if self.close_type == 'no_need':
            return self.lead_id.action_vinaduy_mark_no_need()
        elif self.close_type == 'cancelled':
            return self.lead_id.action_vinaduy_mark_cancelled()
