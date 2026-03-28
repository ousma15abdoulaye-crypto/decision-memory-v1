# Verifications rapides apres migration de machine (Windows PowerShell).
# Usage (racine du repo) : .\scripts\verify_laptop_setup.ps1

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Ok([string]$msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[--] $msg" -ForegroundColor Yellow }
function Bad([string]$msg) { Write-Host "[!!] $msg" -ForegroundColor Red }

Write-Host "DMS verify_laptop_setup - $root`n"

# Python 3.11+
try {
    $v = (& python --version 2>&1 | Out-String).Trim()
    $ok311 = ($v -like "*3.11*") -or ($v -like "*3.12*") -or ($v -like "*3.13*")
    if ($ok311) {
        Ok "Python : $v"
    } elseif ($v -like "Python 3.*") {
        Warn "Python 3.11+ recommande ; detecte : $v"
    } else {
        Warn "Version Python non lue : $v"
    }
} catch {
    Bad "Python introuvable - installer Python 3.11+"
}

if (Test-Path "$root\.venv\Scripts\python.exe") {
    Ok "Venv present : .venv"
} else {
    Warn "Pas de .venv - python -m venv .venv puis pip install -r requirements.txt"
}

if (Test-Path "$root\.env") {
    Ok "Fichier .env present"
} else {
    Warn "Pas de .env - copier depuis ancien PC ou copier .env.example vers .env"
}

if (Test-Path "$root\docker-compose.yml") {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        Ok "Docker CLI disponible"
        docker compose version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n  docker compose ps :" -ForegroundColor DarkGray
            docker compose ps 2>$null
        }
    } else {
        Warn "Docker non trouve dans le PATH - installer Docker Desktop"
    }
} else {
    Warn "docker-compose.yml absent (racine attendue)"
}

Write-Host "`nReferences : docs/dev/LAPTOP_MIGRATION.md , docs/audits/SETUP_STATUS.md`n"
