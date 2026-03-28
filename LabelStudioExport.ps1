# Un seul script : export Label Studio -> JSONL + inventaire.
# 1) Colle ton token (Personal Access Token de l'UI LS) dans $TOKEN ci-dessous.
# 2) Executer :  .\LabelStudioExport.ps1
# Ne commite pas ce fichier avec un vrai token.

$TOKEN    = ""
$LS_URL   = "https://label-studio-production-1f72.up.railway.app"
$PROJECT  = 1
$OUT      = "data\annotations\m12_corpus_from_ls.jsonl"

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $TOKEN.Trim()) {
    Write-Host "Remplis `$TOKEN en haut de LabelStudioExport.ps1 (token API Label Studio)." -ForegroundColor Red
    exit 1
}

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$env:LABEL_STUDIO_URL = $LS_URL.TrimEnd("/")
$env:LABEL_STUDIO_API_KEY = $TOKEN.Trim()

& $py "scripts\export_ls_to_dms_jsonl.py" --project-id $PROJECT --output $OUT --post-inventory
exit $LASTEXITCODE
