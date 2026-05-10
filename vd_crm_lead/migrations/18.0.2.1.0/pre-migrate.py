"""Pre-migration: drop columns thay đổi schema để Odoo tự tạo lại đúng kiểu.

- vd_intake_district: Char (text) → Many2one('vd.district') (int FK)
  → DROP COLUMN để tránh lỗi convert text→int.
- vd_intake_address: bị xoá hoàn toàn → DROP để dọn schema.
"""


def migrate(cr, version):
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_district CASCADE")
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_address CASCADE")
