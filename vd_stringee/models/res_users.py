from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    stringee_user_id = fields.Char(
        string='Stringee User ID',
        help='User ID đã tạo trên Stringee Dashboard. Để trống nếu NV không gọi qua Web SDK.',
        copy=False,
    )
    stringee_from_number_id = fields.Many2one(
        'vd.stringee.hotline',
        string='Số tổng đài Stringee',
        domain=[('active', '=', True)],
        help='Số hotline NV dùng để gọi ra. Để trống → fallback số global '
             'config (Cấu hình → Stringee → From Number).',
    )
    stringee_from_number_display = fields.Char(
        string='Hotline number',
        related='stringee_from_number_id.number',
        readonly=True,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'stringee_user_id',
            'stringee_from_number_id',
            'stringee_from_number_display',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['stringee_user_id']
