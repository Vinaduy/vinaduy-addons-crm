# -*- coding: utf-8 -*-
"""Backfill vd_work_start_date cho res.users existing = ngày tạo user."""


def migrate(cr, version):
    cr.execute("""
        UPDATE res_users u
           SET vd_work_start_date = u.create_date::date
         WHERE u.vd_work_start_date IS NULL
           AND u.create_date IS NOT NULL
    """)
