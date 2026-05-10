"""Pre-migrate 18.0.2.2.0
- vd_intake_timeline: Selection (varchar enum) → Char (free text).
  Drop column để Odoo tạo lại đúng kiểu (data cũ kiểu 'chuan_bi', '1-3_thang' không
  còn hợp lệ → drop là đúng đắn nhất).
"""


def migrate(cr, version):
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_timeline CASCADE")
