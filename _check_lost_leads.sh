#!/bin/bash
set -e

echo '===== TONG SO KH LOST ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT COUNT(*) AS total_lost
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
WHERE s.code = 'lost';
"

echo '===== BREAKDOWN vd_lost_user_id ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT
  COALESCE(u.login, '— NULL —') AS lost_user_login,
  l.vd_lost_user_id,
  l.vd_lost_is_auto,
  COUNT(*) AS cnt
FROM crm_lead l
JOIN crm_stage s ON s.id = l.stage_id
LEFT JOIN res_users u ON u.id = l.vd_lost_user_id
WHERE s.code = 'lost'
GROUP BY u.login, l.vd_lost_user_id, l.vd_lost_is_auto
ORDER BY cnt DESC;
"

echo '===== TIM KH Dien Co Nam Thuy ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT l.id, l.name, l.partner_name, l.phone,
       l.vd_lost_user_id, u.login AS lost_user,
       l.vd_lost_is_auto,
       l.write_uid, wu.login AS write_user,
       substring(l.vd_lost_reason from 1 for 80) AS reason
FROM crm_lead l
LEFT JOIN res_users u ON u.id = l.vd_lost_user_id
LEFT JOIN res_users wu ON wu.id = l.write_uid
WHERE l.partner_name ILIKE '%Điện Cơ Nam Thúy%' OR l.name ILIKE '%Điện Cơ Nam Thúy%' OR l.phone='0977777067'
LIMIT 5;
"
