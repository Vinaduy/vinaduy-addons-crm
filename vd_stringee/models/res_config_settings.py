from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stringee_api_key_sid = fields.Char(
        string='API Key SID',
        config_parameter='vd_stringee.api_key_sid',
    )
    stringee_api_key_secret = fields.Char(
        string='API Key Secret',
        config_parameter='vd_stringee.api_key_secret',
    )
    stringee_project_id = fields.Char(
        string='Project ID',
        config_parameter='vd_stringee.project_id',
        help='Tuỳ chọn — chỉ cần nếu account có nhiều project.',
    )
    stringee_from_number = fields.Char(
        string='From Number',
        config_parameter='vd_stringee.from_number',
        help='Số PSTN mua trên Stringee để hiển thị khi gọi ra.',
    )
    stringee_record_calls = fields.Boolean(
        string='Ghi âm cuộc gọi',
        config_parameter='vd_stringee.record_calls',
        default=True,
    )
    stringee_webhook_base_url = fields.Char(
        string='Webhook Base URL',
        compute='_compute_webhook_base_url',
        help='URL cần khai báo trong Stringee Dashboard cho event webhook & answer URL.',
    )

    def _compute_webhook_base_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.stringee_webhook_base_url = base
