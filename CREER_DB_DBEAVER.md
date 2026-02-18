# 🗄️ Créer la base de données avec DBeaver

## ✅ Étape 1 : Se connecter à PostgreSQL

1. **Ouvre DBeaver**
2. **Nouvelle connexion** (icône prise électrique en haut à gauche) ou **Database** → **New Database Connection**
3. **Sélectionne PostgreSQL** → **Next**

### Configuration de la connexion :

- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `postgres` (base par défaut)
- **Username**: `postgres`
- **Password**: `Babayaga02022` (ou ton mot de passe actuel)

4. **Test Connection** → Si ça échoue, essaie avec ton utilisateur Windows (`abdoulaye.ousmane`) au lieu de `postgres`
5. **Finish**

---

## ✅ Étape 2 : Créer le rôle `dms`

1. **Clic droit** sur ta connexion PostgreSQL → **SQL Editor** → **New SQL Script**
2. **Colle ce SQL** :

```sql
-- Créer le rôle dms
CREATE ROLE dms LOGIN PASSWORD 'dms_dev_password_change_me';
```

3. **Execute** (Ctrl+Enter ou bouton ▶️)
4. Tu devrais voir : `SQL executed successfully`

---

## ✅ Étape 3 : Créer la base de données `dms`

Dans le même SQL Editor, **ajoute et exécute** :

```sql
-- Créer la base de données dms
CREATE DATABASE dms OWNER dms;
```

**Execute** (Ctrl+Enter)

---

## ✅ Étape 4 : Activer l'extension pg_trgm

1. **Clic droit** sur la base `dms` (dans l'arborescence à gauche) → **SQL Editor** → **New SQL Script**
   OU
   **Clic droit** sur ta connexion → **Edit Connection** → Change **Database** de `postgres` à `dms` → **Test Connection** → **OK**

2. **Nouveau SQL Script** → Colle :

```sql
-- Activer l'extension pg_trgm pour fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

3. **Execute** (Ctrl+Enter)

---

## ✅ Étape 5 : Mettre à jour `.env`

Ouvre le fichier `.env` dans ton projet et mets à jour :

```env
DATABASE_URL=postgresql+psycopg://dms:dms_dev_password_change_me@localhost:5432/dms
```

---

## ✅ Étape 6 : Migrations et tests

Dans PowerShell :

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1

# Migrations Alembic
alembic upgrade head

# Smoke test
python scripts\smoke_postgres.py

# Tests complets
python -m pytest tests -v
```

---

## 💡 Astuce DBeaver

- **Rafraîchir** : Clic droit sur la connexion → **Refresh** pour voir la nouvelle base `dms`
- **Voir les tables** : Une fois les migrations faites, tu verras toutes les tables dans `dms` → **Schemas** → **public** → **Tables**
- **Exécuter du SQL** : Toujours disponible via **SQL Editor**

---

## ✅ Vérification rapide

Dans DBeaver, après avoir créé la base :

1. **Clic droit** sur `dms` → **Edit Connection**
2. **Test Connection** → Devrait être ✅ vert
3. **SQL Editor** → Exécute :

```sql
SELECT current_database(), current_user;
```

Tu devrais voir :
- `current_database`: `dms`
- `current_user`: `dms`

---

## 🎯 Tout en une fois (Script SQL complet)

Si tu préfères tout faire d'un coup, dans DBeaver **SQL Editor** connecté à `postgres` :

```sql
-- Créer le rôle dms
CREATE ROLE dms LOGIN PASSWORD 'dms_dev_password_change_me';

-- Créer la base de données dms
CREATE DATABASE dms OWNER dms;

-- Se connecter à dms (change manuellement la connexion dans DBeaver)
-- Puis exécute :
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Important** : Pour la dernière commande (`CREATE EXTENSION`), tu dois être connecté à la base `dms`, pas à `postgres`.

Pour ça dans DBeaver :
- **Clic droit** sur ta connexion → **Edit Connection**
- Change **Database** : `postgres` → `dms`
- **Test Connection** → **OK**
- **Nouveau SQL Script** → Colle `CREATE EXTENSION IF NOT EXISTS pg_trgm;` → **Execute**

---

C'est tout ! 🚀
