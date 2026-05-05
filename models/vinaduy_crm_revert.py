from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VinaduyCrmRevertRequest(models.Model):
    _name = 'vinaduy.crm.revert.request'
    _description = 'Yêu cầu lùi trạng thái lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade')
    requester_id = fields.Many2one('res.users', string='Người yêu cầu', required=True,
                                   default=lambda self: self.env.user)
    from_stage_id = fields.Many2one('crm.stage', string='Từ trạng thái', required=True)
    to_stage_id = fields.Many2one('crm.stage', string='Lùi về trạng thái', required=True)
    reason = fields.Text(string='Lý do', required=True)
    state = fields.Selection(
        [('pending', 'Chờ duyệt'),
         ('approved', 'Đã duyệt'),
         ('rejected', 'Từ chối')],
        default='pending', required=True, tracking=True,
    )
    approver_id = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    approver_note = fields.Text(string='Ghi chú admin')

    def action_approve(self):
        for req in self:
            if req.state != 'pending':
                continue
            req.write({'state': 'approved', 'approver_id': self.env.user.id})
            # Thực hiện lùi stage
            req.lead_id.with_context(vinaduy_skip_stage_check=True).write({
                'stage_id': req.to_stage_id.id,
            })
            req.lead_id.message_post(
                body=_(
                    '✅ <b>Admin đã DUYỆT</b> yêu cầu lùi trạng thái từ "%(from)s" về "%(to)s" (do %(req)s yêu cầu).<br/>Lý do: %(reason)s',
                    **{'from': req.from_stage_id.display_name,
                       'to': req.to_stage_id.display_name,
                       'req': req.requester_id.display_name,
                       'reason': req.reason}
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        for req in self:
            if req.state != 'pending':
                continue
            req.write({'state': 'rejected', 'approver_id': self.env.user.id})
            req.lead_id.message_post(
                body=_(
                    '❌ <b>Admin đã TỪ CHỐI</b> yêu cầu lùi trạng thái về "%(to)s".<br/>Lý do yêu cầu: %(reason)s',
                    **{'to': req.to_stage_id.display_name, 'reason': req.reason}
                ),
                subtype_xmlid='mail.mt_note',
            )
