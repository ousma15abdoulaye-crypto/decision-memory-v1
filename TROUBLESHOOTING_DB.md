# 🔧 Troubleshooting — Création de la base de données

## Problème : Le mot de passe ne fonctionne pas

Le mot de passe `Babayaga02022` ne fonctionne pas pour se connecter à PostgreSQL.

## ✅ Solution 1 : Vérifier dans pgAdmin

1. **Ouvre pgAdmin**
2. **Regarde la liste des serveurs** à gauche
3. **Clique sur ton serveur PostgreSQL** → **Propriétés** (clic droit)
4. **Note le nom d'utilisateur** utilisé pour la connexion (peut être différent de `postgres`)
5. **Teste la connexion** dans pgAdmin pour confirmer le mot de passe

## ✅ Solution 2 : Réinitialiser le mot de passe PostgreSQL

Si tu ne te souviens plus du mot de passe :

### Méthode A : Via pgAdmin (si tu peux te connecter)

1. Connecte-toi à pgAdmin
2. Clic droit sur le serveur → **Properties**
3. Change le mot de passe dans l'onglet **Connection**

### Méthode B : Via ligne de commande Windows

1. **Ouvre PowerShell en tant qu'Administrateur**
2. **Arrête PostgreSQL** :
   ```powershell
   Stop-Service postgresql-x64-15
   ```
   (Remplace `15` par ta version si différente)

3. **Démarre PostgreSQL en mode single-user** :
   ```powershell
   & "C:\Program Files\PostgreSQL\15\bin\postgres.exe" --single -D "C:\Program Files\PostgreSQL\15\data" postgres
   ```

4. Dans la console PostgreSQL qui s'ouvre, tape :
   ```sql
   ALTER USER postgres WITH PASSWORD 'Babayaga02022';
   \q
   ```

5. **Redémarre PostgreSQL** :
   ```powershell
   Start-Service postgresql-x64-15
   ```

## ✅ Solution 3 : Créer la base directement dans pgAdmin

Une fois connecté à pgAdmin avec ton utilisateur/mot de passe qui fonctionne :

1. **Query Tool** (clic droit sur le serveur → Query Tool)
2. **Colle ce SQL** :

```sql
-- Créer le rôle dms
CREATE ROLE dms LOGIN PASSWORD 'dms_dev_password_change_me';

-- Créer la base de données dms
CREATE DATABASE dms OWNER dms;

-- Se connecter à la base dms
\c dms

-- Activer l'extension pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

3. **Execute** (F5)
4. **Mets à jour `.env`** :

```env
DATABASE_URL=postgresql+psycopg://dms:dms_dev_password_change_me@localhost:5432/dms
```

## ✅ Solution 4 : Utiliser l'authentification Windows (si configurée)

Si PostgreSQL est configuré pour l'authentification Windows :

1. **Ouvre pgAdmin**
2. **Crée une nouvelle connexion** avec :
   - **Host**: localhost
   - **Port**: 5432
   - **Maintenance database**: postgres
   - **Username**: ton utilisateur Windows (ex: `abdoulaye.ousmane`)
   - **Password**: laisse vide si auth Windows

3. Une fois connecté, utilise le **Query Tool** pour créer la base (voir Solution 3)

## 🚀 Après création de la base

Une fois la base créée, lance :

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1

# Migrations
alembic upgrade head

# Test
python scripts\smoke_postgres.py

# Tests
python -m pytest tests -v
```

## 💡 Vérifier que PostgreSQL écoute sur le port 5432

```powershell
netstat -an | findstr 5432
```

Tu devrais voir `0.0.0.0:5432` ou `127.0.0.1:5432` si PostgreSQL écoute.
