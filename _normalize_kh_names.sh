#!/bin/bash
# Backfill: normalize ten KH theo spec 2026-05-28
# Logic: title-case tung " - " segment, trừ segment "VINADUY"/"HN"/"HCM2"...
set -e

cat > /tmp/normalize_kh.py << 'PYEOF'
Lead = env['crm.lead']
# Lay tat ca leads can fix (name/partner_name/contact_name)
leads = Lead.search([])
n_updated = 0
for lead in leads:
    vals = {}
    for f in ('name', 'partner_name', 'contact_name'):
        old = lead[f]
        if not old:
            continue
        new = Lead._vd_normalize_kh_name(old)
        if new != old:
            vals[f] = new
    if vals:
        lead.with_context(mail_notrack=True).write(vals)
        n_updated += 1
print(f"Updated {n_updated} leads")
env.cr.commit()
PYEOF

sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin shell \
  -c /etc/odoo18.conf -d vinaduy_crm --no-http < /tmp/normalize_kh.py 2>&1 | tail -10
