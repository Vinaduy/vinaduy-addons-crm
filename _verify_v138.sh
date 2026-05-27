#!/bin/bash
set -e

echo '===== COUNT tinh moi (vd_is_active_2025=TRUE) ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM res_country_state
WHERE country_id = (SELECT id FROM res_country WHERE code='VN')
  AND vd_is_active_2025 = TRUE;
"

echo '===== LIST 34 active 2025 ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT name FROM res_country_state
WHERE country_id = (SELECT id FROM res_country WHERE code='VN')
  AND vd_is_active_2025 = TRUE
ORDER BY name;
"

echo '===== TINH CU bi rename (cu - da sap nhap) ====='
sudo -u postgres psql -d vinaduy_crm -tAc "
SELECT COUNT(*) FROM res_country_state
WHERE country_id = (SELECT id FROM res_country WHERE code='VN')
  AND name LIKE '%(cũ - đã sáp nhập)%';
"

echo '===== LEADS distribution by province (only active 2025) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.name AS province, COUNT(l.id) AS leads
FROM crm_lead l
JOIN res_country_state s ON s.id = l.vd_intake_province_id
GROUP BY s.name
ORDER BY leads DESC;
"

echo '===== WARDS distribution by province (top 10) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.name AS province, COUNT(d.id) AS wards
FROM res_country_state s
JOIN vd_district d ON d.state_id = s.id
WHERE s.country_id = (SELECT id FROM res_country WHERE code='VN')
GROUP BY s.name
ORDER BY wards DESC
LIMIT 10;
"

echo '===== LEAD pointing to OLD province (lo sao sot) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT s.name AS old_province, COUNT(l.id) AS leads
FROM crm_lead l
JOIN res_country_state s ON s.id = l.vd_intake_province_id
WHERE COALESCE(s.vd_is_active_2025, FALSE) = FALSE
GROUP BY s.name
ORDER BY leads DESC;
"
