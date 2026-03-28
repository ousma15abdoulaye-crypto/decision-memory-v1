#Requires -Version 5.1
<#
.SYNOPSIS
  Lance ls_local_autosave.py sans se tromper de guillemets PowerShell.

.DESCRIPTION
  Définir AVANT dans la MÊME fenêtre PowerShell (une ligne = une variable, SANS copier ce bloc avec >>) :

    $env:LABEL_STUDIO_URL = "https://label-studio-production-1f72.up.railway.app"
    $env:LABEL_STUDIO_API_KEY = "<Access Token depuis LS : Account & Settings>"
    $env:PSEUDONYM_SALT = "local-dev-salt"
    $env:ALLOW_WEAK_PSEUDONYMIZATION = "1"

  Puis :
    .\scripts\run_ls_autosave.ps1 -ProjectId 1 -VerifyOnly
    .\scripts\run_ls_autosave.ps1 -ProjectId 1
    .\scripts\run_ls_autosave.ps1 -ProjectId 1 -MirrorRaw
    .\scripts\run_ls_autosave.ps1 -ProjectId 1 -Loop -Interval 300

  -MirrorRaw : écrit aussi data/annotations/ls_raw_project_<id>.json (export API LS brut).
  -EnforceValidatedQa : active la QA stricte sur annotated_validated (export_ok plus sévère).
#>
param(
    [Parameter(Mandatory = $true)]
    [int] $ProjectId,
    [string] $Output = "data/annotations/ls_autosave.jsonl",
    [switch] $VerifyOnly,
    [switch] $Loop,
    [int] $Interval = 300,
    [switch] $MirrorRaw,
    [switch] $EnforceValidatedQa
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "python"
}

$pyArgs = @(
    (Join-Path $Root "scripts\ls_local_autosave.py"),
    "--project-id", "$ProjectId",
    "--output", (Join-Path $Root $Output)
)
if ($VerifyOnly) {
    $pyArgs += "--verify-only"
}
if ($Loop) {
    $pyArgs += @("--loop", "--interval", "$Interval")
}
if ($MirrorRaw) {
    $pyArgs += "--write-raw-ls-json"
}
if ($EnforceValidatedQa) {
    $pyArgs += "--enforce-validated-qa"
}

& $Py @pyArgs
