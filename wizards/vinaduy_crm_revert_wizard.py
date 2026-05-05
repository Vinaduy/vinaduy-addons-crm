from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VinaduyCrmRevertWizard(models.TransientModel):
    _name = 'vinaduy.crm.revert.wizard'
    _description = 'Wizard yêu cầu lùi trạng thái'

    lead_id = fields.Many2one('crm.lead', required=True)
    current_stage_id = fields.Many2one('crm.stage', required=True, readonly=True)
    to_stage_id = fields.Many2one(
        'crm.stage', string='Lùi về trạng thái', required=True,
        domain="[('sequence', '<', current_sequence)]",
    )
    current_sequence = fields.Integer(related='current_stage_id.sequence')
    reason = fields.Text(string='Lý do lùi', required=True)

    def action_submit(self):
        self.ensure_one()
        if self.to_stage_id.sequence >= self.current_stage_id.sequence:
            raise UserError(_('Trạng thái lùi phải trước trạng thái hiện tại.'))
        request = self.env['vinaduy.crm.revert.request'].create({
            'lead_id': self.lead_id.id,
            'requester_id': self.env.user.id,
            'from_stage_id': self.current_stage_id.id,
            'to_stage_id': self.to_stage_id.id,
            'reason': self.reason,
        })
        self.lead_id.message_post(
            body=_(
                '🔄 <b>%(user)s</b> đã gửi yêu cầu lùi trạng thái từ "%(from)s" về "%(to)s".<br/>Lý do: %(reason)s<br/>Đang chờ admin duyệt.',
                user=self.env.user.display_name,
                **{'from': self.current_stage_id.display_name,
                   'to': self.to_stage_id.display_name,
                   'reason': self.reason}
            ),
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Đã gửi yêu cầu',
                'message': 'Yêu cầu lùi trạng thái đã gửi cho admin duyệt.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
