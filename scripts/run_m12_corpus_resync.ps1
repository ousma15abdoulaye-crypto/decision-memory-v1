#Requires -Version 5.1
<#
.SYNOPSIS
  Chaine M12 en une passe : inventaire local, export API Label Studio, delta R2, consolidation (R2 gagne).

.DESCRIPTION
  1) Inventaire de data/annotations/m12_corpus_authoritative.jsonl (verite R2) si present.
  2) Export LS complet -> data/annotations/m12_corpus_from_ls.jsonl (ne remplace pas authoritative).
  3) Delta R2 vs authoritative -> m12_r2_only_missing.jsonl (sans filtre export_ok : dump R2 peut avoir export_ok=false).
  4) Fusion : authoritative + delta + overlay R2 -> m12_consolidated.jsonl

  Variables (process) : charger via .env / .env.local et/ou :
    data/annotations/.ls_export_env   : LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY (ou LS_*), LABEL_STUDIO_PROJECT_ID
    data/annotations/.r2_export_env   : S3_BUCKET, S3_ENDPOINT, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY

.EXAMPLE
  cd decision-memory-v1
  .\scripts\run_m12_corpus_resync.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Import-DotEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim()
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        Set-Item -Path "env:$k" -Value $v
    }
}

Import-DotEnvFile (Join-Path $Root ".env")
Import-DotEnvFile (Join-Path $Root ".env.local")
Import-DotEnvFile (Join-Path $Root "data\annotations\.ls_export_env")
Import-DotEnvFile (Join-Path $Root "data\annotations\.r2_export_env")

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = $null }

function Invoke-DmsPython {
    param([string[]]$Arguments)
    if ($Py) {
        & $Py @Arguments
    } else {
        & py -3.11 @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "python exit $LASTEXITCODE : $($Arguments -join ' ')" }
}

$AuthoritativeJsonl = Join-Path $Root "data\annotations\m12_corpus_authoritative.jsonl"
$LsExportJsonl = Join-Path $Root "data\annotations\m12_corpus_from_ls.jsonl"
$DeltaJsonl = Join-Path $Root "data\annotations\m12_r2_only_missing.jsonl"
$OutJsonl = Join-Path $Root "data\annotations\m12_consolidated.jsonl"
$Manifest = Join-Path $Root "data\annotations\m12_consolidate_manifest.json"

Write-Host "=== [1/4] Inventaire (corpus authoritative R2) ===" -ForegroundColor Cyan
if (Test-Path $AuthoritativeJsonl) {
    Invoke-DmsPython @((Join-Path $Root "scripts\inventory_m12_corpus_jsonl.py"), $AuthoritativeJsonl)
} else {
    Write-Host "Aucun data/annotations/m12_corpus_authoritative.jsonl - exporter depuis R2 dabord." -ForegroundColor Yellow
}

Write-Host "=== [2/4] Export Label Studio -> m12_corpus_from_ls.jsonl ===" -ForegroundColor Cyan
$lsUrl = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_URL", "Process")
if (-not $lsUrl) { $lsUrl = [Environment]::GetEnvironmentVariable("LS_URL", "Process") }
$lsKey = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_API_KEY", "Process")
if (-not $lsKey) { $lsKey = [Environment]::GetEnvironmentVariable("LS_API_KEY", "Process") }
$proj = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_PROJECT_ID", "Process")
if (-not $proj) { $proj = "1" }

if (-not $lsUrl -or -not $lsKey) {
    Write-Host "STOP - LABEL_STUDIO_URL + LABEL_STUDIO_API_KEY (ou LS_URL + LS_API_KEY) requis." -ForegroundColor Red
    Write-Host "      Creez data/annotations/.ls_export_env ou completez .env.local (voir docs/m12/M12_EXPORT.md)." -ForegroundColor Red
    exit 1
}

Invoke-DmsPython @(
    (Join-Path $Root "scripts\export_ls_to_dms_jsonl.py"),
    "--project-id", $proj,
    "--output", $LsExportJsonl
)

Write-Host "=== [3/4] Delta R2 (objets absents du JSONL local) ===" -ForegroundColor Cyan
$bucket = [Environment]::GetEnvironmentVariable("S3_BUCKET", "Process")
if (-not $bucket) {
    Write-Host "STOP - S3_BUCKET absent : impossible de lire R2. Creez data/annotations/.r2_export_env." -ForegroundColor Red
    exit 1
}

Invoke-DmsPython @(
    (Join-Path $Root "scripts\m12_r2_delta_vs_local.py"),
    "--local-jsonl", $AuthoritativeJsonl,
    "--output", $DeltaJsonl
)

Write-Host "=== [4/4] Consolidation (R2 gagne sur les doublons) ===" -ForegroundColor Cyan
Invoke-DmsPython @(
    (Join-Path $Root "scripts\consolidate_m12_corpus.py"),
    "-i", $AuthoritativeJsonl,
    "-i", $DeltaJsonl,
    "--from-r2",
    "--r2-accepted-statuses", "annotated_validated,annotated,validated,review_required",
    "-o", $OutJsonl,
    "--only-m12-v2",
    "--manifest", $Manifest
)

Write-Host "=== Inventaire final (LS export + delta + consolide) ===" -ForegroundColor Cyan
Invoke-DmsPython @((Join-Path $Root "scripts\inventory_m12_corpus_jsonl.py"), $LsExportJsonl, $DeltaJsonl, $OutJsonl)

Write-Host "Termine. Fichier canonique : $OutJsonl" -ForegroundColor Green
