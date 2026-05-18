"""Wizard ĐẶT LỊCH ký HĐ — khi KH đồng ý, NV setup ngày đi ký.
Logic: chỉ schedule, KHÔNG đổi stage. Khi NV thực sự ký xong + có cọc thì
mới mark lead = won (việc đó qua action riêng).
"""
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdContractSignWizard(models.TransientModel):
    _name = 'vd.contract.sign.wizard'
    _description = 'Wizard đặt lịch ký hợp đồng'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)
    quote_price_display = fields.Monetary(
        related='lead_id.vd_quote_price', readonly=True,
        currency_field='currency_id',
    )

    sign_date = fields.Datetime(
        string='Ngày & giờ đi ký',
        default=lambda self: fields.Datetime.now() + timedelta(days=2),
        required=True,
        help='Thời điểm NV hẹn KH đi ký HĐ — hệ thống sẽ remind đúng giờ.',
    )
    sign_location = fields.Char(
        string='Địa điểm ký',
        placeholder='Vd: Tại nhà KH / VP VINADUY HCM / Quán cafe...',
    )
    sign_note = fields.Text(
        string='Ghi chú lịch hẹn',
        placeholder='Vd: KH yêu cầu mang theo bản vẽ chi tiết + báo giá v2, hẹn 14h-15h...',
    )

    currency_id = fields.Many2one(
        'res.currency', compute='_compute_vnd_currency',
    )

    def _compute_vnd_currency(self):
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        for rec in self:
            rec.currency_id = vnd

    def action_schedule_sign(self):
        """KH đồng ý → đặt lịch ký + chuyển stage sang Khách chốt ngay."""
        self.ensure_one()
        won = self.env.ref('vd_crm_lead.stage_won', raise_if_not_found=False) or \
              self.env['crm.stage'].search([('code', '=', 'won')], limit=1)
        if not won:
            raise UserError(_('Không tìm thấy stage "Khách chốt".'))

        old_stage = self.lead_id.stage_id.name or ''
        # Ghi lịch hẹn + chuyển stage + set callback đúng giờ ký
        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_planned_sign_date': self.sign_date,
            'vd_planned_sign_location': self.sign_location or '',
            'vd_planned_sign_note': self.sign_note or '',
            'callback_date': self.sign_date,
            'stage_id': won.id,
        })

        loc_html = ('<br/>📍 Địa điểm: <b>%s</b>' % self.sign_location) if self.sign_location else ''
        note_html = ('<br/>📝 Ghi chú: <i>%s</i>' % self.sign_note) if self.sign_note else ''
        self.lead_id.message_post(subtype_xmlid='mail.mt_note', body=_(
            '🎉 <b>KH ĐỒNG Ý KÝ HĐ</b> — đã đặt lịch + chuyển sang <b>%s</b>!<br/>'
            '🗓️ Lịch hẹn ký: <b>%s</b>%s%s'
        ) % (
            won.name,
            self.sign_date.strftime('%H:%M %d/%m/%Y'),
            loc_html, note_html,
        ))

        # Reload form parent — stage Khách chốt + countdown banner hiện ngay không cần F5
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'main',
            'effect': {
                'fadeout': 'slow',
                'message': '🎉 KH đồng ý — đã đặt lịch ký HĐ!',
                'type': 'rainbow_man',
            },
        }
