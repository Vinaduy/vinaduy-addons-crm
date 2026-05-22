# -*- coding: utf-8 -*-
"""Tái cấu trúc nhóm Tài chính picker:
- Nhóm financial mới: budget_balance + extra_material + promotion (đưa lên đầu)
- Rollback rename very_low_budget về "Thiếu kinh phí nhiều" (sequence cũ 30)
- Rollback rename extra_area về "Phát sinh diện tích" (sequence cũ 130, vẫn còn trong DB
  nhưng không hiện trong picker nữa)
"""


def migrate(cr, version):
    # Rollback rename — restore original names
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = 'Thiếu kinh phí nhiều', icon = '🪙', sequence = 30
         WHERE code = 'very_low_budget'
    """)
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = 'Phát sinh diện tích', sequence = 130
         WHERE code = 'extra_area'
    """)
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
