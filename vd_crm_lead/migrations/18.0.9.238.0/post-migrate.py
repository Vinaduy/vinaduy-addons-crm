# -*- coding: utf-8 -*-
"""Siết quyền xem KH (user spec 2026-06-14).

Trước đây vai trò Nhân viên implied 'group_sale_salesman_all_leads' → NV + Trưởng
nhóm thấy TẤT CẢ lead toàn công ty. Đã bỏ implied đó (security_groups.xml). Nhưng
membership cũ đã materialize trên user → phải GỠ thủ công ở đây cho mọi user KHÔNG
phải quản lý (không có group_sale_manager). Quản lý (Giám đốc/Admin) giữ all_leads
qua group_sale_manager → vẫn thấy tất cả.

Sau migration:
- Nhân viên/CTV: chỉ thấy KH của mình (+ pool chưa giao).
- Trưởng nhóm: KH của mình + KH NV cùng phòng ban (vd_team).
- Giám đốc/Admin: tất cả.

Đồng thời backfill vd_team cho NV còn trống (đề phòng 237 bỏ sót) để rule theo
phòng ban hoạt động đúng.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    all_leads = env.ref('sales_team.group_sale_salesman_all_leads',
                        raise_if_not_found=False)
    manager = env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
    if all_leads:
        # Gỡ all_leads khỏi mọi user KHÔNG có group_sale_manager (NV + Trưởng nhóm).
        victims = all_leads.users.filtered(
            lambda u: not (manager and manager in u.groups_id))
        if victims:
            all_leads.write({'users': [(3, u.id) for u in victims]})

    # Backfill thẻ phòng ban còn trống từ tiền tố tên (an toàn, không đè thẻ đã có).
    users = env['res.users'].with_context(active_test=False).search(
        [('share', '=', False)])
    users._vd_autoset_team()
