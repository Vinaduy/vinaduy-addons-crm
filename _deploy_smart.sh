#!/bin/bash
# SMART deploy — pick mode dựa trên git diff HEAD~1 HEAD.
#   - Chỉ asset (static/src/**)                     → _deploy_fast.sh         (~2s,    no downtime)
#   - Chỉ views/reports XML (+optional asset)       → _deploy_views_only.sh   (~3-8s,  no downtime)
#   - Asset + data/__manifest__/security XML        → _deploy_upgrade_nostop  (~20-40s, no downtime)
#   - Có Python (models/, wizard/) hoặc security    → _deploy_upgrade.sh      (~60-120s, có 502)
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
HAS_HEAVY_XML=0   # __manifest__, data/, security/, csv → cần -u
HAS_VIEWS_XML=0   # views/, reports/ → load nhanh không cần -u
HAS_ASSET=0       # static/src/ → chỉ cần xoá web.assets_%

while IFS= read -r f; do
    case "$f" in
        */static/src/*)
            HAS_ASSET=1 ;;
        */models/*|*/wizard/*|*/controllers/*|*/__init__*)
            NEEDS_FULL_UPGRADE=1
            echo "  → '$f' yêu cầu FULL UPGRADE (Python)" ;;
        *.py)
            NEEDS_FULL_UPGRADE=1
            echo "  → '$f' yêu cầu FULL UPGRADE (Python)" ;;
        */views/*.xml|*/reports/*.xml)
            HAS_VIEWS_XML=1 ;;
        */security/*|*/__manifest__.py|*/data/*|*.csv)
            HAS_HEAVY_XML=1
            echo "  → '$f' yêu cầu NOSTOP UPGRADE (manifest/data/security)" ;;
        *.xml)
            HAS_HEAVY_XML=1 ;;
        _deploy_*.sh|push.ps1|pull.sh|*.md|.git*)
            echo "  → '$f' bỏ qua (script/docs)" ;;
        *)
            HAS_HEAVY_XML=1 ;;
    esac
done <<< "$CHANGED_FILES"

if [ "$NEEDS_FULL_UPGRADE" -eq 1 ]; then
    echo '====== MODE: FULL UPGRADE (chậm ~60-120s, có 502) ======'
    bash _deploy_upgrade.sh
elif [ "$HAS_HEAVY_XML" -eq 1 ]; then
    echo '====== MODE: NOSTOP UPGRADE (~20-40s, no downtime) ======'
    bash _deploy_upgrade_nostop.sh
elif [ "$HAS_VIEWS_XML" -eq 1 ]; then
    echo '====== MODE: VIEWS-ONLY HOT RELOAD (~3-8s, no downtime) ======'
    bash _deploy_views_only.sh
elif [ "$HAS_ASSET" -eq 1 ]; then
    echo '====== MODE: FAST ASSET-ONLY (~2s, no downtime) ======'
    bash _deploy_fast.sh
else
    echo '====== KHÔNG có file nào cần deploy — skip ======'
fi
