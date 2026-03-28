# Premier demarrage sur un PC neuf apres copie du dossier decision-memory-v1.
# Lance depuis PREMIER_DEMARRAGE.bat a la racine du repo.

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host ""
Write-Host "=== DMS — premier demarrage ===" -ForegroundColor Cyan
Write-Host "Dossier : $root" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path "$root\.env")) {
    Write-Host "[ERREUR] Fichier .env introuvable." -ForegroundColor Red
    Write-Host "Il doit etre dans ce dossier (copie depuis l ancien PC)." -ForegroundColor Yellow
    Write-Host "Sans .env, la base de donnees ne peut pas se connecter." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Fichier .env present" -ForegroundColor Green

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[ERREUR] Python introuvable. Installez Python 3.11+ et cochez Add to PATH." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    Write-Host "[...] Creation de .venv ..." -ForegroundColor Gray
    & python -m venv "$root\.venv"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[OK] .venv deja present — mise a jour des paquets" -ForegroundColor Green
}

$pip = "$root\.venv\Scripts\python.exe"
& $pip -m pip install --upgrade pip -q
Write-Host "[...] Installation des paquets (plusieurs minutes) ..." -ForegroundColor Gray
& $pip -m pip install -r "$root\requirements.txt"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pip -m pip install -r "$root\services\annotation-backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "[OK] Paquets Python installes" -ForegroundColor Green

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    Write-Host "[...] Demarrage PostgreSQL (Docker) ..." -ForegroundColor Gray
    Push-Location $root
    try {
        docker compose up -d postgres 2>&1 | Out-Host
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Conteneur postgres demarre (port 5432)" -ForegroundColor Green
            Write-Host "     Attente 5 s pour que Postgres soit pret ..." -ForegroundColor Gray
            Start-Sleep -Seconds 5
        } else {
            Write-Host "[--] docker compose a echoue — demarrez Postgres a la main : docker compose up -d postgres" -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[--] Docker non installe — installez Docker Desktop ou configurez PostgreSQL vous-meme." -ForegroundColor Yellow
    Write-Host "     Verifiez que DATABASE_URL dans .env pointe vers votre Postgres." -ForegroundColor Yellow
}

Write-Host "[...] Migrations base de donnees (alembic) ..." -ForegroundColor Gray
Push-Location $root
try {
    $alembic = "$root\.venv\Scripts\alembic.exe"
    if (-not (Test-Path $alembic)) {
        Write-Host "[ERREUR] alembic.exe introuvable dans .venv" -ForegroundColor Red
        exit 1
    }
    & $alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[--] alembic a echoue — verifiez Docker/Postgres et DATABASE_URL dans .env" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
    Write-Host "[OK] Migrations appliquees" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Termine ===" -ForegroundColor Green
Write-Host "Ouvrez ce dossier dans Cursor. Pour verifier : .\\scripts\\verify_laptop_setup.ps1" -ForegroundColor Gray
Write-Host ""
