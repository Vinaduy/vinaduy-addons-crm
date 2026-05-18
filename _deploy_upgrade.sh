#!/bin/bash
# Tạm thời để debug upgrade vd_crm_lead trên vinaduy.com
# Chạy: ssh root@163.44.192.82 'bash -s' < _deploy_upgrade.sh

echo '====== STOP ======'
systemctl stop odoo18
echo "STOP_RC=$?"

echo '====== UPGRADE (chạy odoo-bin -u vd_crm_lead) ======'
sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin \
  -c /etc/odoo18.conf \
  -d vinaduy_crm \
  -u vd_crm_lead \
  --stop-after-init --no-http \
  > /tmp/up.log 2>&1
RC=$?
echo "UPGRADE_RC=$RC"
echo "LOG_SIZE=$(wc -c < /tmp/up.log) bytes"

systemctl start odoo18
sleep 2

echo '====== ERRORS trong log ======'
grep -iE 'error|traceback|critical|denied|cannot|failed|warning' /tmp/up.log | head -30

echo '====== TAIL 80 dòng cuối log ======'
tail -80 /tmp/up.log

echo '====== COLUMN CHECK (DB) ======'
sudo -u postgres psql -d vinaduy_crm -c "SELECT column_name FROM information_schema.columns WHERE table_name='vd_lead_problem' AND (column_name='contact_called' OR column_name LIKE 'tk_%') ORDER BY column_name;"
