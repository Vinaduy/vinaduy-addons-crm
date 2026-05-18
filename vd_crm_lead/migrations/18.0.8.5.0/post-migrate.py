# -*- coding: utf-8 -*-
"""Post-migrate 18.0.8.5.0
- Đồng bộ matrix phân quyền display: Phó GĐ KHÔNG còn xoá KH (chỉ Admin).
  role_config_data.xml dùng noupdate="1" nên cần force-write thủ công.
"""


def migrate(cr, version):
    # Tắt can_unlink trên row Phó GĐ nếu vẫn đang bật từ phiên bản cũ
    cr.execute("""
        UPDATE vd_crm_role_config
           SET can_unlink = FALSE,
               note = %s
         WHERE role_code = 'deputy'
           AND can_unlink = TRUE
    """, ('Sửa + chuyển KH liên team + xem toàn bộ + xem báo cáo. KHÔNG được xoá KH (chỉ Admin).',))
