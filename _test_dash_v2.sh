#!/bin/bash
echo "===== Odoo shell test ====="
cat > /tmp/test_dash.py << 'PYEOF'
Lead = env['crm.lead']
result = Lead.with_user(36).dashboard_leads_with_problems(user_id=36)
print("Returned", len(result), "leads:")
for r in result[:20]:
    print("  -", r.get('id'), r.get('name'), r.get('stage_code'))

scope_user, label, domain_user, _ = Lead._dashboard_resolve_scope(36)
print("Scope:", label, domain_user)
urgent_ids = Lead._dashboard_urgent_construction_ids(domain_user)
print("Urgent IDs:", urgent_ids)

Stage = env['crm.stage']
mid_stage_ids = Stage.search([('code', 'in', ['quote', 'negotiate'])]).ids
print("Mid stage ids:", mid_stage_ids)

raw_leads = Lead.search(
    domain_user + [
        ('stage_id', 'in', mid_stage_ids),
        ('active', '=', True),
        ('vd_intake_complete', '=', True),
        ('id', 'not in', urgent_ids),
    ],
)
print("Raw match:", len(raw_leads))
for l in raw_leads:
    print("  -", l.id, l.name, "user_id=", l.user_id.id)
PYEOF

sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin shell \
  -c /etc/odoo18.conf -d vinaduy_crm --no-http < /tmp/test_dash.py 2>&1 | tail -40
