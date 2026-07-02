# -*- coding: utf-8 -*-
"""User spec 2026-07-02: gộp "Ô tô vào" từ 3 lựa chọn (xe tải lớn / xe tải nhỏ /
xe 3 bánh) còn 2 (Ô tô vào được / KHÔNG vào được). Đơn giá vốn chỉ có 2 bậc nên
1-1 với Boolean vd_intake_car_access.

Migration: đưa cột vd_intake_car_access_select về đúng 2 giá trị mới, lấy theo
Boolean vd_intake_car_access (nguồn chân lý). Tránh giá trị cũ (xe_*) thành
invalid selection.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # car_access=False → 'khong'; còn lại (True/NULL, default True) → 'duoc'.
    cr.execute("""
        UPDATE crm_lead
           SET vd_intake_car_access_select =
               CASE WHEN vd_intake_car_access IS FALSE THEN 'khong' ELSE 'duoc' END
         WHERE vd_intake_car_access_select IS NULL
            OR vd_intake_car_access_select NOT IN ('duoc', 'khong')
    """)
    _logger.info('vd 289: da chuyen %s lead ve 2 lua chon o to vao', cr.rowcount)
