"""Force recompute vd_quote_price = vd_intake_estimate cho mọi lead có sẵn.
Lý do: trước đây vd_quote_price chỉ sync khi = 0; giờ logic đổi thành luôn sync.
Lead nào có giá báo cũ (đặt manual) cần reset để compute fire."""


def migrate(cr, version):
    cr.execute("""
        UPDATE crm_lead
        SET vd_quote_price = NULL
        WHERE vd_quote_locked = false OR vd_quote_locked IS NULL
    """)
