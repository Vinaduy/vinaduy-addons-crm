# -*- coding: utf-8 -*-
"""User spec 2026-06-12:
1. Thêm loại mái "Mái tôn" (13%) — đảm bảo field pricing mai_ton có giá trị
   trên mọi vùng đã có (phòng khi _init_column không set default).
2. Hệ số mái thái/nhật mặc định đổi sang bản 55%/48% (xử lý ở code resolve,
   không cần migrate dữ liệu vì UI chỉ lưu house_type).
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE vd_pricing_region
           SET mai_ton = 13.0
         WHERE mai_ton IS NULL OR mai_ton = 0
    """)
