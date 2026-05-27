#!/bin/bash
# One-off: tim lead "Anh Đỗ Minh Chiến" + log lý do hủy + ai bấm
set -e

PHONE='0355933443'
NAME='Đỗ Minh Chiến'

echo '===== LEAD INFO ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT
  l.id, l.name, l.phone, l.partner_name,
  l.vd_lost_reason, l.vd_lost_date,
  l.write_date, u.login AS write_user,
  s.name AS stage_name
FROM crm_lead l
LEFT JOIN res_users u ON u.id = l.write_uid
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE l.phone = '${PHONE}'
   OR l.partner_name ILIKE '%${NAME}%'
   OR l.name ILIKE '%${NAME}%'
LIMIT 5;
"

echo '===== MAIL MESSAGES (chatter) ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT
  m.id, m.date, u.login AS author_login,
  substring(regexp_replace(coalesce(m.body, ''), '<[^>]+>', '', 'g') from 1 for 200) AS body_excerpt
FROM mail_message m
LEFT JOIN res_users u ON u.partner_id = m.author_id
WHERE m.model = 'crm.lead'
  AND m.res_id IN (
    SELECT id FROM crm_lead WHERE phone = '${PHONE}' OR partner_name ILIKE '%${NAME}%' OR name ILIKE '%${NAME}%'
  )
ORDER BY m.date DESC
LIMIT 20;
"

echo '===== TRACKING VALUES - STAGE CHANGES ====='
sudo -u postgres psql -d vinaduy_crm -c "
SELECT
  m.date, u.login AS who,
  s_old.name AS from_stage, s_new.name AS to_stage
FROM mail_tracking_value tv
JOIN mail_message m ON m.id = tv.mail_message_id
JOIN ir_model_fields f ON f.id = tv.field_id AND f.name = 'stage_id'
LEFT JOIN res_users u ON u.partner_id = m.author_id
LEFT JOIN crm_stage s_old ON s_old.id = tv.old_value_integer
LEFT JOIN crm_stage s_new ON s_new.id = tv.new_value_integer
WHERE m.model = 'crm.lead'
  AND m.res_id IN (
    SELECT id FROM crm_lead WHERE phone = '${PHONE}' OR partner_name ILIKE '%${NAME}%' OR name ILIKE '%${NAME}%'
  )
ORDER BY m.date DESC;
"
