#!/bin/bash
# ULTRA-FAST view/report reload — KHÔNG chạy `-u`, chỉ load XML files đã đổi
# vào DB qua odoo-bin shell. Thường ~3-8s thay vì 200-300s của full upgrade.
#
# CHỈ AN TOÀN khi changes chỉ có XML views/reports (không Python, không scss,
# không security, không __manifest__). Smart deploy sẽ pick mode này khi đủ
# điều kiện.

set -e

REPO_DIR="${REPO_DIR:-/root/vinaduy-addons-crm}"
DB="${DB:-vinaduy_crm}"

# Lấy list .xml đổi giữa HEAD~1 → HEAD
CHANGED_XML=$(git -C "$REPO_DIR" diff --name-only HEAD~1 HEAD | grep -E '\.xml$' | grep -E '/(views|reports|data)/' || true)
if [ -z "$CHANGED_XML" ]; then
    echo 'Không có XML views/reports/data nào đổi — skip.'
    exit 0
fi

echo '====== XML FILES TO RELOAD ======'
echo "$CHANGED_XML"

# Build Python snippet: load từng file qua tools.convert_file (chỉ load file
# đó, KHÔNG quét toàn bộ module → nhanh hơn `-u` nhiều).
PYTHON_SNIPPET=$(cat <<PYEOF
import os
from odoo.tools.convert import convert_file
module_name = 'vd_crm_lead'
repo = '$REPO_DIR'
files = """$CHANGED_XML""".strip().split('\n')
ok = 0
for rel in files:
    rel = rel.strip()
    if not rel:
        continue
    # rel = "vd_crm_lead/views/crm_lead_views.xml" — strip module prefix cho convert_file
    parts = rel.split('/', 1)
    if len(parts) != 2:
        continue
    mod, inner = parts
    full = os.path.join(repo, rel)
    if not os.path.exists(full):
        print('SKIP missing:', full)
        continue
    print('LOAD:', rel)
    convert_file(env, mod, inner, idref={}, mode='update', noupdate=False, kind='data', pathname=full)
    ok += 1
env.cr.commit()
# Clear caches để view mới hiển thị ngay
env['ir.ui.view'].clear_caches()
env.registry.clear_cache()
print(f'OK loaded={ok}')
PYEOF
)

echo '====== SHELL LOAD (no `-u`, no module rescan) ======'
START=$(date +%s)
echo "$PYTHON_SNIPPET" | sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin shell \
  -c /etc/odoo18.conf -d "$DB" --no-http --log-level=warn > /tmp/views.log 2>&1
RC=$?
END=$(date +%s)
echo "SHELL_RC=$RC  TIME=$((END-START))s"
tail -20 /tmp/views.log

echo '====== INVALIDATE ASSET CACHE ======'
sudo -u postgres psql -d "$DB" -tAc "
DELETE FROM ir_attachment
WHERE name LIKE 'web.assets_%'
   OR url LIKE '/web/assets/%';
" > /dev/null 2>&1 || echo 'WARN: psql delete asset attachments fail (may need DB perms)'

echo '====== STATUS ======'
systemctl is-active odoo18 && echo 'Odoo vẫn đang chạy (no downtime)' || echo 'CẢNH BÁO: Odoo không active'

echo '====== DONE ======'
echo 'Hard refresh browser (Ctrl+Shift+R) để load asset mới.'
