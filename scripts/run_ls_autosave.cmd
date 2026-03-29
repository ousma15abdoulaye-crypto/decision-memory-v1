@echo off
REM Contourne « l'exécution de scripts est désactivée » (PSSecurityException sur les .ps1).
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_ls_autosave.ps1" %*
