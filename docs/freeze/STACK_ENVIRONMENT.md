# STACK_ENVIRONMENT
# Généré par PROBE-ÉTAT-SYSTÈME-COMPLET
# Date UTC : 2026-03-08
# Ne pas modifier manuellement — regénérer via le mandat probe

## Environnement local

os                  : Windows_NT
python_version      : 3.11.0
virtual_env         : (non détecté dans shell — VIRTUAL_ENV vide)

## Variables d'environnement

DATABASE_URL_LOCAL  : DÉFINIE (via .env)
DATABASE_URL_TYPE   : LOCAL (dms@localhost)
REDIS_URL           : ABSENTE
ENV                 : ABSENTE
ANTHROPIC_API_KEY   : ABSENTE
RAILWAY_CLI         : ABSENT
RAILWAY_DATABASE_URL: DÉFINIE (via .env)

## Packages critiques

psycopg             : 3.2.5
alembic             : 1.13.1
sqlalchemy          : 2.0.25
fastapi             : 0.115.0
pytest              : 9.0.2
anthropic           : NON INSTALLÉ
httpx               : 0.27.0

## PostgreSQL local

postgresql_version  : PostgreSQL 15.16, compiled by Visual C++ build 1944, 64-bit
host                : localhost
port                : 5432
database            : dms
alembic_version     : m7_4b

## PostgreSQL Railway

postgresql_version  : ACCESSIBLE (via RAILWAY_DATABASE_URL)
railway_cli_version : ABSENT
connexion_status    : ACCESSIBLE
alembic_version     : m7_4b
dict_items_actifs   : 0
aliases             : 0

## Règle d'usage

DATABASE_URL locale  = développement et tests
DATABASE_URL Railway = lecture prod uniquement depuis railway run
Migrations Railway   = railway run alembic upgrade head
                       uniquement après GO CTO explicite dans mandat
