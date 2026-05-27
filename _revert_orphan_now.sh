#!/bin/bash
set -e

echo '===== Orphan KH (stage quote/nego + locked=False) — TRUOC ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, s.code, l.vd_intake_complete, l.user_id, u.login
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
LEFT JOIN res_users u ON u.id = l.user_id
WHERE s.code IN ('quote', 'negotiate')
  AND l.active = TRUE
  AND COALESCE(l.vd_intake_locked, FALSE) = FALSE
ORDER BY l.user_id, l.id DESC;
"

echo '===== REVERT all orphan ve stage new ====='
sudo -u postgres psql -d vinaduy_crm -c "
WITH new_stage AS (SELECT id FROM crm_stage WHERE code='new' LIMIT 1)
UPDATE crm_lead
SET stage_id = (SELECT id FROM new_stage),
    vd_intake_open = TRUE
FROM crm_stage s
WHERE s.id = crm_lead.stage_id
  AND s.code IN ('quote', 'negotiate')
  AND crm_lead.active = TRUE
  AND COALESCE(crm_lead.vd_intake_locked, FALSE) = FALSE
RETURNING crm_lead.id, crm_lead.name;
"

echo '===== RESTART odoo ====='
systemctl restart odoo18
sleep 3
systemctl is-active odoo18

echo '===== SAU: con orphan? ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE s.code IN ('quote', 'negotiate')
  AND l.active = TRUE
  AND COALESCE(l.vd_intake_locked, FALSE) = FALSE;
"
