from odoo import fields, models


class ResCountryState(models.Model):
    """Mở rộng res.country.state để đánh dấu 34 tỉnh mới sau cải cách
    01/07/2025. Picker chỉ hiển thị các state có vd_is_active_2025=True
    → NV không chọn nhầm tỉnh cũ đã sáp nhập."""
    _inherit = 'res.country.state'

    vd_is_active_2025 = fields.Boolean(
        string='Tỉnh sau cải cách 2025',
        default=False, index=True,
        help='True = 1 trong 34 tỉnh/TP sau cải cách 01/07/2025. '
             'Set bởi _populate_vn_districts() trong post_init.',
    )
