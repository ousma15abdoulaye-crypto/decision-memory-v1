# Charge les variables depuis .env.railway.local à la racine du dépôt (gitignored).
# Usage (PowerShell, depuis n'importe quel répertoire) :
#   . .\scripts\load_railway_env.ps1
# Puis : python scripts/diagnose_railway_migrations.py
# Si « exécution de scripts désactivée » : voir docs/ops/RAILWAY_LOCAL_ENV.md
#   ou : python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repoRoot = Split-Path -Parent $here
$envFile = Join-Path $repoRoot ".env.railway.local"

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "Fichier absent : $envFile`nCopier .env.railway.local.example vers .env.railway.local et remplir les secrets."
    exit 1
}

$loaded = 0
Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -match "^\s*#" -or $line -eq "") {
        return
    }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) {
        return
    }
    $name = $line.Substring(0, $eq).Trim()
    $value = $line.Substring($eq + 1).Trim()
    if ($value.Length -ge 2 -and $value.StartsWith([char]34) -and $value.EndsWith([char]34)) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($value.Length -ge 2 -and $value.StartsWith("'") -and $value.EndsWith("'")) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($name -ne "") {
        Set-Item -Path "Env:$name" -Value $value
        $loaded++
    }
}

Write-Host "Chargé $loaded variable(s) depuis .env.railway.local (ne pas committer ce fichier)."
