from odoo import api, fields, models


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
        string='Số fallback (global)',
        config_parameter='vd_stringee.from_number',
        help='Số PSTN dự phòng khi NV chưa được assign số tổng đài riêng.\n'
             'Khuyến nghị: quản lý pool số ở menu "Stringee → Số tổng đài" + '
             'assign cho từng NV thay vì dùng số global này.',
    )
    stringee_record_calls = fields.Boolean(
        string='Ghi âm cuộc gọi',
        config_parameter='vd_stringee.record_calls',
        default=True,
    )
    stringee_webhook_base_url = fields.Char(
        string='Webhook Base URL',
        compute='_compute_webhook_urls',
        help='Base URL của Odoo server — Stringee gọi 3 endpoint dưới đây để route call + nhận event.',
    )
    stringee_answer_url = fields.Char(
        string='Answer URL', compute='_compute_webhook_urls',
    )
    stringee_event_url = fields.Char(
        string='Event URL', compute='_compute_webhook_urls',
    )
    stringee_recording_url = fields.Char(
        string='Recording Event URL', compute='_compute_webhook_urls',
    )
    stringee_hotline_count = fields.Integer(
        string='Số hotline đã khai báo',
        compute='_compute_stringee_hotline_count',
    )

    def _compute_webhook_urls(self):
        base = (self.env['ir.config_parameter'].sudo()
                .get_param('web.base.url', '') or '').rstrip('/')
        for rec in self:
            rec.stringee_webhook_base_url = base
            rec.stringee_answer_url = f'{base}/stringee/answer' if base else ''
            rec.stringee_event_url = f'{base}/stringee/event' if base else ''
            rec.stringee_recording_url = f'{base}/stringee/recording_event' if base else ''

    def _compute_stringee_hotline_count(self):
        Hotline = self.env['vd.stringee.hotline']
        for rec in self:
            rec.stringee_hotline_count = Hotline.search_count([('active', '=', True)])

    def action_open_stringee_hotline_pool(self):
        """Mở menu quản lý pool số tổng đài từ trang Settings."""
        return self.env.ref('vd_stringee.action_vd_stringee_hotline').sudo().read()[0]
