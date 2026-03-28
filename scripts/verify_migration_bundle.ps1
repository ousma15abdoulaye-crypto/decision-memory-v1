# Verifie que le dossier decision-memory-v1 contient tout le necessaire avant copie / migration.
# Usage (racine du repo) : .\scripts\verify_migration_bundle.ps1

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Ok([string]$msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Info([string]$msg) { Write-Host "     $msg" -ForegroundColor DarkGray }

Write-Host "`n=== Verification bundle migration DMS ===" -ForegroundColor Cyan
Write-Host "Racine : $root`n"

$required = @(
    @{ Path = "README.md"; Desc = "README racine" },
    @{ Path = "docker-compose.yml"; Desc = "Postgres/Redis/API Docker" },
    @{ Path = "Dockerfile"; Desc = "Image API" },
    @{ Path = "requirements.txt"; Desc = "Deps Python app" },
    @{ Path = "services/annotation-backend/requirements.txt"; Desc = "Deps annotation-backend" },
    @{ Path = "alembic.ini"; Desc = "Alembic" },
    @{ Path = "main.py"; Desc = "Point entree API" },
    @{ Path = "start.sh"; Desc = "Demarrage prod / Docker" },
    @{ Path = "pyproject.toml"; Desc = "Config outils Python" },
    @{ Path = ".env.example"; Desc = "Modele variables (sans secrets)" },
    @{ Path = "docs/dev/LAPTOP_MIGRATION.md"; Desc = "Guide migration PC" },
    @{ Path = "LISEZMOI_NOUVEAU_PC.txt"; Desc = "Instructions minimales nouveau PC" },
    @{ Path = "PREMIER_DEMARRAGE.bat"; Desc = "Double-clic premier demarrage" },
    @{ Path = "scripts/premier_demarrage.ps1"; Desc = "Script installe venv + deps + docker + alembic" },
    @{ Path = "scripts/verify_laptop_setup.ps1"; Desc = "Verif post-install nouveau PC" },
    @{ Path = "scripts/verify_migration_bundle.ps1"; Desc = "Ce script (checklist copie)" }
)

$missingRequired = @()
foreach ($item in $required) {
    $p = Join-Path $root $item.Path
    if (Test-Path $p) {
        Ok $item.Desc
        Info $item.Path
    } else {
        Warn "MANQUANT critique : $($item.Desc) -> $($item.Path)"
        $missingRequired += $item.Path
    }
}

$alembicVersions = Join-Path $root "alembic/versions"
if (Test-Path $alembicVersions) {
    $revs = @(Get-ChildItem -Path $alembicVersions -Filter "*.py" -ErrorAction SilentlyContinue)
    if ($revs.Count -gt 0) {
        Ok "Migrations Alembic : $($revs.Count) fichiers dans alembic/versions"
    } else {
        Warn "alembic/versions semble vide"
    }
} else {
    Warn "Dossier alembic/versions introuvable"
}

Write-Host "`n--- Secrets et donnees (souvent hors Git) ---" -ForegroundColor Cyan

$copyIfExists = @(
    @{ Path = ".env"; Desc = "Secrets + DATABASE_URL - A COPIER sur cle USB" },
    @{ Path = ".env.local"; Desc = "Override local optionnel" },
    @{ Path = "data/annotations/.ls_export_env"; Desc = "URL et cle Label Studio export" },
    @{ Path = "data/annotations/.r2_export_env"; Desc = "S3/R2 export corpus (Cloudflare)" },
    @{ Path = "data/annotations/m12_corpus_from_ls.jsonl"; Desc = "Dernier export corpus M12 (JSONL = N lignes, un fichier)" },
    @{ Path = "data/regulatory/MISTRAL_KEY.txt"; Desc = "Cle Mistral import reglementaire" }
)

foreach ($item in $copyIfExists) {
    $p = Join-Path $root $item.Path
    if (Test-Path $p) {
        Ok "Present : $($item.Desc)"
        Info $item.Path
    } else {
        Warn "Absent (normal si non utilise) : $($item.Desc)"
        Info $item.Path
    }
}

$annDir = Join-Path $root "data/annotations"
if (Test-Path $annDir) {
    $jsonl = @(Get-ChildItem -Path $annDir -Filter "m12_corpus*.jsonl" -ErrorAction SilentlyContinue)
    if ($jsonl.Count -gt 0) {
        Write-Host "`nExports m12_corpus*.jsonl :" -ForegroundColor DarkGray
        foreach ($f in $jsonl) { Info $f.FullName }
    }
}

Write-Host "`n--- Environnement local ---" -ForegroundColor Cyan
if (Test-Path "$root\.venv\Scripts\python.exe") {
    Info ".venv present : tu peux EXCLURE de la copie USB (recree sur le nouveau PC)"
} else {
    Info "Pas de .venv : a creer sur le nouveau PC apres copie"
}

Push-Location $root
& git rev-parse --git-dir 1>$null 2>$null
if ($LASTEXITCODE -eq 0) {
    $branch = git branch --show-current 2>$null
    Ok "Depot Git (branche : $branch)"
    $stLines = @(git status --short 2>$null)
    if ($stLines.Count -gt 0) {
        Warn "Working tree non vide - verifier fichiers non commites"
        $max = [Math]::Min(15, $stLines.Count)
        for ($i = 0; $i -lt $max; $i++) { Info $stLines[$i] }
    }
} else {
    Info "Pas de depot Git detecte (OK si copie fichier seule)"
}
Pop-Location

Write-Host "`n--- Resume ---" -ForegroundColor Cyan
if ($missingRequired.Count -eq 0) {
    Ok "Structure repo : fichiers critiques presents."
} else {
    Warn "Manquants critiques : $($missingRequired.Count) - copie ou clone incomplet"
}
Write-Host "`nRappel : copier TOUT le dossier pour garder .env et data ignores par Git."
Write-Host "Suite : docs/dev/LAPTOP_MIGRATION.md`n"
