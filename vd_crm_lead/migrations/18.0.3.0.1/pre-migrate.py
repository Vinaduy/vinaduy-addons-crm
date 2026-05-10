"""Pre-migrate 18.0.3.0.1 — revert về popup-only.
- Bỏ field vd_intake_expanded (không còn panel inline expand).
"""


def migrate(cr, version):
    cr.execute("ALTER TABLE crm_lead DROP COLUMN IF EXISTS vd_intake_expanded CASCADE")
