# Verification APRES bootstrap sur le nouveau PC (venv + migrations).
# Usage : .\scripts\verify_laptop_setup.ps1
# Optionnel : $env:DMS_EXPECT_GIT_BRANCH = "main" ou "chore/..." pour exiger une branche.
$ErrorActionPreference = "Continue"
$failed = $false

function Fail([string]$msg) {
    Write-Host "STOP: $msg" -ForegroundColor Red
    $script:failed = $true
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== verify_laptop_setup (racine: $RepoRoot) ===" -ForegroundColor Cyan

docker info 2>&1 | Out-Null
if (-not $?) {
    Fail "Docker Desktop non demarre ou CLI docker inaccessible. Ouvrez Docker Desktop et attendez le moteur pret."
}

if (-not (Test-Path ".env")) { Fail "Fichier .env absent a la racine du repo." }

$py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Fail "Environnement .venv absent ou casse. Supprimez .venv puis relancez premier_demarrage.bat a la racine du repo."
}

$alembicExe = Join-Path $RepoRoot ".venv\Scripts\alembic.exe"
if (-not (Test-Path $alembicExe)) {
    Fail "alembic.exe introuvable dans .venv — pip / venv incomplet."
}
else {
    $headsOut = & $alembicExe heads 2>&1 | Out-String
    $lines = @($headsOut -split "`r?`n" | Where-Object { $_.Trim() -ne "" })
    if ($lines.Count -ne 1) {
        Fail "alembic heads doit retourner exactement un head. Sortie :`n$headsOut"
    }
}

$branch = (git branch --show-current 2>&1 | Out-String).Trim()
Write-Host "Branche courante : $branch" -ForegroundColor Gray
$expect = $env:DMS_EXPECT_GIT_BRANCH
if ($expect -and $branch -ne $expect) {
    Fail "Branche Git inattendue (actuelle: '$branch', attendue: '$expect'). Ajustez ou videz DMS_EXPECT_GIT_BRANCH."
}

$remotes = (git remote -v 2>&1 | Out-String).Trim()
if (-not $remotes) {
    Write-Host "AVERTISSEMENT: aucun remote Git configure." -ForegroundColor Yellow
}

if ($failed) {
    Write-Host "verify_laptop_setup : ECHEC" -ForegroundColor Red
    exit 1
}

Write-Host "OK: verify_laptop_setup (Docker actif, .env, .venv, un head Alembic)." -ForegroundColor Green
exit 0
