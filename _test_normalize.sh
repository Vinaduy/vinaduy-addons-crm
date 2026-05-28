#!/bin/bash
set -e
cat > /tmp/test_norm.py << 'PYEOF'
Lead = env['crm.lead']
# Direct test on string
for test in ["đặng cương", "Anh Nghiêm Mạnh Dưong", "ĐOÀN VŨ GIA HÂN", "VINADUY - anh Sỹ Chuẩn - HN"]:
    result = Lead._vd_normalize_kh_name(test)
    print(f"{test!r} -> {result!r}")

# Force normalize for lead 1477
print("\n--- Force lead 1477 normalize ---")
l = Lead.browse(1477)
print(f"Current name: {l.name!r}")
print(f"Current partner_name: {l.partner_name!r}")
new_n = Lead._vd_normalize_kh_name(l.name)
new_pn = Lead._vd_normalize_kh_name(l.partner_name)
print(f"Normalized name: {new_n!r}")
print(f"Normalized partner_name: {new_pn!r}")
vals = {}
if new_n != l.name:
    vals['name'] = new_n
if new_pn != l.partner_name:
    vals['partner_name'] = new_pn
print(f"Vals to write: {vals}")
if vals:
    l.with_context(mail_notrack=True).write(vals)
    env.cr.commit()
    print("WROTE!")
    print(f"After: {l.name!r}")
PYEOF
sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin shell \
  -c /etc/odoo18.conf -d vinaduy_crm --no-http < /tmp/test_norm.py 2>&1 | tail -20
