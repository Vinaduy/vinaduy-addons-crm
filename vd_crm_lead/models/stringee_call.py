"""Extend stringee.call with a back-link to the (standard) crm.lead, and update
lead activity stats when a call reaches a terminal state.
"""
from odoo import api, fields, models


class StringeeCall(models.Model):
    _inherit = 'stringee.call'

    lead_id = fields.Many2one('crm.lead', string='Khách hàng', ondelete='set null', index=True)
    lead_stage_name = fields.Char(related='lead_id.stage_id.name', string='Stage KH')
    lead_probability = fields.Float(related='lead_id.probability', string='Tỉ lệ chốt')

    def action_open_lead(self):
        self.ensure_one()
        if not self.lead_id:
            from odoo.exceptions import UserError
            raise UserError("Cuộc gọi này chưa được link với khách hàng nào.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_lead_activity()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'state', 'duration', 'callee_number'} & vals.keys():
            self._sync_lead_activity()
        return result

    def _sync_lead_activity(self):
        """Push call info back to the matched lead so the dashboard can rank it.

        For inbound calls from numbers we've never seen, auto-create a 'Khách mới'
        lead so the call doesn't fall on the floor. Outbound calls without a match
        are left unlinked — they were placed manually and the agent owns linking.
        """
        Lead = self.env['crm.lead']
        for call in self:
            lead = call.lead_id
            phone = call.callee_number if call.direction == 'outbound' else call.caller_number
            if not lead and phone:
                lead = Lead.search([
                    '|', ('phone', '=', phone), ('mobile', '=', phone),
                    ('user_id', '=', call.user_id.id or self.env.user.id),
                ], limit=1, order='create_date desc')
                if not lead:
                    lead = Lead.search([
                        '|', ('phone', '=', phone), ('mobile', '=', phone),
                    ], limit=1, order='create_date desc')
                if not lead and call.direction == 'inbound':
                    new_stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False)
                    lead = Lead.create({
                        'name': f'KH gọi đến {phone}',
                        'phone': phone,
                        'user_id': call.user_id.id or False,
                        'type': 'opportunity',
                        'stage_id': new_stage.id if new_stage else False,
                        'description': 'Tự động tạo từ cuộc gọi đến.',
                    })
                if lead:
                    call.with_context(skip_sync=True).lead_id = lead.id
            if not lead:
                continue
            vals = {}
            if not lead.last_call_date or (call.start_time and call.start_time > lead.last_call_date):
                vals['last_call_date'] = call.start_time
            if call.state == 'answered' or (call.state == 'ended' and call.duration > 0):
                vals['last_answered_date'] = call.answer_time or call.start_time
                vals['no_answer_streak'] = 0
            elif call.state in ('no_answer', 'busy', 'declined', 'cancelled', 'failed'):
                vals['no_answer_streak'] = lead.no_answer_streak + 1
            vals['call_count'] = lead.call_count + (0 if call._origin.id else 1)
            if vals:
                lead.write(vals)
