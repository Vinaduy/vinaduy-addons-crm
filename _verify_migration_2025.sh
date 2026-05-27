#!/bin/bash
set -e

echo '===== CHECK res_country_state schema ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT column_name FROM information_schema.columns
WHERE table_name='res_country_state' AND table_schema='public'
ORDER BY ordinal_position;
"

echo '===== ALL VN PROVINCES ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.id, s.name, s.code
FROM res_country_state s
WHERE s.country_id = (SELECT id FROM res_country WHERE code='VN')
ORDER BY s.name;
"

echo '===== TOTAL ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM res_country_state s
WHERE s.country_id = (SELECT id FROM res_country WHERE code='VN');
"

echo '===== WARDS by province ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.name AS province, COUNT(d.id) AS wards
FROM res_country_state s
LEFT JOIN vd_district d ON d.state_id = s.id
WHERE s.country_id = (SELECT id FROM res_country WHERE code='VN')
GROUP BY s.name
HAVING COUNT(d.id) > 0
ORDER BY wards DESC;
"

echo '===== LEAD distribution by province ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.name AS province, COUNT(l.id) AS leads
FROM crm_lead l
LEFT JOIN res_country_state s ON s.id = l.vd_intake_province_id
WHERE l.vd_intake_province_id IS NOT NULL
GROUP BY s.name
ORDER BY leads DESC
LIMIT 20;
"
