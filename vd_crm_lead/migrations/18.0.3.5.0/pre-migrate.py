"""Pre-migrate 18.0.3.5.0
- Bỏ field vd_intake_roof_kind, vd_intake_roof_subtype (gộp lại với
  vd_intake_house_type → vd_intake_roof_type cascade trực tiếp).
- vd_intake_roof_type chuyển từ COMPUTED stored → REGULAR Selection.
  Drop+recreate column để Odoo tạo lại đúng type (không còn readonly).
"""


def migrate(cr, version):
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_roof_kind CASCADE")
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_roof_subtype CASCADE")
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_roof_type CASCADE")
