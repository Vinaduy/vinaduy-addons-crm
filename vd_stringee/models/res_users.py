from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    stringee_user_id = fields.Char(
        string='Stringee User ID',
        help='User ID đã tạo trên Stringee Dashboard. Để trống nếu NV không gọi qua Web SDK.',
        copy=False,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['stringee_user_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['stringee_user_id']
