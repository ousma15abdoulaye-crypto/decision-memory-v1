@echo off
REM Export LS + inventaire + verdict — SANS PowerShell (.ps1). Python uniquement.
REM Définir AVANT les variables (ex. dans PowerShell : $env:... puis lancer ce .cmd) :
REM   LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY, PSEUDONYM_SALT, ALLOW_WEAK_PSEUDONYMIZATION=1
REM Usage : scripts\export_ls_smoke.cmd 2
REM Option TLS (certificat / proxy) : set LABEL_STUDIO_SSL_VERIFY=0

setlocal
cd /d "%~dp0.."

if "%~1"=="" (
  echo Usage: scripts\export_ls_smoke.cmd PROJECT_ID
  echo Exemple: scripts\export_ls_smoke.cmd 2
  exit /b 1
)

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%~dp0ls_local_autosave.py" --project-id %~1 --output "data\annotations\ls_smoke_export.jsonl" --overwrite --write-raw-ls-json --only-finished
if errorlevel 1 exit /b 1

"%PY%" "%~dp0inventory_m12_corpus_jsonl.py" "data\annotations\ls_smoke_export.jsonl" --manifest-tsv "data\annotations\ls_smoke_export.manifest.tsv"
if errorlevel 1 exit /b 1

"%PY%" "%~dp0verify_m12_jsonl_corpus.py" "data\annotations\ls_smoke_export.jsonl"
exit /b %ERRORLEVEL%
