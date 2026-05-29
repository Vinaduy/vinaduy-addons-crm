# Local push helper — chạy: .\push.ps1 "commit message"
# Args:
#   $args[0] = commit message (bắt buộc)
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Message
)

$ErrorActionPreference = 'Stop'

Write-Host "====== ADD ======" -ForegroundColor Cyan
git add -A

Write-Host "====== COMMIT ======" -ForegroundColor Cyan
git commit -m $Message

Write-Host "====== PUSH ======" -ForegroundColor Cyan
git push origin main

Write-Host ""
Write-Host "DONE — chạy trên server:" -ForegroundColor Green
Write-Host "  bash /root/vinaduy-addons-crm/pull.sh" -ForegroundColor Yellow
