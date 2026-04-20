# P3.2 — Execute post-checks migration 101

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 POST-CHECK MIGRATION 101" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\Users\abdoulaye.ousmane\OneDrive - Save the Children International\Documents\GitHub\decision-memory-v1"
Set-Location $repoRoot

Write-Host "Executing post-checks..." -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" ".\.venv\Scripts\python.exe" "scripts\p32_postcheck_migration_101.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Post-check failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host "POST-CHECK COMPLETE — ALL CHECKS PASS" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
