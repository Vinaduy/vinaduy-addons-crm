#!/bin/bash
# Fix cached stage_code / stage_is_lost / stage_is_won bi stale sau bulk SQL update
set -e

echo '===== TRUOC: mismatched count ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM crm_lead l JOIN crm_stage s ON s.id=l.stage_id
WHERE l.stage_code != s.code
   OR COALESCE(l.stage_is_lost, FALSE) != COALESCE(s.is_lost, FALSE)
   OR COALESCE(l.stage_is_won, FALSE) != COALESCE(s.is_won, FALSE);
"

echo '===== Sample 10 mismatched ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, l.stage_id, s.code AS real_code, l.stage_code AS cached_code,
       s.is_lost AS real_lost, l.stage_is_lost AS cached_lost,
       s.is_won AS real_won, l.stage_is_won AS cached_won
FROM crm_lead l JOIN crm_stage s ON s.id=l.stage_id
WHERE l.stage_code != s.code
   OR COALESCE(l.stage_is_lost, FALSE) != COALESCE(s.is_lost, FALSE)
   OR COALESCE(l.stage_is_won, FALSE) != COALESCE(s.is_won, FALSE)
LIMIT 10;
"

echo '===== FIX: sync cached fields tu stage_id ====='
sudo -u postgres psql -d vinaduy_crm -c "
UPDATE crm_lead l
SET stage_code    = s.code,
    stage_is_lost = COALESCE(s.is_lost, FALSE),
    stage_is_won  = COALESCE(s.is_won, FALSE)
FROM crm_stage s
WHERE s.id = l.stage_id
  AND (l.stage_code != s.code
       OR COALESCE(l.stage_is_lost, FALSE) != COALESCE(s.is_lost, FALSE)
       OR COALESCE(l.stage_is_won, FALSE) != COALESCE(s.is_won, FALSE));
"

echo '===== Restart Odoo ====='
systemctl restart odoo18
sleep 3
systemctl is-active odoo18

echo '===== SAU: mismatched count ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM crm_lead l JOIN crm_stage s ON s.id=l.stage_id
WHERE l.stage_code != s.code
   OR COALESCE(l.stage_is_lost, FALSE) != COALESCE(s.is_lost, FALSE)
   OR COALESCE(l.stage_is_won, FALSE) != COALESCE(s.is_won, FALSE);
"
