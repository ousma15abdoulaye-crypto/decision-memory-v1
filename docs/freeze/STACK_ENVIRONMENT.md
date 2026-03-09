# STACK_ENVIRONMENT
# Généré par PROBE-ÉTAT-SYSTÈME-COMPLET (MANDAT MRD-0)
# Date UTC : 2026-03-09T07:18:49Z
# Ne pas modifier manuellement — regénérer via le mandat probe

## Environnement local

os                  : Windows-10-10.0.22000-SP0 (64bit, WindowsPE)
python_version      : Python 3.11.0
python_path         : C:\Users\abdoulaye.ousmane\AppData\Local\Programs\Python\Python311
virtual_env         : ABSENT (pas de venv actif — installation système directe)
conda_env           : ABSENT
shell               : PowerShell (win32)

## Variables d'environnement shell

DATABASE_URL_SHELL  : ABSENTE (non exportée dans le shell)
DATABASE_URL_ENV    : DÉFINIE dans .env (LOCAL — postgresql+psycopg://dms:dms123@localhost:5432/dms)
DATABASE_URL_TYPE   : LOCAL
RAILWAY_DATABASE_URL: DÉFINIE dans .env (postgresql://postgres:...@maglev.proxy.rlwy.net:35451/railway)
REDIS_URL           : ABSENTE
ENV                 : ABSENTE
ANTHROPIC_API_KEY   : ABSENTE
RAILWAY_CLI         : ABSENT

## Packages critiques (installés dans Python 3.11.0 système)

psycopg             : 3.2.5
psycopg2            : NON INSTALLÉ
sqlalchemy          : 2.0.25
alembic             : 1.13.1
fastapi             : 0.115.0
uvicorn             : 0.30.0
pydantic            : 2.9.0
httpx               : 0.27.0
redis               : 5.2.1
pytest              : 9.0.2
pytest-asyncio      : NON INSTALLÉ
anthropic           : NON INSTALLÉ
openai              : NON INSTALLÉ

## PostgreSQL local

postgresql_version  : PostgreSQL 15.16, compiled by Visual C++ build 1944, 64-bit
host                : localhost
port                : 5432
database            : dms
user                : dms
connexion           : ACCESSIBLE

## PostgreSQL Railway

postgresql_version  : PostgreSQL 17.7 (Debian 17.7-3.pgdg13+1) x86_64 gcc 14.2.0
host                : maglev.proxy.rlwy.net
port                : 35451
database            : railway
railway_cli_version : ABSENT
connexion_status    : ACCESSIBLE (via RAILWAY_DATABASE_URL direct)

## Git

git_version         : git version 2.53.0.windows.1
remote_origin       : https://github.com/ousma15abdoulaye-crypto/decision-memory-v1
branch_courante     : main
last_commit         : 0f37c23 chore: probe etat systeme + fondation MRD [PROBE-MRD0]
last_tag            : framework-v1-done

## CI/CD

workflows           : 7 fichiers dans .github/workflows/
  ci-main.yml, ci-invariants.yml, ci-milestones-gates.yml,
  ci-freeze-integrity.yml, ci-lint-ruff.yml,
  ci-format-black.yml, ci-regenerate-freeze-checksums.yml

## Règle d'usage

DATABASE_URL locale  = développement et tests uniquement
                       URL format : postgresql+psycopg://... (SQLAlchemy)
                       URL conn   : postgresql://...         (psycopg3 direct)
DATABASE_URL Railway = lecture prod via RAILWAY_DATABASE_URL direct
                     = ou railway run ... si CLI installé
Migrations Railway   = railway run alembic upgrade head
                       UNIQUEMENT après GO CTO explicite dans mandat
psql CLI             : ABSENT — utiliser psycopg3 Python pour les probes
node / npm           : ABSENT — Railway CLI non installable sans node
