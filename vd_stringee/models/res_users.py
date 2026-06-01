from odoo import _, fields, models

from .vd_stringee_hotline import vd_carrier_from_number

# Nhà mạng hỗ trợ gọi cùng mạng + label tiếng Việt.
_CARRIER_LABELS = {
    'viettel': 'Viettel', 'vina': 'Vinaphone', 'mobi': 'MobiFone',
    'vietnamobile': 'Vietnamobile', 'gmobile': 'Gmobile', 'itelecom': 'iTel',
}
_SAME_CARRIER_SUPPORTED = ('viettel', 'vina', 'mobi')


class ResUsers(models.Model):
    _inherit = 'res.users'

    stringee_user_id = fields.Char(
        string='Stringee User ID',
        help='User ID đã tạo trên Stringee Dashboard. Để trống nếu NV không gọi qua Web SDK.',
        copy=False,
    )
    stringee_from_number_id = fields.Many2one(
        'vd.stringee.hotline',
        string='Số tổng đài Stringee (số đơn cũ)',
        domain=[('active', '=', True)],
        help='LEGACY — số đơn 1 NV/1 số. Giờ dùng "Số theo mạng" bên dưới.',
    )
    stringee_from_number_display = fields.Char(
        string='Hotline number',
        related='stringee_from_number_id.number',
        readonly=True,
    )
    # Gán theo mạng (mới): mỗi NV nên có đủ 1 Viettel + 1 Vina + 1 Mobi.
    stringee_hotline_ids = fields.Many2many(
        'vd.stringee.hotline', 'vd_stringee_hotline_user_rel', 'user_id', 'hotline_id',
        string='Số tổng đài theo mạng',
        domain=[('active', '=', True)],
        help='Mỗi NV cần đủ 1 Viettel + 1 Vinaphone + 1 MobiFone. Khi gọi, hệ '
             'thống TỰ lấy số CÙNG MẠNG với KH; không có số cùng mạng → báo lỗi.',
    )

    def _vd_resolve_outbound(self, to_number):
        """Chọn số gọi ra CÙNG MẠNG với KH (to_number).
        - Ưu tiên số NV đã được gán cho mạng đó (stringee_hotline_ids).
        - Không có số cùng mạng → trả {'error': ...} (KHÔNG fallback mạng khác).
        Trả: {'from_number': '84...', 'carrier': 'viettel'} hoặc {'error': '...'}.
        """
        self.ensure_one()
        carrier = vd_carrier_from_number(to_number)
        if carrier not in _SAME_CARRIER_SUPPORTED:
            return {'error': (
                'Số khách "%s" không thuộc Viettel/Vinaphone/MobiFone (đầu số lạ) '
                '— chưa hỗ trợ gọi cùng mạng.'
            ) % (to_number or '')}
        label = _CARRIER_LABELS.get(carrier, carrier)
        hotline = self.stringee_hotline_ids.filtered(
            lambda h: h.active and h.carrier == carrier
        )[:1]
        if not hotline:
            return {'error': (
                'Bạn CHƯA được gán số %s — không gọi được CÙNG MẠNG cho khách này. '
                'Báo admin gán số %s cho bạn.'
            ) % (label, label)}
        return {'from_number': hotline.number, 'carrier': carrier}

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'stringee_user_id',
            'stringee_from_number_id',
            'stringee_from_number_display',
            'stringee_hotline_ids',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['stringee_user_id']
