#!/bin/bash
set -e

cat > /tmp/test_dash.py << 'PYEOF'
from odoo import api, SUPERUSER_ID
import odoo
db_name = 'vinaduy_crm'
registry = odoo.modules.registry.Registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Test cho user 36 (Hau)
    Lead = env['crm.lead']
    result = Lead.with_user(36).dashboard_leads_with_problems(user_id=36)
    print(f"Returned {len(result)} leads:")
    for r in result[:20]:
        print(f"  - id={r['id']}, name={r['name']}, stage={r.get('stage_code', '?')}")

    # Test urgent_ids
    scope_user, label, domain_user, _ = Lead._dashboard_resolve_scope(36)
    print(f"\nScope: user={label}, domain_user={domain_user}")
    urgent_ids = Lead._dashboard_urgent_construction_ids(domain_user)
    print(f"Urgent IDs for Hau: {urgent_ids}")

    # Raw match query
    Stage = env['crm.stage']
    mid_stage_ids = Stage.search([('code', 'in', ['quote', 'negotiate'])]).ids
    raw_leads = Lead.search(
        domain_user + [
            ('stage_id', 'in', mid_stage_ids),
            ('active', '=', True),
            ('vd_intake_complete', '=', True),
            ('id', 'not in', urgent_ids),
        ],
    )
    print(f"\nRaw search match: {len(raw_leads)} leads")
    for l in raw_leads:
        print(f"  - id={l.id}, name={l.name}, user_id={l.user_id.id}")
PYEOF

sudo -u odoo18 /opt/odoo18/venv/bin/python3 -c "
import sys
sys.path.insert(0, '/opt/odoo18')
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo18.conf'])
exec(open('/tmp/test_dash.py').read())
"
