#!/bin/bash
# NOSTOP upgrade — chạy odoo-bin -u nhưng KHÔNG stop systemd Odoo.
# Workers tiếp tục serve trong lúc upgrade chạy ở process riêng.
# OK cho XML data changes (ir.ui.view, ir.actions.report, ir.model.data records).
# KHÔNG OK nếu đổi Python (.py) — workers giữ code cũ trong RAM.
# Tổng thời gian: ~20-40s (vs 60-120s của full stop+start).

set -e

echo '====== UPGRADE (no-stop, odoo-bin -u vd_crm_lead) ======'
START=$(date +%s)
sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin \
  -c /etc/odoo18.conf \
  -d vinaduy_crm \
  -u vd_crm_lead \
  --stop-after-init --no-http \
  --log-level=warn \
  --max-cron-threads=0 \
  --workers=0 \
  > /tmp/up.log 2>&1
RC=$?
END=$(date +%s)
echo "UPGRADE_RC=$RC  TIME=$((END-START))s  LOG_SIZE=$(wc -c < /tmp/up.log) bytes"

echo '====== INVALIDATE ASSET CACHE (assets sẽ rebuild ở request kế) ======'
sudo -u postgres psql -d vinaduy_crm -tAc "
DELETE FROM ir_attachment
WHERE name LIKE 'web.assets_%'
   OR url LIKE '/web/assets/%';
" > /dev/null

echo '====== ERRORS trong log ======'
grep -iE 'error|traceback|critical|denied|cannot|failed' /tmp/up.log | head -20 || true

echo '====== STATUS ======'
systemctl is-active odoo18 && echo 'Odoo vẫn đang chạy (không downtime)' || echo 'CẢNH BÁO: Odoo không active'

echo '====== DONE ======'
echo 'Hard refresh browser (Ctrl+Shift+R) để load asset mới.'
