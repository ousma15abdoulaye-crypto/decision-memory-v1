#Requires -Version 5.1
<#
.SYNOPSIS
  Sauvegarde versionnee du corpus M12 : export R2, export LS (si creds), copie authoritative.

.DESCRIPTION
  Ecrit sous data/annotations/backups/YYYYMMDD_HHMMSS/ :
    - r2_corpus.jsonl          (export R2 --no-status-filter)
    - ls_corpus.jsonl          (si LABEL_STUDIO_URL + cle API + PROJECT_ID)
    - m12_corpus_authoritative_copy.jsonl  (copie du fichier courant si present)

  Charge les memes fichiers .env que run_m12_corpus_resync.ps1 :
    .env, .env.local, data/annotations/.ls_export_env, .r2_export_env,
    data/annotations/annotations/.ls_export_env, .r2_export_env, r2_export.env

.PARAMETER SkipR2
  Ne pas appeler export_r2_corpus_to_jsonl.py

.PARAMETER SkipLs
  Ne pas appeler export_ls_to_dms_jsonl.py

.EXAMPLE
  cd decision-memory-v1
  .\scripts\m12_corpus_backup.ps1
#>
param(
    [switch]$SkipR2,
    [switch]$SkipLs
)

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

foreach ($rel in @(
        ".env",
        ".env.local",
        "data\annotations\.ls_export_env",
        "data\annotations\.r2_export_env",
        "data\annotations\annotations\.ls_export_env",
        "data\annotations\annotations\.r2_export_env",
        "data\annotations\annotations\r2_export.env"
    )) {
    Import-DotEnvFile (Join-Path $Root $rel)
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = $null }

function Invoke-DmsPython {
    param([string[]]$Arguments)
    if ($Py) {
        & $Py @Arguments
    } else {
        & py -3.11 @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "python exit $LASTEXITCODE" }
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = Join-Path $Root "data\annotations\backups\$stamp"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$Summary = Join-Path $BackupDir "BACKUP_SUMMARY.txt"
$lines = @("M12 backup $stamp", "Root: $Root", "")

if (-not $SkipR2) {
    if (-not $env:S3_VERIFY_SSL) {
        # Par défaut, garder la vérification TLS activée pour les appels S3/R2.
        # Ne définir S3_VERIFY_SSL=0 qu'explcitement (proxy / certificat interne).
        $env:S3_VERIFY_SSL = "1"
    }
    $r2Out = Join-Path $BackupDir "r2_corpus.jsonl"
    try {
        Invoke-DmsPython @(
            (Join-Path $Root "scripts\export_r2_corpus_to_jsonl.py"),
            "-o", $r2Out,
            "--no-status-filter"
        )
        $n = (Get-Content $r2Out | Measure-Object -Line).Lines
        $lines += "R2 -> $r2Out ($n lines)"
    } catch {
        $lines += "R2 FAILED: $_"
    }
} else {
    $lines += "R2 skipped (-SkipR2)"
}

$auth = Join-Path $Root "data\annotations\m12_corpus_authoritative.jsonl"
if (Test-Path $auth) {
    $copy = Join-Path $BackupDir "m12_corpus_authoritative_copy.jsonl"
    Copy-Item -LiteralPath $auth -Destination $copy -Force
    $lines += "Copy authoritative -> $copy"
} else {
    $lines += "No authoritative file at $auth"
}

if (-not $SkipLs) {
    $lsUrl = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_URL", "Process")
    if (-not $lsUrl) { $lsUrl = [Environment]::GetEnvironmentVariable("LS_URL", "Process") }
    $lsKey = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_API_KEY", "Process")
    if (-not $lsKey) { $lsKey = [Environment]::GetEnvironmentVariable("LS_API_KEY", "Process") }
    $proj = [Environment]::GetEnvironmentVariable("LABEL_STUDIO_PROJECT_ID", "Process")
    if (-not $proj) { $proj = "1" }

    if ($lsUrl -and $lsKey) {
        $lsOut = Join-Path $BackupDir "ls_corpus.jsonl"
        try {
            Invoke-DmsPython @(
                (Join-Path $Root "scripts\export_ls_to_dms_jsonl.py"),
                "--project-id", $proj,
                "--output", $lsOut
            )
            $n = (Get-Content $lsOut | Measure-Object -Line).Lines
            $lines += "LS project_id=$proj -> $lsOut ($n lines)"
        } catch {
            $lines += "LS export FAILED: $_"
        }
    } else {
        $lines += "LS skipped (LABEL_STUDIO_URL/KEY or LS_* missing)"
    }
} else {
    $lines += "LS skipped (-SkipLs)"
}

$lines | Set-Content -Path $Summary -Encoding UTF8
Write-Host ($lines -join "`n")
Write-Host "`nResume -> $Summary"
