# -*- coding: utf-8 -*-
"""User spec 2026-06-12: KM chia 3 phương án thay cho 2 loại cũ.
Map giá trị km_type cũ → mới (giữ nguyên dữ liệu KM đã có):
- 'discount' (giảm giá số tiền trực tiếp) → 'discount_money' (Khuyến mãi tiền)
- 'promo'    (vật tư tặng + quy đổi)      → 'promo_material' (KM thiết bị/vật tư)
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE vd_lead_problem
           SET km_type = 'discount_money'
         WHERE km_type = 'discount'
    """)
    cr.execute("""
        UPDATE vd_lead_problem
           SET km_type = 'promo_material'
         WHERE km_type = 'promo'
    """)
