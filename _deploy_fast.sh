#!/bin/bash
# FAST deploy — KHÔNG restart Odoo, không upgrade module.
# Chỉ dùng khi change CHỈ là asset (SCSS/JS/XML template trong static/src/).
# Cách hoạt động:
#   1. Xoá cached web.assets_* attachments → Odoo regenerate bundle ở request kế.
#   2. Reload templates QWeb qua Odoo HTTP endpoint (nếu cần).
#   3. KHÔNG stop/start systemctl → KHÔNG 502, không cắt cuộc gọi Stringee.
# Tổng thời gian: ~2-5s (vs 50-125s của _deploy_upgrade.sh)
# CẢNH BÁO: KHÔNG dùng khi đổi models/*.py, views/*.xml (data files), __manifest__.py
#           → dùng _deploy_upgrade.sh cho các change đó.

set -e

echo '====== INVALIDATE ASSET CACHE ======'
# Xoá bundle web.assets_backend + frontend + qweb templates cached
sudo -u postgres psql -d vinaduy_crm -tAc "
DELETE FROM ir_attachment
WHERE name LIKE 'web.assets_%'
   OR url LIKE '/web/assets/%';
" | xargs -I {} echo "Deleted {} cached attachments"

echo '====== SIGNAL WORKERS RELOAD (fix bug 2026-06-07) ======'
# CHỈ xoá attachment KHÔNG đủ: worker đang chạy giữ HASH bundle CŨ trong RAM →
# trang bootstrap vẫn trỏ bundle cũ → browser nạp bản cũ (suốt nhiều lần deploy
# trước "không thấy đổi"). Bơm registry signaling → MỌI worker tự reload registry
# ở request kế (xoá cache bundle hash), KHÔNG cần restart → vẫn no-downtime.
sudo -u postgres psql -d vinaduy_crm -tAc "SELECT nextval('base_registry_signaling');" \
  | xargs -I {} echo "registry_signaling -> {}"

echo '====== STATUS ======'
systemctl is-active odoo18 && echo 'Odoo vẫn đang chạy (không downtime)' || echo 'CẢNH BÁO: Odoo không active'

echo '====== DONE ======'
echo 'F5 / Ctrl+Shift+R browser để load asset mới.'
