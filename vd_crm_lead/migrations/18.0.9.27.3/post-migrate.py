# -*- coding: utf-8 -*-
"""Tái cấu trúc nhóm Tài chính picker:
- Nhóm financial mới: budget_balance + extra_material + promotion (đưa lên đầu)
- Rollback rename very_low_budget về "Thiếu kinh phí nhiều" (sequence cũ 30)
- Rollback rename extra_area về "Phát sinh diện tích" (sequence cũ 130, vẫn còn trong DB
  nhưng không hiện trong picker nữa)

Note: name là Char(translate=True) → DB type JSONB, phải dùng jsonb syntax.
"""


def migrate(cr, version):
    # Rollback rename — restore original names
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = jsonb_build_object('en_US', %s),
               icon = %s,
               sequence = 30
         WHERE code = 'very_low_budget'
    """, ('Thiếu kinh phí nhiều', '🪙'))
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = jsonb_build_object('en_US', %s),
               sequence = 130
         WHERE code = 'extra_area'
    """, ('Phát sinh diện tích',))
    # Group financial mới — 3 items lên đầu
    cr.execute("""
        UPDATE vd_nego_problem
           SET sequence = 5
         WHERE code = 'budget_balance'
    """)
    cr.execute("""
        UPDATE vd_nego_problem
           SET sequence = 6
         WHERE code = 'extra_material'
    """)
    cr.execute("""
        UPDATE vd_nego_problem
           SET sequence = 7
         WHERE code = 'promotion'
    """)
