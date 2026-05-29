#!/bin/bash
# Server pull helper — chạy trên vinaduy.com:
#   bash /root/vinaduy-addons-crm/pull.sh
# Tự pick fast (asset-only ~3s) vs upgrade (Python/data XML ~60-120s).

set -e
cd /root/vinaduy-addons-crm

echo '====== GIT PULL ======'
git pull --rebase --autostash

echo ''
echo '====== SMART DEPLOY ======'
bash _deploy_smart.sh
