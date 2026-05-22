# -*- coding: utf-8 -*-
"""Cập nhật tên + sequence cho 3 vấn đề Tài chính (nhóm tài chính top dropdown).

Vì vd_nego_problem_data.xml dùng noupdate="1", record đã có trong DB không
được override khi -u module. Migration này force update theo XML mới.
"""


def migrate(cr, version):
    # very_low_budget: "Thiếu kinh phí nhiều" → "Cân đối tài chính"
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = 'Cân đối tài chính', icon = '💰', sequence = 5
         WHERE code = 'very_low_budget'
    """)
    # extra_area: "Phát sinh diện tích" → "Phát sinh"
    cr.execute("""
        UPDATE vd_nego_problem
           SET name = 'Phát sinh', sequence = 7
         WHERE code = 'extra_area'
    """)
    # promotion: giữ tên, đẩy sequence lên top group tài chính
    cr.execute("""
        UPDATE vd_nego_problem
           SET sequence = 6
         WHERE code = 'promotion'
    """)
