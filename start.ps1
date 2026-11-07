Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting Placement Intelligence Hub..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

$Env:PYTHONPATH = $PSScriptRoot

python run.py
