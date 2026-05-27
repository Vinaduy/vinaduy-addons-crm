#!/bin/bash
set -e

echo '===== Hau user_id = 36 — list ALL his leads ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, s.code AS stage,
       l.vd_intake_complete AS compl,
       l.active AS act
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE l.user_id = 36
ORDER BY l.id DESC;
"

echo '===== Hau leads at quote/negotiate (raw filter) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, s.code, l.vd_intake_complete, l.active
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE l.user_id = 36
  AND s.code IN ('quote', 'negotiate')
  AND l.active = TRUE
  AND l.vd_intake_complete = TRUE;
"

echo '===== Test name_search filter (NEW domain user spec) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT id, name FROM crm_lead WHERE id=1738;
"

echo '===== Check if Chi Thoa in URGENT (Thi cong gap) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, l.vd_intake_timeline,
       l.vd_intake_complete, l.user_id
FROM crm_lead l
WHERE l.id=1738;
"
