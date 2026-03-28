# Verification rapide AVANT ou APRES copie OneDrive / changement de PC.
# Usage (PowerShell, racine du repo) : .\scripts\verify_migration_bundle.ps1
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== verify_migration_bundle (racine: $RepoRoot) ===" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Host "STOP: pas de depot Git ici. Ouvrez PowerShell a la racine decision-memory-v1." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "STOP: .env absent. Copiez-le (OneDrive / sauvegarde) — il n'est pas dans Git." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "data\annotations")) {
    Write-Host "STOP: dossier data\annotations absent (emplacement attendu pour exports M12 locaux)." -ForegroundColor Red
    exit 1
}

$jsonl = @(Get-ChildItem "data\annotations" -Filter "*.jsonl" -File -ErrorAction SilentlyContinue)
if ($jsonl.Count -eq 0) {
    Write-Host "AVERTISSEMENT: aucun .jsonl dans data\annotations. OK si vous rechargez depuis R2 (voir docs/m12/M12_EXPORT.md)." -ForegroundColor Yellow
}

$alembicExe = Join-Path $RepoRoot ".venv\Scripts\alembic.exe"
if (Test-Path $alembicExe) {
    $headsOut = & $alembicExe heads 2>&1 | Out-String
    $lines = @($headsOut -split "`r?`n" | Where-Object { $_.Trim() -ne "" })
    if ($lines.Count -ne 1) {
        Write-Host "STOP: alembic heads doit afficher exactement une ligne (heads multiples ou erreur). Sortie :" -ForegroundColor Red
        Write-Host $headsOut
        exit 1
    }
    Write-Host "OK: un seul head Alembic." -ForegroundColor Green
}
else {
    Write-Host "INFO: .venv absent ou alembic.exe introuvable — saut de la verification alembic heads (normal avant premier bootstrap)." -ForegroundColor Yellow
}

Write-Host "OK: bundle minimal (.env + data/annotations + depot Git) coherent." -ForegroundColor Green
exit 0
