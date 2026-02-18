# Setup Local PostgreSQL — Production Ready

## Étape 1 : Créer la base de données et le rôle

Exécute le script de setup (il demandera le mot de passe PostgreSQL superuser) :

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1
python scripts\setup_db.py
```

**OU** via pgAdmin (recommandé pour production) :

1. Connecte-toi à PostgreSQL en tant que superuser `postgres`
2. Exécute ce SQL dans Query Tool :

```sql
-- Créer le rôle
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dms') THEN
    CREATE ROLE dms LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
  ELSE
    ALTER ROLE dms PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
  END IF;
END$$;

-- Créer la base
CREATE DATABASE dms OWNER dms;

-- Se connecter à la base dms
\c dms

-- Activer pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## Étape 2 : Configurer DATABASE_URL

Le fichier `.env` est déjà créé avec des valeurs par défaut. **Mets à jour le mot de passe** :

```env
DATABASE_URL=postgresql+psycopg://dms:TON_MOT_DE_PASSE@localhost:5432/dms
```

## Étape 3 : Migrations Alembic

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## Étape 4 : Smoke Test

```powershell
python scripts\smoke_postgres.py
```

## Étape 5 : Tests

```powershell
python -m pytest tests -v
```

## Port PostgreSQL

**Port par défaut : `5432`** (configuré dans `.env` et `docker-compose.yml`)

Si tu changes le port PostgreSQL, mets à jour `DATABASE_URL` dans `.env` :
```
DATABASE_URL=postgresql+psycopg://dms:password@localhost:5433/dms
```
