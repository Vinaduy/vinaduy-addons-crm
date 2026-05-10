"""Wizard ký hợp đồng + nhập tiền cọc.
Yêu cầu user: cọc TỐI THIỂU 50.000.000đ. Đây là kịch bản tư vấn (hard
validation: nếu < 50tr → block save + cho NV gợi ý KH bổ sung)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VdContractSignWizard(models.TransientModel):
    _name = 'vd.contract.sign.wizard'
    _description = 'Wizard ký hợp đồng + nhận cọc'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)
    quote_price_display = fields.Monetary(
        related='lead_id.vd_quote_price', readonly=True,
        currency_field='currency_id',
    )

    sign_date = fields.Date(string='Ngày ký HĐ', default=fields.Date.context_today, required=True)
    deposit_amount = fields.Monetary(
        string='Tiền cọc KH chuyển (đ)',
        currency_field='currency_id', required=True,
        help='TỐI THIỂU 50.000.000đ. Hệ thống chặn nếu nhập thấp hơn.',
    )
    deposit_method = fields.Selection([
        ('cash', '💵 Tiền mặt'),
        ('bank', '🏦 Chuyển khoản'),
        ('card', '💳 Thẻ'),
    ], string='Phương thức', default='bank', required=True)
    deposit_note = fields.Text(string='Ghi chú nhận cọc')

    currency_id = fields.Many2one(
        'res.currency', compute='_compute_vnd_currency',
    )

    def _compute_vnd_currency(self):
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        for rec in self:
            rec.currency_id = vnd

    @api.constrains('deposit_amount')
    def _check_min_deposit(self):
        for rec in self:
            if rec.deposit_amount < self.env['crm.lead'].VD_MIN_DEPOSIT:
                raise ValidationError(_(
                    "Tiền cọc TỐI THIỂU 50.000.000đ. KH cọc %.0fđ là chưa đủ.\n\n"
                    "💡 Kịch bản tư vấn:\n"
                    '"Anh/chị ơi, để bên em chính thức giữ chỗ + đặt vật liệu + '
                    'lên kế hoạch tổ thợ thì cần cọc tối thiểu 50tr theo quy định '
                    'công ty. Anh/chị có thể chuyển thêm phần còn thiếu trong hôm '
                    'nay được không ạ?"'
                ) % rec.deposit_amount)

    def action_confirm_sign(self):
        """Ghi nhận ký HĐ + cọc → set stage = won."""
        self.ensure_one()
        won = self.env.ref('vd_crm_lead.stage_won', raise_if_not_found=False) or \
              self.env['crm.stage'].search([('code', '=', 'won')], limit=1)
        if not won:
            raise UserError(_('Không tìm thấy stage "Khách chốt".'))

        old_stage = self.lead_id.stage_id.name or ''
        # Disable tracking để không trigger auto-email lúc đổi stage
        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_contract_signed': True,
            'vd_contract_sign_date': self.sign_date,
            'vd_contract_deposit': self.deposit_amount,
            'stage_id': won.id,
        })
        method_label = dict(self._fields['deposit_method'].selection).get(
            self.deposit_method, ''
        )
        self.lead_id.message_post(subtype_xmlid='mail.mt_note', body=_(
            "🏆 <b>KÝ HỢP ĐỒNG THÀNH CÔNG</b> ngày <b>%s</b>!<br/>"
            "Cọc nhận: <b>%s đ</b> (%s)<br/>"
            "Chuyển từ <i>%s</i> → <b>%s</b>.<br/>"
            "%s"
        ) % (
            self.sign_date.strftime('%d/%m/%Y'),
            f'{self.deposit_amount:,.0f}'.replace(',', '.'),
            method_label,
            old_stage, won.name,
            f'<i>Ghi chú: {self.deposit_note}</i>' if self.deposit_note else '',
        ))
        return {'type': 'ir.actions.act_window_close'}
