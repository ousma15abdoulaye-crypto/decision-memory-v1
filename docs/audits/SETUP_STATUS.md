# ✅ Setup Status — Production Ready

## ✅ Fait

1. **Venv Python 3.11** : `.venv` créé avec toutes les dépendances installées
2. **Fichier `.env`** : Créé avec `DATABASE_URL` (à mettre à jour avec ton mot de passe)
3. **Scripts de setup** :
   - `scripts/setup_db.py` : Script Python pour créer DB/role automatiquement
   - `scripts/setup_postgres_local.ps1` : Script PowerShell alternatif
4. **Alembic** : Configuré pour charger `.env` automatiquement
5. **Port PostgreSQL** : **5432** (standard, configuré partout)

## ⚠️ À faire (1 seule étape)

**Créer la base de données et le rôle `dms`** :

### Option A : Script Python (recommandé)

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1
python scripts\setup_db.py
```

Le script demandera le mot de passe PostgreSQL superuser (`postgres`).

### Option B : pgAdmin (production)

1. Ouvre pgAdmin
2. Connecte-toi à PostgreSQL (superuser `postgres`)
3. Query Tool → Exécute :

```sql
-- Créer le rôle
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dms') THEN
    CREATE ROLE dms LOGIN PASSWORD 'TON_MOT_DE_PASSE_FORT';
  ELSE
    ALTER ROLE dms PASSWORD 'TON_MOT_DE_PASSE_FORT';
  END IF;
END$$;

-- Créer la base
CREATE DATABASE dms OWNER dms;

-- Se connecter à dms
\c dms

-- Activer pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

4. **Mets à jour `.env`** avec ton mot de passe :
   ```
   DATABASE_URL=postgresql+psycopg://dms:TON_MOT_DE_PASSE_FORT@localhost:5432/dms
   ```

## 🚀 Après création de la DB

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1

# Migrations
alembic upgrade head

# Smoke test
python scripts\smoke_postgres.py

# Tests complets
python -m pytest tests -v
```

## 📋 Port PostgreSQL

**Port par défaut : `5432`** ✅

Si tu changes le port PostgreSQL, mets à jour `DATABASE_URL` dans `.env` :
```
DATABASE_URL=postgresql+psycopg://dms:password@localhost:5433/dms
```
