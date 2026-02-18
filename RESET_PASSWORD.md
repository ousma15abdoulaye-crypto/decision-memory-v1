# 🔑 Réinitialiser le mot de passe PostgreSQL

## ✅ Méthode simple (5 minutes)

### Étape 1 : Ouvre PowerShell en tant qu'Administrateur

1. **Clic droit** sur le menu Démarrer
2. **Windows PowerShell (Admin)** ou **Terminal (Admin)**
3. Clique sur **Oui** pour autoriser

### Étape 2 : Arrête PostgreSQL

```powershell
Stop-Service postgresql-x64-15
```

(Remplace `15` par ta version si différente)

### Étape 3 : Modifie pg_hba.conf

Ouvre le fichier dans Notepad (en tant qu'admin) :

```powershell
notepad "C:\Program Files\PostgreSQL\15\data\pg_hba.conf"
```

**Cherche ces lignes** (vers la fin du fichier) :

```
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
local   all             all                                     scram-sha-256
```

**Remplace `scram-sha-256` par `trust`** :

```
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
local   all             all                                     trust
```

**Sauvegarde** (Ctrl+S) et **ferme** Notepad.

### Étape 4 : Redémarre PostgreSQL

```powershell
Start-Service postgresql-x64-15
```

### Étape 5 : Change le mot de passe

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD 'Babayaga02022';"
```

Tu devrais voir : `ALTER ROLE`

### Étape 6 : Remet pg_hba.conf en sécurité

**Rouvre** pg_hba.conf :

```powershell
notepad "C:\Program Files\PostgreSQL\15\data\pg_hba.conf"
```

**Remets** `scram-sha-256` (ou `md5`) :

```
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
local   all             all                                     scram-sha-256
```

**Sauvegarde** et **ferme**.

### Étape 7 : Redémarre PostgreSQL

```powershell
Restart-Service postgresql-x64-15
```

### Étape 8 : Teste la connexion

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
$env:PGPASSWORD='Babayaga02022'; & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -c "SELECT current_user;"
```

Tu devrais voir : `postgres`

---

## 🚀 Après réinitialisation

Une fois le mot de passe réinitialisé, crée la base :

```powershell
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
.\.venv\Scripts\Activate.ps1
python scripts\setup_db_with_password.py --password Babayaga02022
```

Puis les migrations :

```powershell
alembic upgrade head
python scripts\smoke_postgres.py
```

---

## ⚠️ Important

- **Fais ça en PowerShell Admin** (clic droit → Exécuter en tant qu'administrateur)
- **Remets `scram-sha-256` après** pour la sécurité
- Le fichier `pg_hba.conf` est dans `C:\Program Files\PostgreSQL\15\data\`
