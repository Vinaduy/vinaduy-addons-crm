#!/bin/bash
set -e

echo '===== LEAD INFO ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, l.partner_name, l.phone, l.user_id, u.login AS assigned_to,
       s.code AS stage_code, s.name AS stage_name,
       l.vd_intake_complete, l.vd_intake_locked, l.active
FROM crm_lead l
LEFT JOIN res_users u ON u.id = l.user_id
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE l.partner_name ILIKE '%Thoa%' OR l.name ILIKE '%Thoa%' OR l.phone='0814814347'
ORDER BY l.id DESC
LIMIT 5;
"

echo '===== INTAKE FIELDS DETAIL (Chi Thoa) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT
  vd_intake_province_id, vd_intake_district,
  vd_intake_timeline, vd_intake_total_m2,
  vd_intake_house_type, vd_intake_foundation_type,
  vd_intake_floor_1_m2, vd_intake_land_type, vd_intake_soil_dump,
  vd_intake_car_access_select, vd_intake_budget_range, vd_intake_dimensions
FROM crm_lead l
WHERE (l.partner_name ILIKE '%Thoa%' OR l.name ILIKE '%Thoa%' OR l.phone='0814814347')
  AND l.active = TRUE
LIMIT 3;
"

echo '===== T1 FUNCTION IDS ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT cl.id AS lead_id, COUNT(rel.tag_id) AS t1_func_count
FROM crm_lead cl
LEFT JOIN vd_lead_floor_func_line rel ON rel.lead_id=cl.id AND rel.field_name='vd_intake_floor_1_function_ids'
WHERE cl.partner_name ILIKE '%Thoa%' OR cl.name ILIKE '%Thoa%'
GROUP BY cl.id;
"
