# P3.2 ÉTAPE C — Execute Alembic resolution (delete 082 parasite)

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 ÉTAPE C — RÉSOLUTION ALEMBIC (DELETE 082)" -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel 2>$null).Trim()
if (-not $repoRoot) {
    throw "Unable to determine the repository root from script location: $PSScriptRoot"
}
Set-Location $repoRoot

$file082 = "alembic\versions\082_p32_dao_criteria_scoring_schema.py"

Write-Host "BEFORE: Checking if 082 exists..." -ForegroundColor Yellow
if (Test-Path $file082) {
    Write-Host "  ✅ Found: $file082" -ForegroundColor Green
} else {
    Write-Host "  ⛔ NOT FOUND: $file082 (already deleted?)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "DELETING: $file082" -ForegroundColor Yellow
Remove-Item $file082 -Force

Write-Host "  ✅ Deleted" -ForegroundColor Green
Write-Host ""

Write-Host "POST-CHECK: Verifying alembic heads..." -ForegroundColor Yellow
Write-Host ""
& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "heads"

Write-Host ""
Write-Host "POST-CHECK: Verifying alembic current..." -ForegroundColor Yellow
Write-Host ""
& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "current"

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host "RESOLUTION COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
