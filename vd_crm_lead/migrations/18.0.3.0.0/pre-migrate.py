"""Pre-migrate 18.0.3.0.0
- Bỏ field vd_intake_finish_level (không còn binary "tho/tron_goi", chỉ còn 1 mode).
"""


def migrate(cr, version):
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_finish_level CASCADE")
