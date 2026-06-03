from odoo import _, api, fields, models

from .vd_stringee_hotline import vd_carrier_from_number

# Nhà mạng hỗ trợ gọi cùng mạng + label tiếng Việt.
_CARRIER_LABELS = {
    'viettel': 'Viettel', 'vina': 'Vinaphone', 'mobi': 'MobiFone',
    'vietnamobile': 'Vietnamobile', 'gmobile': 'Gmobile', 'itelecom': 'iTel',
}
# Mạng được gọi NỘI MẠNG (có đầu số tổng đài tương ứng trên Stringee).
# Bật thêm Vietnamobile + iTel (2026-06-03): có hotline 84922039966 (VNM) +
# 84872446886 (iTel) → cho gọi KH cùng 2 mạng này thay vì chặn.
_SAME_CARRIER_SUPPORTED = ('viettel', 'vina', 'mobi', 'vietnamobile', 'itelecom')


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

    # Cờ loại NV khỏi "chia đều số" (admin / quản lý / NV không trực tiếp gọi).
    vd_no_number_share = fields.Boolean(
        string='Không tham gia chia số',
        default=False,
        help='Tick để NV này KHÔNG được nhận số khi bấm "Chia đều" trên bảng kho số.',
    )

    # Số đang gán theo từng mạng — để dựng bảng MA TRẬN "NV × nhà mạng":
    # mỗi dòng 1 NV, mỗi cột 1 mạng, ô = số được gán. Tra 1 NV thấy ngay đủ số.
    stringee_num_viettel = fields.Char(string='Viettel', compute='_compute_stringee_nums')
    stringee_num_mobi = fields.Char(string='MobiFone', compute='_compute_stringee_nums')
    stringee_num_vina = fields.Char(string='Vinaphone', compute='_compute_stringee_nums')
    stringee_num_vietnamobile = fields.Char(string='Vietnamobile', compute='_compute_stringee_nums')
    stringee_num_itelecom = fields.Char(string='iTel', compute='_compute_stringee_nums')
    stringee_missing_main = fields.Char(
        string='Thiếu mạng', compute='_compute_stringee_nums',
        help='Các mạng chính (Viettel/Vinaphone/MobiFone) NV chưa được gán số.',
    )

    @api.depends('stringee_hotline_ids', 'stringee_hotline_ids.number',
                 'stringee_hotline_ids.carrier', 'stringee_hotline_ids.active')
    def _compute_stringee_nums(self):
        for user in self:
            buckets = {'viettel': [], 'mobi': [], 'vina': [],
                       'vietnamobile': [], 'itelecom': []}
            for h in user.stringee_hotline_ids:
                if h.active and h.carrier in buckets:
                    buckets[h.carrier].append(h.number)
            user.stringee_num_viettel = ', '.join(buckets['viettel'])
            user.stringee_num_mobi = ', '.join(buckets['mobi'])
            user.stringee_num_vina = ', '.join(buckets['vina'])
            user.stringee_num_vietnamobile = ', '.join(buckets['vietnamobile'])
            user.stringee_num_itelecom = ', '.join(buckets['itelecom'])
            missing = [lbl for code, lbl in (
                ('viettel', 'Viettel'), ('vina', 'Vinaphone'), ('mobi', 'MobiFone'))
                if not buckets[code]]
            user.stringee_missing_main = ', '.join(missing)

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
                'KHÔNG GỌI ĐƯỢC số "%s": số khách thuộc nhà mạng khác '
                '(Gmobile...) hoặc đầu số lạ. Bạn KHÔNG được gọi ngoại mạng — '
                'chỉ gọi nội mạng Viettel / Vinaphone / MobiFone / Vietnamobile '
                '/ iTel.'
            ) % (to_number or '')}
        label = _CARRIER_LABELS.get(carrier, carrier)
        hotline = self.stringee_hotline_ids.filtered(
            lambda h: h.active and h.carrier == carrier
        )[:1]
        if not hotline:
            return {'error': (
                'BẠN KHÔNG CÓ SỐ %s ĐỂ GỌI: khách này dùng mạng %s, mà bạn chưa '
                'được gán số tổng đài %s nào. Bạn KHÔNG được gọi ngoại mạng. '
                '→ Báo admin gán cho bạn 1 số %s.'
            ) % (label, label, label, label)}
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
