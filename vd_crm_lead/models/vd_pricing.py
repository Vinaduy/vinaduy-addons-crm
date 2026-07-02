from odoo import api, fields, models


def _pct(v):
    """30.0 -> '30', 12.5 -> '12.5'."""
    return ('%g' % (v or 0))


def _money(v):
    """6400000 -> '6.400.000'."""
    return '{:,.0f}'.format(v or 0).replace(',', '.')


# Ghi chú theo vùng (text mô tả phụ phí địa bàn - không phải con số đơn giá).
_REGION_NOTE = {
    'bac': 'Toàn tỉnh: Lai Châu, Sơn La, Điện Biên, Cao Bằng, Bắc Kạn tăng '
           '300k/m². Các huyện của tỉnh Hà Giang, Lạng Sơn tăng 300k.',
    'trung': 'Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả '
             'bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng '
             '800k. Gửi cấp trên duyệt.',
    'nam': 'Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả '
           'bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng '
           '800k. Gửi cấp trên duyệt.',
}
# Nhãn dòng móng đầu tiên theo vùng (Nam quen gọi "Móng cốc").
_MONG_FIRST_LABEL = {'bac': 'Móng đơn', 'trung': 'Móng đơn', 'nam': 'Móng cốc'}
_REGION_ORDER = [('bac', 'BẮC'), ('trung', 'TRUNG'), ('nam', 'NAM')]


class VdPricingRegion(models.Model):
    """Đơn giá xây dựng theo VÙNG (Bắc / Trung / Nam). Admin chỉnh được.

    Mỗi field = 1 cell trong bảng đơn giá. Đơn vị tiền = VND.
    Đơn vị % = phần trăm (vd 30 = 30%).
    """
    _name = 'vd.pricing.region'
    _description = 'Đơn giá xây dựng theo vùng'
    _order = 'sequence, code'

    name = fields.Char(string='Tên vùng', required=True)
    code = fields.Char(string='Mã vùng', required=True, size=10,
                        help="bac / trung / nam — dùng để map từ tỉnh.")
    sequence = fields.Integer(default=10)
    note = fields.Text(string='Ghi chú')

    # ============ MÓNG (% nhân với đơn giá sàn × diện tích móng) ============
    mong_don_lon = fields.Float(string='Móng đơn (≥70m², %)', default=30.0)
    mong_don_nho = fields.Float(string='Móng đơn (≤69m², %)', default=35.0)
    mong_bang_lon = fields.Float(string='Móng băng (≥70m², %)', default=40.0)
    mong_bang_nho = fields.Float(string='Móng băng (≤69m², %)', default=45.0)
    mong_coc_lon = fields.Float(string='Móng cọc (≥70m², %)', default=40.0)
    mong_coc_nho = fields.Float(string='Móng cọc (≤69m², %)', default=45.0)

    # ============ ĐƠN GIÁ SÀN (đ/m²) — phụ thuộc DT 1 sàn & ô tô vào được ============
    # Bảng cập nhật 2026-05-20: cả 3 vùng dùng chung 1 bảng sàn.
    san_75_oto = fields.Float(string='Sàn ≥75m² · ô tô vào (đ/m²)', default=6_400_000)
    san_75_kxe = fields.Float(string='Sàn ≥75m² · ô tô KO vào (đ/m²)', default=6_700_000)
    san_65_oto = fields.Float(string='Sàn 65–74m² · ô tô vào (đ/m²)', default=6_600_000)
    san_65_kxe = fields.Float(string='Sàn 65–74m² · ô tô KO vào (đ/m²)', default=6_900_000)
    san_50_oto = fields.Float(string='Sàn 50–64m² · ô tô vào (đ/m²)', default=6_800_000)
    san_50_kxe = fields.Float(string='Sàn 50–64m² · ô tô KO vào (đ/m²)', default=7_000_000)
    san_40_oto = fields.Float(string='Sàn 40–49m² · ô tô vào (đ/m²)', default=7_000_000)
    san_40_kxe = fields.Float(string='Sàn 40–49m² · ô tô KO vào (đ/m²)', default=7_500_000)
    san_lt40_oto = fields.Float(string='Sàn ≤39m² · ô tô vào (đ/m²)', default=7_500_000)
    san_lt40_kxe = fields.Float(string='Sàn ≤39m² · ô tô KO vào (đ/m²)', default=8_000_000)

    # ============ XÂY THÔ TRỌN GÓI (đ/m²) ============
    tho_lon = fields.Float(string='Trọn gói (≥70m², đ/m²)', default=5_000_000)
    tho_nho = fields.Float(string='Trọn gói (≤69m², đ/m²)', default=5_200_000)

    # ============ MÁI (% nhân với đơn giá sàn × diện tích mái) ============
    mai_bang = fields.Float(string='Mái bằng (%)', default=20.0)
    mai_nhat_kdt = fields.Float(string='Mái nhật KHÔNG đổ trần (%)', default=42.0)
    mai_nhat_cdt = fields.Float(string='Mái nhật CÓ đổ trần (%)', default=48.0)
    mai_thai_kdt = fields.Float(string='Mái thái KHÔNG đổ trần (%)', default=45.0)
    mai_thai_cdt = fields.Float(string='Mái thái CÓ đổ trần (%)', default=55.0)
    thong_tang = fields.Float(string='Thông tầng (%)', default=40.0)
    mai_trang_tri = fields.Float(string='Mái trang trí (%)', default=50.0,
                                  help='Khoảng 40–60%, lấy giữa.')
    mai_trang_tri_dt = fields.Float(string='Mái trang trí ĐỔ TRẦN (%)', default=100.0)
    mai_ton = fields.Float(string='Mái tôn (%)', default=13.0)
    mai_ton_1m = fields.Float(string='Mái tôn 1 mặt (%)', default=13.0)
    mai_ton_2m = fields.Float(string='Mái tôn 2 mặt (%)', default=16.0)
    mai_ton_3m = fields.Float(string='Mái tôn 3 mặt (%)', default=20.0)

    # ============ HỆ SỐ MÓNG CỘNG THÊM (% trên TOTAL) ============
    # Cập nhật 2026-05-20: rename + đổi mapping cho đúng spec.
    # - Móng ĐƠN: +10% (trước đây bị gán nhầm cho móng cọc)
    # - Móng BĂNG + Móng CỌC: +15% (cả 2 cùng phụ phí)
    pct_mong_don = fields.Float(string='Phụ phí móng đơn (%)', default=10.0)
    pct_mong_bang_coc = fields.Float(string='Phụ phí móng băng + cọc (%)', default=15.0)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã vùng phải duy nhất.'),
    ]

    # ==================================================================
    #  NGUỒN CHUNG cho BẢNG BÁO GIÁ (form khách) + khóa học "Bảng giá".
    #  Đổi cấu hình đơn giá ở đây -> cả 2 nơi đồng bộ theo.
    # ==================================================================
    @api.model
    def vd_get_price_table(self):
        """Trả về toàn bộ bảng đơn giá (3 miền) suy từ field model.
        Móng đổi theo miền; Sàn/Mái dùng chung (lấy từ vùng 'bac')."""
        recs = {r.code: r for r in self.sudo().search([])}
        base = recs.get('bac') or (list(recs.values())[0] if recs else None)
        if not base:
            return self._vd_price_table_fallback()

        def mong_rows(r):
            first = _MONG_FIRST_LABEL.get(r.code, 'Móng đơn')
            return [
                {'name': first,
                 'over': 'DT × %s%% × Đơn giá' % _pct(r.mong_don_lon),
                 'under': 'DT × %s%% × Đơn giá' % _pct(r.mong_don_nho)},
                {'name': 'Móng băng',
                 'over': 'DT × %s%% × Đơn giá' % _pct(r.mong_bang_lon),
                 'under': 'DT × %s%% × Đơn giá' % _pct(r.mong_bang_nho)},
                {'name': 'Móng cọc',
                 'over': 'DT × %s%% × Đơn giá' % _pct(r.mong_coc_lon),
                 'under': 'DT × %s%% × Đơn giá' % _pct(r.mong_coc_nho)},
            ]

        regions = []
        for code, label in _REGION_ORDER:
            r = recs.get(code)
            if not r:
                continue
            regions.append({'key': code, 'label': label,
                            'rows': mong_rows(r),
                            'note': r.note or _REGION_NOTE.get(code, '')})

        san_rows = [
            {'name': 'Ô tô vào được', 'vals': [
                _money(base.san_75_oto), _money(base.san_65_oto),
                _money(base.san_50_oto), _money(base.san_40_oto),
                _money(base.san_lt40_oto)]},
            {'name': 'Ô tô không vào được', 'vals': [
                _money(base.san_75_kxe), _money(base.san_65_kxe),
                _money(base.san_50_kxe), _money(base.san_40_kxe),
                _money(base.san_lt40_kxe)]},
        ]
        mai = [
            {'name': 'Mái bằng', 'val': 'DT × %s%% × Đơn giá' % _pct(base.mai_bang)},
            {'name': 'Mái Nhật',
             'left': 'Không đổ trần: DT × %s%%' % _pct(base.mai_nhat_kdt),
             'right': 'Có đổ trần: DT × %s%%' % _pct(base.mai_nhat_cdt)},
            {'name': 'Mái Thái',
             'left': 'Không đổ trần: DT × %s%%' % _pct(base.mai_thai_kdt),
             'right': 'Có đổ trần: DT × %s%%' % _pct(base.mai_thai_cdt)},
            {'name': 'Thông tầng', 'val': 'DT × %s%% × Đơn giá' % _pct(base.thong_tang)},
            {'name': 'Mái trang trí', 'val': 'DT × 40%% → 60%% × Đơn giá'},
            {'name': 'Mái trang trí đổ trần',
             'val': 'DT × %s%% × Đơn giá' % _pct(base.mai_trang_tri_dt)},
            {'name': 'Mái tôn',
             'val': '1 mặt: DT × %s%%   ·   2 mặt: DT × %s%%   ·   3 mặt: DT × %s%%'
                    % (_pct(base.mai_ton_1m), _pct(base.mai_ton_2m), _pct(base.mai_ton_3m))},
        ]
        return {
            'regions': regions,
            'san_cols': ['≥ 75m²', '65-75m²', '50-65m²', '40-50m²', '< 40m²'],
            'san_rows': san_rows,
            'san_tho': {'over': _money(base.tho_lon) + ' đ/m²',
                        'under': _money(base.tho_nho) + ' đ/m²'},
            'mai': mai,
            'luu_y': 'Hệ số móng đơn cộng thêm %s%%; móng băng, móng cọc cộng thêm %s%%.'
                     % (_pct(base.pct_mong_don), _pct(base.pct_mong_bang_coc)),
        }

    @api.model
    def _vd_price_table_fallback(self):
        """Bảng mặc định khi chưa có record vd.pricing.region (hiếm)."""
        return {
            'regions': [
                {'key': 'bac', 'label': 'BẮC', 'note': _REGION_NOTE['bac'], 'rows': [
                    {'name': 'Móng đơn', 'over': 'DT × 30% × Đơn giá', 'under': 'DT × 35% × Đơn giá'},
                    {'name': 'Móng băng', 'over': 'DT × 40% × Đơn giá', 'under': 'DT × 45% × Đơn giá'},
                    {'name': 'Móng cọc', 'over': 'DT × 40% × Đơn giá', 'under': 'DT × 45% × Đơn giá'}]},
                {'key': 'trung', 'label': 'TRUNG', 'note': _REGION_NOTE['trung'], 'rows': [
                    {'name': 'Móng đơn', 'over': 'DT × 35% × Đơn giá', 'under': 'DT × 40% × Đơn giá'},
                    {'name': 'Móng băng', 'over': 'DT × 45% × Đơn giá', 'under': 'DT × 50% × Đơn giá'},
                    {'name': 'Móng cọc', 'over': 'DT × 45% × Đơn giá', 'under': 'DT × 50% × Đơn giá'}]},
                {'key': 'nam', 'label': 'NAM', 'note': _REGION_NOTE['nam'], 'rows': [
                    {'name': 'Móng cốc', 'over': 'DT × 40% × Đơn giá', 'under': 'DT × 45% × Đơn giá'},
                    {'name': 'Móng băng', 'over': 'DT × 50% × Đơn giá', 'under': 'DT × 55% × Đơn giá'},
                    {'name': 'Móng cọc', 'over': 'DT × 50% × Đơn giá', 'under': 'DT × 55% × Đơn giá'}]},
            ],
            'san_cols': ['≥ 75m²', '65-75m²', '50-65m²', '40-50m²', '< 40m²'],
            'san_rows': [
                {'name': 'Ô tô vào được', 'vals': ['6.400.000', '6.600.000', '6.800.000', '7.000.000', '7.500.000']},
                {'name': 'Ô tô không vào được', 'vals': ['6.700.000', '6.900.000', '7.000.000', '7.500.000', '8.000.000']},
            ],
            'san_tho': {'over': '5.000.000 đ/m²', 'under': '5.200.000 đ/m²'},
            'mai': [
                {'name': 'Mái bằng', 'val': 'DT × 20% × Đơn giá'},
                {'name': 'Mái Nhật', 'left': 'Không đổ trần: DT × 42%', 'right': 'Có đổ trần: DT × 48%'},
                {'name': 'Mái Thái', 'left': 'Không đổ trần: DT × 45%', 'right': 'Có đổ trần: DT × 55%'},
                {'name': 'Thông tầng', 'val': 'DT × 40% × Đơn giá'},
                {'name': 'Mái trang trí', 'val': 'DT × 40% → 60% × Đơn giá'},
                {'name': 'Mái trang trí đổ trần', 'val': 'DT × 100% × Đơn giá'},
                {'name': 'Mái tôn', 'val': '1 mặt: DT × 13%   ·   2 mặt: DT × 16%   ·   3 mặt: DT × 20%'},
            ],
            'luu_y': 'Hệ số móng đơn cộng thêm 10%; móng băng, móng cọc cộng thêm 15%.',
        }

    def _vd_sync_course_bang_gia(self):
        """Dung lai bang gia trong khoa hoc (neu co module vd_elearning)."""
        if 'slide.channel' not in self.env:
            return
        Channel = self.env['slide.channel']
        if hasattr(Channel, '_vd_reseed_bang_gia_safe'):
            try:
                Channel.sudo()._vd_reseed_bang_gia_safe()
            except Exception:
                pass

    def write(self, vals):
        res = super().write(vals)
        # Đổi cấu hình đơn giá -> dựng lại nội dung bảng giá trong khóa học để đồng bộ.
        self._vd_sync_course_bang_gia()
        # Admin sửa đơn giá -> bật banner thông báo 24h cho phòng KD + mốc đổi giá.
        self._vd_trigger_price_notice(vals)
        return res

    def _vd_trigger_price_notice(self, vals):
        """User spec 2026-07-02: mỗi khi admin sửa ĐƠN GIÁ (san_/mong_/mai_/
        thong_/xay/tron) -> lưu mốc đổi giá + bật thông báo đỏ 24h trên dashboard
        cho toàn phòng KD. Bọc try/except để KHÔNG bao giờ làm hỏng việc lưu giá."""
        price_prefixes = ('san_', 'mong_', 'mai_', 'thong_', 'xay', 'tron')
        if not any(str(k).startswith(price_prefixes) for k in (vals or {})):
            return
        try:
            from datetime import timedelta
            now = fields.Datetime.now()
            ICP = self.env['ir.config_parameter'].sudo()
            ICP.set_param('vd_crm_lead.pricing_changed_at', fields.Datetime.to_string(now))
            ICP.set_param('vd_crm_lead.pricing_notice_until',
                          fields.Datetime.to_string(now + timedelta(hours=24)))
            ICP.set_param('vd_crm_lead.pricing_notice_title',
                          '📢 THÔNG BÁO ĐIỀU CHỈNH ĐƠN GIÁ')
            ICP.set_param('vd_crm_lead.pricing_notice_msg',
                          'Đơn giá xây dựng vừa được điều chỉnh.\n'
                          'Từ bây giờ vui lòng tư vấn và báo giá theo BẢNG GIÁ MỚI.\n'
                          'Khách đã chốt vẫn giữ giá cũ; cần cập nhật thì làm lại báo giá.')
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._vd_sync_course_bang_gia()
        return recs
