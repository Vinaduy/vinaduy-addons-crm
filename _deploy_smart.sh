#!/bin/bash
# SMART deploy — pick mode dựa trên git diff HEAD~1 HEAD.
#   - Chỉ asset (static/src/**)                     → _deploy_fast.sh        (~2s, no downtime)
#   - Asset + data XML (views, reports, data)       → _deploy_upgrade_nostop (~20-40s, no downtime)
#   - Có Python (models/, wizard/) hoặc security    → _deploy_upgrade.sh     (~60-120s, có 502)
# Chạy: bash _deploy_smart.sh

set -e
cd "$(dirname "$0")"

CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)
if [ -z "$CHANGED_FILES" ]; then
    echo 'Không có file nào đổi giữa HEAD và HEAD~1 — abort.'
    exit 0
fi

echo '====== CHANGED FILES ======'
echo "$CHANGED_FILES"

NEEDS_FULL_UPGRADE=0
HAS_DATA_XML=0
HAS_ASSET_ONLY=0

while IFS= read -r f; do
    case "$f" in
        */static/src/*)
            HAS_ASSET_ONLY=1 ;;
        */models/*|*/wizard/*|*/security/*|*/controllers/*|*/__init__*)
            NEEDS_FULL_UPGRADE=1
            echo "  → '$f' yêu cầu FULL UPGRADE (Python/security)" ;;
        *.py)
            NEEDS_FULL_UPGRADE=1
            echo "  → '$f' yêu cầu FULL UPGRADE (Python)" ;;
        */__manifest__.py|*/views/*|*/reports/*|*/data/*|*.xml|*.csv)
            HAS_DATA_XML=1 ;;
        _deploy_*.sh|push.ps1|pull.sh|*.md|.git*)
            echo "  → '$f' bỏ qua (script/docs)" ;;
        *)
            HAS_DATA_XML=1 ;;
    esac
done <<< "$CHANGED_FILES"

if [ "$NEEDS_FULL_UPGRADE" -eq 1 ]; then
    echo '====== MODE: FULL UPGRADE (chậm ~60-120s, có 502) ======'
    bash _deploy_upgrade.sh
elif [ "$HAS_DATA_XML" -eq 1 ]; then
    echo '====== MODE: NOSTOP UPGRADE (~20-40s, no downtime) ======'
    bash _deploy_upgrade_nostop.sh
elif [ "$HAS_ASSET_ONLY" -eq 1 ]; then
    echo '====== MODE: FAST ASSET-ONLY (~2s, no downtime) ======'
    bash _deploy_fast.sh
else
    echo '====== KHÔNG có file nào cần deploy — skip ======'
fi
