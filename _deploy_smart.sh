#!/bin/bash
# SMART deploy — tự pick mode dựa trên git diff vs HEAD~1.
#   - Chỉ asset (static/src/**) → _deploy_fast.sh (~3s, no downtime)
#   - Có Python/manifest/data XML đổi → _deploy_upgrade.sh (~60-120s)
# Chạy: ssh root@163.44.192.82 'cd /root/vinaduy-addons-crm && bash _deploy_smart.sh'

set -e
cd "$(dirname "$0")"

# So sánh HEAD vs HEAD~1 (commit vừa pull về)
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)

if [ -z "$CHANGED_FILES" ]; then
    echo 'Không có file nào đổi giữa HEAD và HEAD~1 — abort.'
    exit 0
fi

echo '====== CHANGED FILES ======'
echo "$CHANGED_FILES"

# Phân loại: nếu CHỈ có file static/src/** → fast, else upgrade
NEEDS_UPGRADE=0
while IFS= read -r f; do
    case "$f" in
        */static/src/*)
            ;;  # asset only — OK fast
        *)
            NEEDS_UPGRADE=1
            echo "→ '$f' yêu cầu FULL UPGRADE"
            ;;
    esac
done <<< "$CHANGED_FILES"

if [ "$NEEDS_UPGRADE" -eq 1 ]; then
    echo '====== MODE: FULL UPGRADE (chậm ~60-120s, downtime 502) ======'
    bash _deploy_upgrade.sh
else
    echo '====== MODE: FAST ASSET-ONLY (~3s, no downtime) ======'
    bash _deploy_fast.sh
fi
