# Audit CI & Conformité Constitution V3.1

**Date** : 2026-02-13  
**Auteur** : Agent d'audit GitHub Copilot  
**Statut** : 🔴 **CRITIQUE** – CI échoue, correctifs requis  

---

## Résumé exécutif

**Verdict général** : Le projet présente 2 problèmes **critiques** bloquant la CI et 1 violation de la Constitution.

### Problèmes critiques identifiés

1. 🔴 **CI masque les échecs de tests** : `|| true` dans `.github/workflows/ci.yml` ligne 45 viole **Invariant 5**
2. 🔴 **Endpoints d'authentification non protégés** : Absence de rate limiting sur `/auth/token`, `/auth/register`, `/auth/me` (violation Constitution M4A-F)
3. 🟡 **Tests potentiellement défaillants** : La CI cache les échecs, tests réels non vérifiés

**Impact** : La CI est verte artificiellement. Les vrais problèmes sont masqués. Risque de sécurité sur les endpoints d'authentification.

---

## 1. Workflows GitHub Actions

### ✅ Structure générale correcte

- **Fichier unique** : `.github/workflows/ci.yml` ✅ (pas de workflows multiples)
- **Service PostgreSQL** : Correctement configuré
  - Image : `postgres:15` ✅
  - Health checks : présents ✅
  - Port : `5432:5432` ✅
  - Base de données : `test_db` ✅

### ✅ Configuration DATABASE_URL

```yaml
DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/test_db
```

- Format : ✅ Correct (`postgresql+psycopg://`)
- Driver : ✅ psycopg (Constitution conforme)
- Injection : ✅ Variable d'environnement présente

### ✅ Étapes du workflow

1. Checkout : ✅ `actions/checkout@v3`
2. Python setup : ✅ `3.11.9` (conforme `runtime.txt`)
3. Installation dépendances : ✅ `pip install -r requirements.txt`
4. Tests : ❌ **PROBLÈME CRITIQUE**

### 🔴 Problème #1 : Masquage des erreurs de tests

**Fichier** : `.github/workflows/ci.yml`  
**Ligne** : 45  
**Code actuel** :
```yaml
run: |
  pytest tests/ -v --tb=short || true
```

**Cause racine** : `|| true` force le succès même si pytest échoue.

**Impact** : 
- ❌ Viole **Invariant 5** de la Constitution : "CI verte obligatoire"
- ❌ Les tests peuvent échouer silencieusement
- ❌ Impossible de détecter les régressions
- ❌ Fausse impression de stabilité du projet

**Solution** :
```yaml
run: |
  pytest tests/ -v --tb=short
```

**Priorité** : 🔴 **CRITIQUE** – Bloquer immédiatement

---

## 2. Migrations Alembic

### ✅ Structure des migrations

**Fichiers présents** :
1. `alembic/versions/002_add_couche_a.py` ✅
2. `alembic/versions/003_add_procurement_extensions.py` ✅
3. `alembic/versions/004_users_rbac.py` ✅

### ✅ Chaîne de dépendances

```
002_add_couche_a
    ↓
003_add_procurement_extensions
    ↓
004_users_rbac
```

**Vérification** :
- `002` : `down_revision = None` ✅
- `003` : `down_revision = '002_add_couche_a'` ✅
- `004` : `down_revision = '003_add_procurement_extensions'` ✅

### ✅ Conformité Constitution

**Pattern `_get_bind` / `_execute_sql`** : ✅ Présent dans toutes les migrations

```python
def _get_bind(engine: Optional[Engine] = None) -> Engine | Connection:
    """Retourne la connexion/engine approprié."""
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine

def _execute_sql(target, sql: str) -> None:
    """Exécute du SQL brut."""
    if isinstance(target, Engine):
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    else:
        target.execute(text(sql))
```

**Vérifications Constitution** :
- ❌ Pas d'`op.create_table` direct : ✅ Utilise `CREATE TABLE IF NOT EXISTS`
- ❌ Pas de `metadata.create_all` : ✅ Aucune utilisation d'ORM
- ❌ Pas de code asynchrone : ✅ Tout synchrone
- ✅ Syntaxe PostgreSQL : ✅ `TRUE/FALSE`, `GENERATED ALWAYS AS IDENTITY`, `JSONB`
- ✅ Idempotence : ✅ `IF NOT EXISTS`, `ON CONFLICT DO NOTHING`

### ✅ Migration 003 : Corrections appliquées

**Problème historique** (résolu dans `RAPPORT_DEBLOCAGE_CI_MIGRATION_003.md`) :
- ❌ Syntaxe `server_default='1'` au lieu de `sa.text('TRUE')` → ✅ **CORRIGÉ**
- ❌ `INSERT VALUES (..., 1, ...)` au lieu de `TRUE` → ✅ **CORRIGÉ**

**État actuel** : Toutes les migrations utilisent `TRUE/FALSE` correctement.

**Verdict migrations** : ✅ **CONFORMES Constitution V3.1**

---

## 3. Tests

### 🟡 Problème #3 : État des tests inconnu

**Cause** : CI masque les échecs avec `|| true`, impossible de connaître l'état réel.

**Tests présents** :
```
tests/test_resilience.py
tests/test_upload.py
tests/test_rbac.py
tests/test_auth.py
tests/test_corrections_smoke.py
tests/test_partial_offers.py
tests/test_upload_security.py
tests/test_templates.py
tests/couche_a/test_endpoints.py
tests/couche_a/test_migration.py
tests/mapping/test_engine_smoke.py
```

**Action requise** : Exécuter les tests après suppression de `|| true` pour identifier les échecs réels.

**Tests skippés** : À vérifier après correction CI (recherche `@pytest.mark.skip`)

**Couverture de code** : Constitution exige **≥40%** sur modules critiques :
- `src/upload_security.py`
- `src/auth.py`
- `src/couche_a/services/`

**Action** : Mesurer couverture après stabilisation CI.

---

## 4. Code source

### ✅ Conformité Constitution V3.1

**Vérifications effectuées** :

| Critère Constitution | Statut | Détails |
|---------------------|--------|---------|
| Appels DB synchrones uniquement | ✅ | Tous via `src.db` helpers |
| Pas d'`asyncpg` | ✅ | Utilise `psycopg` |
| Pas d'`await conn.execute` | ✅ | Aucune DB asynchrone |
| Pas d'ORM (SQLAlchemy models) | ✅ | SQL brut uniquement |
| Pas de `sqlite3` | ✅ | PostgreSQL uniquement |
| Pas de `metadata.create_all` | ✅ | Migrations manuelles |
| Rate limiting endpoints sensibles | ❌ | **Violation auth_router.py** |
| Validation uploads (MIME, taille, quota) | ✅ | `src/upload_security.py` conforme |
| Pas de code mort | ✅ | Aucune référence SQLite trouvée |

### 🔴 Problème #2 : Endpoints d'authentification non protégés

**Fichier** : `src/auth_router.py`  
**Lignes** : 40-76  

**Endpoints vulnérables** :
1. `POST /auth/token` (ligne 40-56) – Login
2. `POST /auth/register` (ligne 59-69) – Enregistrement
3. `GET /auth/me` (ligne 72-76) – Info utilisateur

**Code actuel** :
```python
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Pas de @limiter.limit()
```

**Violation Constitution** : 
- Section M4A-F (Sécurité) : Rate limiting obligatoire sur endpoints sensibles
- Risque : Brute-force sur `/token`, spam sur `/register`

**Solution** :
```python
from src.ratelimit import limiter  # Import déjà présent dans src/couche_a/routers.py

@limiter.limit("5/minute")  # 5 tentatives/minute max
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    ...

@limiter.limit("3/hour")  # 3 enregistrements/heure max
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserRegister):
    ...

@limiter.limit("60/minute")  # 60 requêtes/minute max
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    ...
```

**Priorité** : 🔴 **CRITIQUE** – Risque de sécurité

### ✅ Ordre des paramètres FastAPI (PEP 570)

**Vérification** : Endpoints respectent `path → query → body → dependencies`  
**Statut** : ✅ Aucune violation détectée

### ✅ Helpers DB synchrones

**Fichier** : `src/db.py`  
**Statut** : ✅ Conforme Constitution
- Driver : `psycopg` (PostgreSQL sync)
- Retry logic : ✅ Via `tenacity`
- Circuit breaker : ✅ Via `pybreaker`
- Aucune référence async

---

## 5. Configuration Railway

### 🟡 Fichiers de configuration manquants

**Recherche effectuée** :
```bash
$ ls -la | grep -E "(nixpacks|railway)"
# Aucun résultat
```

**Fichiers attendus** (pour déploiement Railway) :
1. `nixpacks.toml` – Configuration buildpack
2. `railway.json` – Configuration Railway (optionnel)

**Impact** : 
- ⚠️ Railway utilisera la détection automatique
- ⚠️ Dépendances système (ex: `libmagic` pour `python-magic`) pourraient manquer
- ⚠️ Commande de démarrage par défaut non optimale

**Recommandations** (non bloquant pour CI) :

**nixpacks.toml** :
```toml
[phases.setup]
nixPkgs = ["python311", "postgresql", "file"]  # file = libmagic

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

**Priorité** : 🟡 **Mineur** – Déploiement seulement

---

## 6. Conformité Constitution V3.1

### Invariants (§2)

| Invariant | Statut | Détails |
|-----------|--------|---------|
| **1. Réduction charge cognitive** | ✅ | Architecture 3 écrans respectée |
| **2. Primauté Couche A** | ✅ | Pas de dépendance Couche B dans Couche A |
| **3. Mémoire = sous-produit** | ✅ | Aucune action "pour documenter" imposée |
| **4. Système non décisionnaire** | ✅ | Pas de scoring/recommandation |
| **5. Traçabilité sans accusation** | ❌ | CI masque erreurs (`|| true`) – **VIOLATION** |
| **6. Online-first haute perf** | ✅ | FastAPI + PostgreSQL |
| **6 bis. Supériorité sur Excel** | ✅ | CBA/PV exports optimisés |
| **7. ERP-agnostique** | ✅ | Aucune dépendance ERP |
| **8. Append-only** | ✅ | Tables d'audit, pas de DELETE |
| **9. Techno subordonnée** | ✅ | IA/LLM optionnels |
| **10. Survivabilité** | ✅ | Code structuré, migrations versionnées |

### Sections critiques (§7-11)

| Section | Statut | Détails |
|---------|--------|---------|
| **§7 : Frontière Couche A/B** | ✅ | `src/couche_a/` séparé, pas de cross-imports |
| **§8 : Machine d'état (CBA)** | ✅ | Workflow extraction → structuration → export |
| **§9 : Doctrine d'échec** | ❌ | CI masque échecs – **VIOLATION** |
| **§10 : Sécurité (M4A-F)** | ❌ | Rate limiting manquant sur auth – **VIOLATION** |
| **§11 : Résilience (M4D)** | ✅ | Retry + circuit breaker présents |

**Bilan conformité** : **7/10 invariants OK** – 3 violations critiques détectées

---

## Actions correctives (priorisées)

### 🔴 Critiques (Bloquer PR)

1. **Supprimer `|| true` dans CI** (Invariant 5)
   ```bash
   # Fichier : .github/workflows/ci.yml, ligne 45
   # Avant :
   run: |
     pytest tests/ -v --tb=short || true
   
   # Après :
   run: |
     pytest tests/ -v --tb=short
   ```
   **Effet** : Tests échouent → bloquer merge si échec

2. **Ajouter rate limiting sur auth endpoints** (§10 Sécurité M4A-F)
   ```python
   # Fichier : src/auth_router.py
   # Ajouter import :
   from src.ratelimit import limiter
   
   # Décorer chaque endpoint :
   @limiter.limit("5/minute")
   @router.post("/token", response_model=Token)
   ...
   
   @limiter.limit("3/hour")
   @router.post("/register", response_model=UserResponse, status_code=201)
   ...
   
   @limiter.limit("60/minute")
   @router.get("/me", response_model=UserResponse)
   ...
   ```

3. **Exécuter tests réels et corriger échecs**
   ```bash
   # Après suppression || true :
   pytest tests/ -v --tb=short
   # → Identifier et corriger tous les tests défaillants
   ```

### 🟠 Importants (Post-stabilisation CI)

4. **Mesurer couverture de tests**
   ```bash
   pytest tests/ --cov=src --cov-report=html --cov-fail-under=40
   ```
   **Objectif** : ≥40% sur modules critiques (Constitution)

5. **Ajouter configuration Railway** (déploiement)
   - Créer `nixpacks.toml` avec dépendances système
   - Vérifier commande démarrage (`alembic upgrade head && uvicorn...`)

### 🟡 Mineurs (Optimisation)

6. **Améliorer rate limiting** (après validation CI)
   - Passer de `MemoryStorage` à `RedisStorage` en production
   - Configurer limites par rôle utilisateur

7. **Documenter processus CI** (après stabilisation)
   - Ajouter `docs/CI.md` avec explication workflow
   - Documenter procédure debug CI failures

---

## Vérification finale

### Checklist pré-merge

- [ ] `|| true` supprimé de `.github/workflows/ci.yml`
- [ ] Rate limiting ajouté sur `/auth/token`, `/auth/register`, `/auth/me`
- [ ] Tests passent : `pytest tests/ -v` → ✅ succès
- [ ] Migrations passent : `alembic upgrade head` → ✅ succès
- [ ] Compilation Python : `python -m compileall src/` → ✅ succès
- [ ] Aucune violation Constitution détectée
- [ ] CI GitHub Actions verte (vraiment, pas masquée)

### Commandes de validation

```bash
# 1. Tests
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test_db"
pytest tests/ -v --tb=short

# 2. Migrations
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 3. Compilation
python -m compileall src/ -q

# 4. Vérifications Constitution
grep -r "import sqlite3" src/          # → Aucun résultat attendu
grep -r "metadata.create_all" src/     # → Aucun résultat attendu
grep -r "asyncpg" src/                 # → Aucun résultat attendu
grep -r "await.*execute" src/          # → Aucun résultat attendu
```

**Statut attendu après correctifs** : ✅ **CI verte sans masquage, Constitution respectée**

---

## Notes de l'audit

### Points positifs ✅

1. **Migrations bien structurées** : Pattern `_get_bind`/`_execute_sql` respecté
2. **Syntaxe PostgreSQL correcte** : `TRUE/FALSE`, idempotence
3. **Architecture propre** : Séparation Couche A/B claire
4. **Pas d'ORM** : SQL brut conforme Constitution
5. **Résilience** : Retry + circuit breaker présents
6. **Upload security** : Validation MIME, quota, taille OK

### Points critiques à corriger ❌

1. **CI masque les erreurs** : `|| true` invalide tout le processus de test
2. **Endpoints auth non protégés** : Risque brute-force / spam
3. **Tests non vérifiés** : État réel inconnu à cause du masquage

### Recommandations architecturales 💡

1. **Ajouter pre-commit hooks** : Bloquer commits si tests échouent localement
2. **CI/CD améliorée** : Ajouter étape build + lint avant tests
3. **Monitoring** : Logs rate limiting pour détecter attaques
4. **Documentation** : Enrichir `docs/` avec guide contribution + CI

---

**FIN DU RAPPORT D'AUDIT**

**Prochaine étape** : Application des correctifs critiques #1 et #2, puis validation tests.
