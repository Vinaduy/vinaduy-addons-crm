# -*- coding: utf-8 -*-
"""Chuyển các cột diện tích từng tầng (m²) Float -> Integer.

Trước đây dùng Float digits(10,1) nên render '0,0' (locale VN) + parse lỗi khi
gõ -> giá trị bị 'tự xoá'. Đổi sang Integer (số nguyên m²).

Tự làm trước (round + ::integer) để Odoo không rename cột thành *_moved0 rồi
mất dữ liệu cũ.
"""

COLS = [
    'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
    'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
    'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2',
    'vd_intake_floor_lung_m2', 'vd_intake_floor_thongtang_m2',
    'vd_intake_total_m2',
]


def migrate(cr, version):
    for col in COLS:
        cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'crm_lead' AND column_name = %s
        """, (col,))
        row = cr.fetchone()
        if not row:
            continue
        # Chỉ convert nếu đang là double precision / numeric
        if row[0] in ('integer',):
            continue
        cr.execute(
            'ALTER TABLE crm_lead ALTER COLUMN "%s" TYPE integer '
            'USING round(COALESCE("%s", 0))::integer' % (col, col)
        )
