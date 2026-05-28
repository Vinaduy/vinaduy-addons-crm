#!/bin/bash
set -e

echo '===== Step 1: Manual fix 2 leads bi mangled v9.163 ====='
sudo -u postgres psql -d vinaduy_crm -c "
UPDATE crm_lead SET
  name = REPLACE(REPLACE(name, ' Tni', ' TNI'), 'Tp.hcm', 'TP.HCM'),
  partner_name = REPLACE(REPLACE(COALESCE(partner_name, ''), ' Tni', ' TNI'), 'Tp.hcm', 'TP.HCM')
WHERE name LIKE '% Tni%' OR name LIKE '%Tp.hcm%'
   OR partner_name LIKE '% Tni%' OR partner_name LIKE '%Tp.hcm%'
RETURNING id, name;
"

echo '===== Step 2: Re-run backfill voi logic v9.164 ====='
cat > /tmp/normalize_kh.py << 'PYEOF'
Lead = env['crm.lead']
leads = Lead.search([])
n_updated = 0
samples = []
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
        if len(samples) < 10:
            samples.append((lead.id, lead.name, vals))
        lead.with_context(mail_notrack=True).write(vals)
        n_updated += 1
print(f"Updated {n_updated} leads")
for s in samples:
    print(f"  - id={s[0]}, old_name={s[1]!r}, new={s[2]}")
env.cr.commit()
PYEOF

sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin shell \
  -c /etc/odoo18.conf -d vinaduy_crm --no-http < /tmp/normalize_kh.py 2>&1 | tail -15

echo '===== Step 3: Verify ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT id, name FROM crm_lead WHERE id IN (1733, 1721, 1525, 1477, 1735);
"
