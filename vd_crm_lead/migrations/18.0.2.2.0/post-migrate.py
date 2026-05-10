"""Post-migrate 18.0.2.2.0
- Populate ~705 huyện/quận/thị xã VN vào vd.district (idempotent).
"""

from odoo.addons.vd_crm_lead import _populate_vn_districts


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _populate_vn_districts(env)
