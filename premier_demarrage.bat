@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ========================================
echo  DMS - Premier demarrage (Windows)
echo ========================================
echo.

REM Python 3.11.x aligne runtime.txt / CI — evite une install 3.12 cassee en tete de PATH
set "PYEXE="
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PYEXE py -3.11 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.11"
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
  echo [ERREUR] Python 3.11 introuvable. Installez Python 3.11.9+ ^(voir runtime.txt^) ou ajoutez-le au PATH.
  exit /b 1
)
echo [INFO] Interprete: %PYEXE%

where docker >nul 2>&1
if not errorlevel 1 (
  echo [INFO] Demarrage PostgreSQL via docker compose...
  docker compose up -d
  if errorlevel 1 (
    echo [AVERTISSEMENT] docker compose a echoue. Verifiez PostgreSQL et DATABASE_URL dans .env
  ) else (
    echo [INFO] Attente courte pour Postgres...
    timeout /t 6 /nobreak >nul
  )
) else (
  echo [INFO] Docker absent: demarrez PostgreSQL vous-meme et renseignez DATABASE_URL dans .env
)

if not exist ".env" (
  echo [INFO] Creation .env ^(PostgreSQL Docker: dms/dms@localhost:5432/dms^)
  (
    echo # Genere par premier_demarrage.bat — ajuster si besoin
    echo DATABASE_URL=postgresql+psycopg://dms:dms@localhost:5432/dms
    echo JWT_SECRET=dev-local-change-me
    echo ENV=dev
  ) > .env
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creation de .venv avec %PYEXE%...
  %PYEXE% -m venv .venv
  if errorlevel 1 exit /b 1
)

call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERREUR] Impossible d activer .venv
  exit /b 1
)

echo [INFO] pip install -r requirements.txt
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [INFO] alembic upgrade head
alembic upgrade head
if errorlevel 1 (
  echo [ERREUR] Migrations echouees. Verifiez DATABASE_URL et que Postgres ecoute.
  exit /b 1
)

echo.
echo [OK] API: http://127.0.0.1:8000  (Ctrl+C pour arreter)
echo.
uvicorn main:app --reload --host 127.0.0.1 --port 8000

endlocal
