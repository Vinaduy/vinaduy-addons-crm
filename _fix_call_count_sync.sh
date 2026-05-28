#!/bin/bash
set -e

echo '===== TRUOC: leads voi call_count STALE ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, l.call_count AS stored, COUNT(sc.id) AS actual
FROM crm_lead l
LEFT JOIN stringee_call sc ON sc.lead_id = l.id
GROUP BY l.id, l.name, l.call_count
HAVING l.call_count != COUNT(sc.id)
ORDER BY actual DESC
LIMIT 20;
"

echo '===== TOTAL stale ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM (
  SELECT l.id FROM crm_lead l
  LEFT JOIN stringee_call sc ON sc.lead_id = l.id
  GROUP BY l.id, l.call_count
  HAVING l.call_count != COUNT(sc.id)
) sub;
"

echo '===== FIX: sync call_count tu stringee_call ====='
sudo -u postgres psql -d vinaduy_crm -c "
UPDATE crm_lead l
SET call_count = subq.actual
FROM (
  SELECT l2.id AS lead_id, COUNT(sc.id) AS actual
  FROM crm_lead l2
  LEFT JOIN stringee_call sc ON sc.lead_id = l2.id
  GROUP BY l2.id
) subq
WHERE l.id = subq.lead_id
  AND COALESCE(l.call_count, 0) != subq.actual;
"

echo '===== Restart Odoo ====='
systemctl restart odoo18
sleep 3
systemctl is-active odoo18

echo '===== SAU: con stale? ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM (
  SELECT l.id FROM crm_lead l
  LEFT JOIN stringee_call sc ON sc.lead_id = l.id
  GROUP BY l.id, l.call_count
  HAVING l.call_count != COUNT(sc.id)
) sub;
"

echo '===== Check dang cuong sau fix ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT id, name, call_count FROM crm_lead WHERE id=1477;
"
