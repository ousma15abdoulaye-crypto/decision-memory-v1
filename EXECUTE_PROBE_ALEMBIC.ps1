# P3.2 ÉTAPE A — Execute Alembic heads probe

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 ÉTAPE A — PROBE ALEMBIC HEADS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\Users\abdoulaye.ousmane\OneDrive - Save the Children International\Documents\GitHub\decision-memory-v1"
Set-Location $repoRoot

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" ".\.venv\Scripts\python.exe" "scripts\p32_probe_alembic_heads.py" | Tee-Object -FilePath "p32_alembic_heads_probe_output.txt"

Write-Host ""
Write-Host "Output saved to: p32_alembic_heads_probe_output.txt" -ForegroundColor Green
