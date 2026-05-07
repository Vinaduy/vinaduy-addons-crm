"""Extend stringee.call with a back-link to the lead, and update lead activity stats
when the call reaches a terminal state.
"""
from odoo import api, fields, models


class StringeeCall(models.Model):
    _inherit = 'stringee.call'

    lead_id = fields.Many2one('vd.crm.lead', string='Khách hàng', ondelete='set null', index=True)

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
        """Push call info back to the matched lead so the dashboard can rank it."""
        for call in self:
            lead = call.lead_id
            if not lead and call.callee_number:
                lead = self.env['vd.crm.lead'].search(
                    [('phone', '=', call.callee_number), ('user_id', '=', call.user_id.id or self.env.user.id)],
                    limit=1, order='create_date desc',
                )
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
