"""Wizard hẹn ngày gọi lại cho NV — chọn preset nhanh hoặc datetime tự do,
ghi chú optional. Ghi vào crm.lead.callback_date + message_post."""

from datetime import time

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _tomorrow_9am(env):
    """Mai 9h sáng giờ user (UTC-aware để write vào Datetime field)."""
    now_user = fields.Datetime.context_timestamp(env.user, fields.Datetime.now())
    tomorrow = (now_user + relativedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0,
    )
    return tomorrow.astimezone(tz=None).replace(tzinfo=None)


class VdLeadCallbackWizard(models.TransientModel):
    _name = 'vd.lead.callback.wizard'
    _description = 'Wizard hẹn ngày gọi lại KH'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)
    current_callback = fields.Datetime(
        related='lead_id.callback_date', readonly=True,
        string='Lịch hẹn hiện tại',
    )

    quick_preset = fields.Selection([
        ('tomorrow', '☀️ Mai 9h sáng'),
        ('3d', '📅 3 ngày sau'),
        ('1w', '📅 1 tuần sau'),
        ('2w', '📅 2 tuần sau'),
        ('1m', '🗓️ 1 tháng sau'),
        ('custom', '🎯 Tự chọn ngày giờ'),
    ], string='Preset nhanh', required=True, default='tomorrow')

    callback_date = fields.Datetime(
        string='Ngày giờ gọi lại', required=True,
        help='Tự fill theo preset hoặc chọn tay khi preset = Tự chọn.',
    )
    note = fields.Text(
        string='Ghi chú (optional)',
        help='Lý do hẹn gọi lại / nội dung cần chốt với KH khi gọi.',
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if 'callback_date' in fields_list and not vals.get('callback_date'):
            vals['callback_date'] = _tomorrow_9am(self.env)
        return vals

    @api.onchange('quick_preset')
    def _onchange_quick_preset(self):
        if not self.quick_preset or self.quick_preset == 'custom':
            return
        now = fields.Datetime.now()
        now_user = fields.Datetime.context_timestamp(self.env.user, now)
        mapping = {
            'tomorrow': relativedelta(days=1),
            '3d': relativedelta(days=3),
            '1w': relativedelta(weeks=1),
            '2w': relativedelta(weeks=2),
            '1m': relativedelta(months=1),
        }
        target_user = (now_user + mapping[self.quick_preset]).replace(
            hour=9, minute=0, second=0, microsecond=0,
        )
        self.callback_date = target_user.astimezone(tz=None).replace(tzinfo=None)

    def action_confirm_callback(self):
        self.ensure_one()
        if not self.callback_date:
            raise UserError(_('Vui lòng chọn ngày giờ gọi lại.'))
        if self.callback_date <= fields.Datetime.now():
            raise UserError(_('Ngày hẹn phải ở tương lai.'))

        old = self.lead_id.callback_date
        self.lead_id.with_context(mail_notrack=True).write({
            'callback_date': self.callback_date,
        })

        local_str = fields.Datetime.context_timestamp(
            self.env.user, self.callback_date,
        ).strftime('%H:%M %d/%m/%Y')
        body_lines = [
            _("📅 <b>Đã hẹn gọi lại</b>: %s") % local_str,
        ]
        if old:
            old_local = fields.Datetime.context_timestamp(
                self.env.user, old,
            ).strftime('%H:%M %d/%m/%Y')
            body_lines.insert(0, _("(Lịch cũ: %s)") % old_local)
        if self.note and self.note.strip():
            body_lines.append(_("<b>Ghi chú:</b> %s") % self.note.strip())

        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body='<br/>'.join(body_lines),
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_clear_callback(self):
        """Hủy lịch hẹn hiện tại (set callback_date = False)."""
        self.ensure_one()
        if not self.lead_id.callback_date:
            return {'type': 'ir.actions.act_window_close'}
        old_local = fields.Datetime.context_timestamp(
            self.env.user, self.lead_id.callback_date,
        ).strftime('%H:%M %d/%m/%Y')
        self.lead_id.with_context(mail_notrack=True).write({
            'callback_date': False,
        })
        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body=_("🗑️ Đã hủy lịch hẹn gọi lại (cũ: %s).") % old_local,
        )
        return {'type': 'ir.actions.act_window_close'}
