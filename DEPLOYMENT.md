# 🚀 DÉPLOIEMENT DMS

## 📋 Modes de déploiement

### Local SQLite (Développement)

**Aucune configuration requise.**

```bash
# Installer dépendances
pip install -r requirements.txt

# Lancer serveur
python3 main.py

# Accès: http://localhost:5000
```

**Base de données**: `data/dms.sqlite3` (créé automatiquement)

---

### PostgreSQL Online (Production)

#### Option 1: Railway.app (Recommandé)

1. **Créer compte**: https://railway.app
2. **New Project** → Deploy from GitHub
3. **Connect repo**: `decision-memory-v1`
4. **Add Database** → PostgreSQL
5. **Variables d'environnement**: Railway injecte automatiquement `DATABASE_URL`

**Déploiement**: Automatique à chaque push sur `main`

---

#### Option 2: Render.com

1. **New Web Service** → Connect GitHub
2. **Add PostgreSQL** dans Services
3. **Variable d'environnement**:
   ```
   DATABASE_URL=${{ postgres.DATABASE_URL }}
   ```

4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

#### Option 3: Fly.io

```bash
# Installer flyctl
curl -L https://fly.io/install.sh | sh

# Déployer
fly launch
fly postgres create
fly postgres attach <db-name>
fly deploy
```

---

## 🔧 Configuration DATABASE_URL

### Format

```
# SQLite (local)
DATABASE_URL=sqlite:///data/dms.sqlite3

# PostgreSQL (prod)
DATABASE_URL=postgresql://user:password@host:5432/database
```

### Variables

Copier `.env.example` → `.env` et configurer:

```bash
cp .env.example .env
# Éditer .env avec vos credentials PostgreSQL
```

**Important**: `.env` est dans `.gitignore` (secrets pas committé)

---

## ✅ Vérification

### Test connexion DB

```python
python3 -c "from src.db import engine; print(engine.url)"
```

**Sortie attendue**:
- Dev: `sqlite:////workspace/data/dms.sqlite3`
- Prod: `postgresql://user@host:5432/db`

### Test API

```bash
curl http://localhost:5000/api/health
```

**Réponse attendue**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "invariants_status": "enforced"
}
```

---

## 📊 Migration données SQLite → PostgreSQL

Si vous avez déjà des données en SQLite local:

```bash
# Export SQLite
sqlite3 data/dms.sqlite3 .dump > export.sql

# Adapter pour PostgreSQL (remplacer syntaxe spécifique)
sed -i 's/AUTOINCREMENT/SERIAL/g' export.sql

# Import vers PostgreSQL
psql $DATABASE_URL < export.sql
```

---

## 🔒 Sécurité Production

**À ajouter avant mise en production** (hors scope actuel):

- Authentification API (JWT/API Keys)
- HTTPS (inclus par défaut sur Railway/Render/Fly)
- Rate limiting
- CORS configuré
- Variables secrets via dashboard cloud

---

## 📞 Support

**Local dev SQLite**: Fonctionne offline, zéro config  
**Prod PostgreSQL**: URL publique, multi-user, backups auto  

**Migration réversible**: Copier `data/dms.sqlite3` pour rollback
