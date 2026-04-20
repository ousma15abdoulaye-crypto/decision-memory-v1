# P3.2 R2 — Execute F2 probes via with_railway_env
# CTO: exécuter ce script PowerShell

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 ACTION R2 — F2 NULL PROBES EXECUTION" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\Users\abdoulaye.ousmane\OneDrive - Save the Children International\Documents\GitHub\decision-memory-v1"
Set-Location $repoRoot

Write-Host "Executing: .\.venv\Scripts\python.exe scripts\with_railway_env.py .\.venv\Scripts\python.exe scripts\p32_r2_execute_all_f2_probes.py" -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" ".\.venv\Scripts\python.exe" "scripts\p32_r2_execute_all_f2_probes.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: F2 probes failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host "F2 PROBES EXECUTION COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
