#!/bin/bash
# Bulk restore KH ma write_uid = OdooBot/superuser va vd_lost_user_id = NULL
# (data cu — khong xac dinh duoc NV that su huy)
set -e

echo '===== TRUOC: COUNT cantidates ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT COUNT(*) AS to_restore
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE s.code = 'lost'
  AND l.vd_lost_user_id IS NULL
  AND COALESCE(l.vd_lost_is_auto, FALSE) = FALSE
  AND COALESCE(l.write_uid, 0) IN (1, 2);
"

echo '===== SAMPLE 13 KH ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.partner_name, l.phone, l.vd_lost_date,
       substring(l.vd_lost_reason from 1 for 60) AS reason_excerpt,
       wu.login AS write_user
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
LEFT JOIN res_users wu ON wu.id = l.write_uid
WHERE s.code = 'lost'
  AND l.vd_lost_user_id IS NULL
  AND COALESCE(l.vd_lost_is_auto, FALSE) = FALSE
  AND COALESCE(l.write_uid, 0) IN (1, 2)
ORDER BY l.vd_lost_date DESC;
"

echo '===== EXECUTING RESTORE ====='
sudo -u postgres psql -d vinaduy_crm -c "
WITH new_stage AS (SELECT id FROM crm_stage WHERE code='new' LIMIT 1)
UPDATE crm_lead l
SET stage_id      = (SELECT id FROM new_stage),
    active        = TRUE,
    vd_lost_reason   = NULL,
    vd_lost_date     = NULL,
    vd_lost_user_id  = NULL,
    vd_lost_is_auto  = FALSE
FROM crm_stage s
WHERE s.id = l.stage_id
  AND s.code = 'lost'
  AND l.vd_lost_user_id IS NULL
  AND COALESCE(l.vd_lost_is_auto, FALSE) = FALSE
  AND COALESCE(l.write_uid, 0) IN (1, 2)
RETURNING l.id, l.partner_name;
"

echo '===== RESTART ODOO ====='
systemctl restart odoo18
sleep 3
systemctl is-active odoo18

echo '===== SAU: COUNT con lai ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*)
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE s.code = 'lost'
  AND l.vd_lost_user_id IS NULL
  AND COALESCE(l.vd_lost_is_auto, FALSE) = FALSE
  AND COALESCE(l.write_uid, 0) IN (1, 2);
"
