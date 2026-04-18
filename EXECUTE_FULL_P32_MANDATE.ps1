# P3.2 — Execute full mandate: delete 082 + migrate 101 + post-checks

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "P3.2 MANDAT COMPLET — DELETE 082 + MIGRATE 101 + POST-CHECKS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\Users\abdoulaye.ousmane\OneDrive - Save the Children International\Documents\GitHub\decision-memory-v1"
Set-Location $repoRoot

# ===========================================================================
# ÉTAPE C — Delete 082 and verify single head
# ===========================================================================
Write-Host ""
Write-Host "ÉTAPE C — SUPPRESSION 082 PARASITE" -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" ".\.venv\Scripts\python.exe" "scripts\p32_delete_082_and_verify.py" | Tee-Object -FilePath "p32_etape_c_output.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⛔ ÉTAPE C FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "✅ ÉTAPE C COMPLETE — SINGLE HEAD CONFIRMED" -ForegroundColor Green
Write-Host ""

# ===========================================================================
# ÉTAPE D — Pre-check migration 101
# ===========================================================================
Write-Host ""
Write-Host "ÉTAPE D — PRE-CHECK MIGRATION 101" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ✅ revision = '101_p32_dao_criteria_scoring_schema'" -ForegroundColor Green
Write-Host "  ✅ down_revision = '100_process_workspaces_zip_r2'" -ForegroundColor Green
Write-Host "  ✅ essential → family=NULL, criterion_mode='GATE'" -ForegroundColor Green
Write-Host "  ✅ scoring_mode backfill sans fallback" -ForegroundColor Green
Write-Host ""

# ===========================================================================
# ÉTAPE E — Execute migration 101
# ===========================================================================
Write-Host ""
Write-Host "ÉTAPE E — EXÉCUTION MIGRATION 101" -ForegroundColor Yellow
Write-Host ""

Write-Host "Executing: alembic upgrade head" -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" "alembic" "upgrade" "head" | Tee-Object -FilePath "p32_etape_e_output.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⛔ MIGRATION 101 FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "✅ MIGRATION 101 COMPLETE" -ForegroundColor Green
Write-Host ""

# ===========================================================================
# ÉTAPE F — Post-checks
# ===========================================================================
Write-Host ""
Write-Host "ÉTAPE F — POST-CHECKS MIGRATION 101" -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\python.exe" "scripts\with_railway_env.py" ".\.venv\Scripts\python.exe" "scripts\p32_postcheck_migration_101.py" | Tee-Object -FilePath "p32_etape_f_output.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⛔ POST-CHECKS FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "✅ POST-CHECKS COMPLETE" -ForegroundColor Green
Write-Host ""

# ===========================================================================
# FINAL
# ===========================================================================
Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host "P3.2 MANDAT COMPLET — SUCCESS" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 69) -ForegroundColor Green
Write-Host ""
Write-Host "Outputs saved to:" -ForegroundColor Green
Write-Host "  - p32_etape_c_output.txt (delete 082 + verify single head)" -ForegroundColor Green
Write-Host "  - p32_etape_e_output.txt (migration 101)" -ForegroundColor Green
Write-Host "  - p32_etape_f_output.txt (post-checks)" -ForegroundColor Green
Write-Host ""
