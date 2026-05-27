#!/bin/bash
# One-off: bulk unlock vd_intake_locked tren toan bo crm_lead
set -e

echo '===== TRUOC ====='
sudo -u postgres psql -d vinaduy_crm -tAc \
  "SELECT COUNT(*) FROM crm_lead WHERE vd_intake_locked = true;"

echo '===== UPDATE ====='
sudo -u postgres psql -d vinaduy_crm -c \
  "UPDATE crm_lead SET vd_intake_locked = false, vd_intake_open = true WHERE vd_intake_locked = true;"

echo '===== RESTART ODOO ====='
systemctl restart odoo18
sleep 3
systemctl is-active odoo18

echo '===== SAU ====='
sudo -u postgres psql -d vinaduy_crm -tAc \
  "SELECT COUNT(*) FROM crm_lead WHERE vd_intake_locked = true;"
