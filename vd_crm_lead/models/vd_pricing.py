from odoo import fields, models


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
