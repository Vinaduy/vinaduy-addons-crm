#!/bin/bash
set -e

echo '===== TRUOC: orphan quote leads ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, s.code, l.vd_intake_complete, l.vd_intake_locked
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE s.code IN ('quote', 'negotiate')
  AND l.active = TRUE
  AND COALESCE(l.vd_intake_locked, FALSE) = FALSE
ORDER BY l.id DESC;
"

echo '===== LOCK leads complete=True at quote/negotiate ====='
sudo -u postgres psql -d vinaduy_crm -c "
UPDATE crm_lead
SET vd_intake_locked = TRUE,
    vd_intake_open = FALSE
FROM crm_stage s
WHERE s.id = crm_lead.stage_id
  AND s.code IN ('quote', 'negotiate')
  AND crm_lead.active = TRUE
  AND COALESCE(crm_lead.vd_intake_locked, FALSE) = FALSE
  AND crm_lead.vd_intake_complete = TRUE
RETURNING crm_lead.id, crm_lead.name;
"

echo '===== REVERT leads complete=False ve stage new ====='
sudo -u postgres psql -d vinaduy_crm -c "
WITH new_stage AS (SELECT id FROM crm_stage WHERE code='new' LIMIT 1)
UPDATE crm_lead
SET stage_id = (SELECT id FROM new_stage),
    vd_intake_locked = FALSE
FROM crm_stage s
WHERE s.id = crm_lead.stage_id
  AND s.code IN ('quote', 'negotiate')
  AND crm_lead.active = TRUE
  AND COALESCE(crm_lead.vd_intake_locked, FALSE) = FALSE
  AND COALESCE(crm_lead.vd_intake_complete, FALSE) = FALSE
RETURNING crm_lead.id, crm_lead.name;
"

echo '===== RESTART Odoo (clear cache) ====='
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
