# 🗄️ Comment créer la base de données et le rôle `dms`

## ✅ Option 1 : Script Python (le plus simple)

**Étape 1** : Ouvre PowerShell dans le projet

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1
```

**Étape 2** : Lance le script

```powershell

```

**Étape 3** : Quand il demande le mot de passe, entre le mot de passe de ton utilisateur PostgreSQL superuser (`postgres`)

Le script va :
- ✅ Créer le rôle `dms`
- ✅ Créer la base de données `dms`
- ✅ Activer l'extension `pg_trgm`
- ✅ Afficher le `DATABASE_URL` à mettre dans `.env`

**Étape 4** : Copie le `DATABASE_URL` affiché et mets-le dans `.env` (remplace la ligne existante)

---

## ✅ Option 2 : pgAdmin (interface graphique)

**Étape 1** : Ouvre **pgAdmin** (installé avec PostgreSQL)

**Étape 2** : Connecte-toi à ton serveur PostgreSQL (clic droit → Connect)

**Étape 3** : Ouvre **Query Tool** (clic droit sur le serveur → Query Tool)

**Étape 4** : Copie-colle ce SQL et **remplace `TON_MOT_DE_PASSE_FORT`** par un mot de passe fort :

```sql
-- Créer le rôle dms
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dms') THEN
    CREATE ROLE dms LOGIN PASSWORD 'TON_MOT_DE_PASSE_FORT';
  ELSE
    ALTER ROLE dms PASSWORD 'TON_MOT_DE_PASSE_FORT';
  END IF;
END$$;

-- Créer la base de données dms
CREATE DATABASE dms OWNER dms;

-- Se connecter à la base dms
\c dms

-- Activer l'extension pg_trgm (pour fuzzy matching)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Étape 5** : Clique sur **Execute** (F5)

**Étape 6** : Mets à jour `.env` avec ton mot de passe :

```env
DATABASE_URL=postgresql+psycopg://dms:TON_MOT_DE_PASSE_FORT@localhost:5432/dms
```

---

## ✅ Option 3 : psql en ligne de commande
python scripts\setup_db.py
Si `psql` est dans ton PATH :

```powershell
# Se connecter en tant que superuser postgres
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres

# Puis dans psql, exécute :
```

```sql
-- Créer le rôle
CREATE ROLE dms LOGIN PASSWORD 'TON_MOT_DE_PASSE_FORT';

-- Créer la base
CREATE DATABASE dms OWNER dms;

-- Se connecter à dms
\c dms

-- Activer pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Quitter
\q
```

---

## 🚀 Après création de la DB

Une fois la base créée, lance les migrations :

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1

# Migrations Alembic
alembic upgrade head

# Test de connexion
python scripts\smoke_postgres.py

# Tests complets
python -m pytest tests -v
```

---

## 💡 Quelle option choisir ?

- **Option 1 (Script Python)** : ✅ Le plus simple, tout automatique
- **Option 2 (pgAdmin)** : ✅ Visuel, bon si tu préfères les interfaces graphiques
- **Option 3 (psql)** : ✅ Rapide si tu es à l'aise en ligne de commande

**Recommandation** : Commence par l'**Option 1**, c'est la plus simple ! 🎯
