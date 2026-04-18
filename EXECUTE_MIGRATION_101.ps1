# P3.2 — Execute migration 101 with Railway env
# GO CTO authorized 2026-04-18

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 MIGRATION 101 — EXECUTION AUTORISÉE CTO" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\Users\abdoulaye.ousmane\OneDrive - Save the Children International\Documents\GitHub\decision-memory-v1"
Set-Location $repoRoot

Write-Host "PRE-CHECK: Verifying alembic current..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "current"
Write-Host ""

Write-Host "EXECUTING: alembic upgrade head" -ForegroundColor Yellow
Write-Host ""
& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "upgrade" "head"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Migration 101 failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "POST-CHECK: Verifying alembic current..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "current"

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host "MIGRATION 101 EXECUTION COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
