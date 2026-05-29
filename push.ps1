# Local push helper: .\push.ps1 "commit message"
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
Write-Host "DONE - chay tren server:" -ForegroundColor Green
Write-Host "  bash /root/vinaduy-addons-crm/pull.sh" -ForegroundColor Yellow
