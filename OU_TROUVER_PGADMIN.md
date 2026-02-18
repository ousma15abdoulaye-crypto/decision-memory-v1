# 📍 Où trouver pgAdmin ?

## pgAdmin n'est pas installé sur ton système

pgAdmin n'est pas trouvé dans les emplacements standards. Voici tes options :

---

## ✅ Option 1 : Installer pgAdmin (recommandé)

### Méthode A : Via le site officiel

1. **Télécharge pgAdmin** : https://www.pgadmin.org/download/pgadmin-4-windows/
2. **Installe** le fichier `.exe` téléchargé
3. **Lance pgAdmin** depuis le menu Démarrer

### Méthode B : Via le Stack Builder PostgreSQL

1. **Ouvre PostgreSQL Stack Builder** (installé avec PostgreSQL)
   - Menu Démarrer → PostgreSQL 15 → Application Stack Builder
2. **Sélectionne** ton serveur PostgreSQL
3. **Installe** pgAdmin 4 depuis la liste des applications

---

## ✅ Option 2 : Utiliser psql (ligne de commande) — Plus rapide !

Tu n'as pas besoin de pgAdmin ! Tu peux créer la base directement avec `psql` :

### Étape 1 : Ouvre PowerShell

### Étape 2 : Essaie de te connecter avec différents utilisateurs

```powershell
# Essayer avec postgres
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres
```

**Si ça demande un mot de passe**, entre `Babayaga02022`

**Si ça ne fonctionne pas**, essaie avec ton utilisateur Windows :

```powershell
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U abdoulaye.ousmane -d postgres
```

### Étape 3 : Une fois connecté, exécute ce SQL :

```sql
-- Créer le rôle dms
CREATE ROLE dms LOGIN PASSWORD 'dms_dev_password_change_me';

-- Créer la base de données dms
CREATE DATABASE dms OWNER dms;

-- Se connecter à la base dms
\c dms

-- Activer l'extension pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Quitter
\q
```

---

## ✅ Option 3 : Script Python automatique (si tu connais le bon utilisateur)

Si tu sais quel utilisateur fonctionne avec le mot de passe `Babayaga02022`, dis-moi et je créerai un script adapté.

Sinon, essaie ces commandes pour trouver le bon utilisateur :

```powershell
# Avec postgres
$env:PGPASSWORD='Babayaga02022'; & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -c "SELECT current_user;"

# Avec ton utilisateur Windows
$env:PGPASSWORD='Babayaga02022'; & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U abdoulaye.ousmane -d postgres -c "SELECT current_user;"
```

---

## ✅ Option 4 : Utiliser DBeaver (alternative à pgAdmin)

1. **Télécharge DBeaver** : https://dbeaver.io/download/
2. **Installe** et lance
3. **Nouvelle connexion** → PostgreSQL
4. **Configure** :
   - Host: localhost
   - Port: 5432
   - Database: postgres
   - Username: postgres (ou ton utilisateur)
   - Password: Babayaga02022
5. **Test Connection** pour voir si ça fonctionne
6. **SQL Editor** → Colle le SQL de création de base

---

## 🎯 Recommandation

**Commence par l'Option 2 (psql)** — c'est le plus rapide et tu n'as pas besoin d'installer quoi que ce soit !

Essaie cette commande et dis-moi ce qui se passe :

```powershell
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres
```

Si ça demande un mot de passe, entre `Babayaga02022` et dis-moi si ça fonctionne ! 🚀
