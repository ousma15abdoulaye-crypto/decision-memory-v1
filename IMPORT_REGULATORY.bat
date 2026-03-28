@echo off
cd /d "%~dp0"
rem Reseau d'entreprise / proxy : desactive la verif SSL cote client (sinon erreur certificat)
set MISTRAL_SSL_VERIFY=0
echo Import bibliotheque reglementaire (PDF dans data\regulatory\raw\)...
python scripts\parse_regulatory_docs.py --all --method mistral_ocr
if errorlevel 1 (
  echo.
  echo Echec. Verifie : cle dans data\regulatory\MISTRAL_KEY.txt ou MISTRAL_API_KEY dans .env.local
  pause
  exit /b 1
)
echo Termine. Sorties : data\regulatory\parsed\
pause
