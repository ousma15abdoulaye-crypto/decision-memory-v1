# Plan Ingénieur: Tests Coverage 41% → 60%

**Date**: 2026-02-13  
**Objectif**: Élever coverage de 41% (actuel) à 60% (production-ready)  
**Stratégie**: Tests ciblés modules critiques + fixtures PostgreSQL

---

## 📊 État Actuel Coverage

```
TOTAL: 41% (1377 statements, 813 missed)

Modules HAUTE coverage (à maintenir):
✅ src/resilience.py: 97%
✅ src/templates/cba_template.py: 99%
✅ src/templates/pv_template.py: 99%

Modules ZÉRO coverage (critiques):
❌ src/auth.py: 0% (97 stmts) - JWT + RBAC
❌ src/auth_router.py: 0% (36 stmts) - Endpoints auth
❌ src/couche_a/routers.py: 0% (106 stmts) - Upload workflows
❌ src/db.py: 51% (78 stmts, 38 missed) - DB layer
❌ src/upload_security.py: 0% (44 stmts) - Security validation
❌ alembic/env.py: 0% (34 stmts) - Migrations
```

**Analyse:**
- 11 tests passent SANS DATABASE_URL (resilience, templates, mapping)
- 7 fichiers tests bloqués par DATABASE_URL required (Constitution V2.1 online-only)
- Pour tester auth/routers/db: PostgreSQL test fixture OBLIGATOIRE

---

## 🎯 Objectif: 60% Coverage

**Calcul:**
- Total statements: 1377
- 60% target: 826 statements couverts
- Actuel: 564 couverts (41%)
- Gap: **262 statements à couvrir**

**Priorités (impact/effort):**

| Module | Statements Missed | Priority | Tests à créer | Effort |
|--------|-------------------|----------|---------------|--------|
| src/auth.py | 97 | 🔴 CRITIQUE | 8-10 tests | 4h |
| src/couche_a/routers.py | 106 | 🔴 CRITIQUE | 6-8 tests | 4h |
| src/db.py | 38 | 🟠 HAUTE | 5-6 tests | 2h |
| src/upload_security.py | 44 | 🟠 HAUTE | 4-5 tests | 2h |
| src/auth_router.py | 36 | 🟡 MOYENNE | 3-4 tests | 2h |
| alembic/env.py | 34 | 🟡 MOYENNE | 2-3 tests | 1h |

**Total effort:** ~15 heures pour 60% coverage

---

## 📋 Plan Exécution (4 phases)

### Phase 1: Setup Infrastructure Tests (2h)

**Objectif:** Créer fixtures PostgreSQL test pour débloquer tests auth/routers/db

**Fichier:** `tests/conftest.py` (global fixtures)

```python
import pytest
import os
from sqlalchemy import create_engine, text
from contextlib import contextmanager

@pytest.fixture(scope="session")
def test_database_url():
    """
    PostgreSQL test database URL.
    
    En local: export DATABASE_URL="postgresql://localhost/dms_test"
    En CI: Fourni par service container
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL required for integration tests")
    return url

@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """SQLAlchemy engine pour tests."""
    from src.db import _normalize_url
    url = _normalize_url(test_database_url)
    if "postgresql://" in url and "postgresql+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, pool_pre_ping=True)
    return engine

@pytest.fixture(scope="function")
def db_connection(test_engine):
    """
    Connexion DB avec rollback automatique (isolation tests).
    
    Chaque test tourne dans une transaction rollbackée.
    Aucune donnée persistée entre tests.
    """
    conn = test_engine.connect()
    trans = conn.begin()
    
    yield conn
    
    trans.rollback()
    conn.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_schema(test_engine):
    """
    Crée schéma test via Alembic migrations.
    Exécuté une fois par session test.
    """
    from alembic import command
    from alembic.config import Config
    
    # Appliquer migrations
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    
    yield
    
    # Cleanup après tous tests (optionnel)
    # command.downgrade(config, "base")
```

**Fichier:** `tests/couche_a/conftest.py` (fixtures Couche A spécifiques)

```python
import pytest
from datetime import datetime

@pytest.fixture
def sample_case(db_connection):
    """Crée un case test."""
    case_id = "TEST_CASE_001"
    db_connection.execute(text("""
        INSERT INTO cases (id, case_type, title, lot, created_at, status)
        VALUES (:id, 'DAO', 'Test Case', 'LOT1', :ts, 'draft')
    """), {"id": case_id, "ts": datetime.utcnow().isoformat()})
    return case_id

@pytest.fixture
def sample_user(db_connection):
    """Crée un user test avec role admin."""
    from src.auth import get_password_hash
    
    # Créer role si absent
    db_connection.execute(text("""
        INSERT INTO roles (name, description, created_at) 
        VALUES ('admin', 'Test Admin', :ts)
        ON CONFLICT (name) DO NOTHING
    """), {"ts": datetime.utcnow().isoformat()})
    
    # Créer user
    db_connection.execute(text("""
        INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at)
        SELECT 'test@dms.local', 'testuser', :pwd, 'Test User', TRUE, TRUE, r.id, :ts
        FROM roles r WHERE r.name = 'admin'
        ON CONFLICT (username) DO NOTHING
    """), {
        "pwd": get_password_hash("Test123!"),
        "ts": datetime.utcnow().isoformat()
    })
    
    return {"username": "testuser", "password": "Test123!"}
```

**Effort:** 2h (setup fixtures + documentation)

---

### Phase 2: Tests Auth & DB (6h)

**Objectif:** Couvrir modules critiques auth + db (50% → 80% coverage sur ces modules)

#### 2.1 Tests `src/auth.py` (4h)

**Fichier:** `tests/test_auth_core.py` (nouveau)

**Scénarios:**

1. **test_verify_password_correct** (15 min)
   ```python
   def test_verify_password_correct():
       pwd = "Test123!"
       hashed = get_password_hash(pwd)
       assert verify_password(pwd, hashed) == True
   ```

2. **test_verify_password_incorrect** (10 min)
   ```python
   def test_verify_password_incorrect():
       hashed = get_password_hash("Test123!")
       assert verify_password("WrongPassword", hashed) == False
   ```

3. **test_get_user_by_username_exists** (20 min)
   ```python
   def test_get_user_by_username_exists(db_connection, sample_user):
       user = get_user_by_username("testuser")
       assert user is not None
       assert user["username"] == "testuser"
       assert user["role_name"] == "admin"
   ```

4. **test_get_user_by_username_not_exists** (10 min)
   ```python
   def test_get_user_by_username_not_exists():
       user = get_user_by_username("nonexistent")
       assert user is None
   ```

5. **test_create_access_token** (20 min)
   ```python
   def test_create_access_token():
       data = {"sub": "testuser", "role": "admin"}
       token = create_access_token(data)
       assert token is not None
       assert isinstance(token, str)
       # Décoder token et vérifier payload
   ```

6. **test_verify_token_valid** (20 min)
   ```python
   def test_verify_token_valid():
       data = {"sub": "testuser"}
       token = create_access_token(data)
       payload = verify_token(token)
       assert payload["sub"] == "testuser"
   ```

7. **test_verify_token_expired** (30 min)
   ```python
   def test_verify_token_expired():
       # Créer token avec expiration -1 minute
       data = {"sub": "testuser", "exp": datetime.utcnow() - timedelta(minutes=1)}
       token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
       with pytest.raises(HTTPException) as exc:
           verify_token(token)
       assert exc.value.status_code == 401
   ```

8. **test_get_current_user_valid_token** (30 min)
   ```python
   @pytest.mark.asyncio
   async def test_get_current_user_valid_token(db_connection, sample_user):
       token = create_access_token({"sub": "testuser"})
       user = await get_current_user(token)
       assert user.username == "testuser"
       assert user.role == "admin"
   ```

9. **test_get_current_user_invalid_token** (20 min)
   ```python
   @pytest.mark.asyncio
   async def test_get_current_user_invalid_token():
       with pytest.raises(HTTPException) as exc:
           await get_current_user("invalid_token")
       assert exc.value.status_code == 401
   ```

10. **test_check_case_ownership_owner** (20 min)
    ```python
    def test_check_case_ownership_owner(db_connection, sample_case, sample_user):
        # User owns case
        user = CurrentUser(user_id=1, username="testuser", role="admin")
        # Should not raise
        check_case_ownership(sample_case, user)
    ```

**Total:** 10 tests, ~3-4h développement + 1h debugging/refactoring

**Coverage attendue:** src/auth.py: 0% → 75%

#### 2.2 Tests `src/db.py` (2h)

**Fichier:** `tests/test_db_core.py` (nouveau)

**Scénarios:**

1. **test_get_connection_success** (30 min)
2. **test_get_connection_rollback_on_error** (30 min)
3. **test_db_execute_retry_on_operational_error** (30 min)
4. **test_db_execute_one_returns_dict** (15 min)
5. **test_db_fetchall_returns_list** (15 min)

**Coverage attendue:** src/db.py: 51% → 80%

---

### Phase 3: Tests Routers & Upload Security (6h)

#### 3.1 Tests `src/couche_a/routers.py` (4h)

**Fichier:** `tests/couche_a/test_routers.py` (améliorer test_endpoints.py existant)

**Scénarios critiques:**

1. **test_upload_dao_success** (1h)
   - Mock UploadFile
   - Vérifier artifact créé en DB
   - Vérifier fichier enregistré sur disque
   
2. **test_upload_dao_duplicate_409** (30 min)
   - Upload DAO déjà existant
   - Vérifier HTTP 409 Conflict
   
3. **test_upload_offer_success** (1h)
   - Upload offre avec supplier_name, offer_type, lot_id
   - Vérifier artifact + offer créés
   
4. **test_upload_offer_missing_supplier** (20 min)
   - Upload sans supplier_name
   - Vérifier HTTP 422 Validation Error
   
5. **test_register_artifact_creates_entry** (30 min)
6. **test_compute_file_hash_consistent** (20 min)
7. **test_upload_unauthorized** (30 min)
8. **test_upload_rate_limited** (30 min)

**Total:** 8 tests, ~4h

**Coverage attendue:** src/couche_a/routers.py: 0% → 70%

#### 3.2 Tests `src/upload_security.py` (2h)

**Fichier:** `tests/test_upload_security_core.py` (améliorer existant)

**Scénarios:**

1. **test_validate_mime_type_allowed** (15 min)
2. **test_validate_mime_type_blocked** (15 min)
3. **test_validate_file_size_ok** (15 min)
4. **test_validate_file_size_exceeded** (15 min)
5. **test_sanitize_filename_removes_special_chars** (20 min)
6. **test_update_case_quota_increments** (30 min)
7. **test_update_case_quota_exceeds_limit** (30 min)

**Total:** 7 tests, ~2h

**Coverage attendue:** src/upload_security.py: 0% → 80%

---

### Phase 4: Tests Migrations (1h)

**Objectif:** Garantir intégrité chaîne migrations

**Fichier:** `tests/migrations/test_migration_chain.py` (nouveau)

```python
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="module")
def alembic_config():
    return Config("alembic.ini")

def test_migration_chain_upgrade(alembic_config, test_engine):
    """
    Test upgrade complet: base → head
    Vérifie que toutes migrations s'appliquent sans erreur.
    """
    command.upgrade(alembic_config, "head")
    
    # Vérifier version finale
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert result[0] == '004_users_rbac'

def test_migration_chain_downgrade(alembic_config, test_engine):
    """
    Test downgrade: head → -1 → head
    Vérifie réversibilité migrations.
    """
    command.downgrade(alembic_config, "-1")
    
    # Vérifier version après downgrade
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert result[0] == '003_add_procurement_extensions'
    
    # Re-upgrade
    command.upgrade(alembic_config, "head")
    
    # Vérifier retour head
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert result[0] == '004_users_rbac'

def test_migration_003_creates_tables(test_engine):
    """
    Test spécifique migration 003: tables créées correctement.
    """
    with test_engine.connect() as conn:
        # Vérifier tables procurement créées
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('procurement_references', 'procurement_categories', 'purchase_categories', 'procurement_thresholds')
            ORDER BY table_name
        """)).fetchall()
        
        assert len(result) == 4
        assert result[0][0] == 'procurement_categories'
        assert result[1][0] == 'procurement_references'
        assert result[2][0] == 'procurement_thresholds'
        assert result[3][0] == 'purchase_categories'

def test_migration_003_seeds_data(test_engine):
    """
    Test seed data migration 003.
    """
    with test_engine.connect() as conn:
        # Vérifier 6 catégories procurement
        result = conn.execute(text("SELECT COUNT(*) FROM procurement_categories")).fetchone()
        assert result[0] == 6
        
        # Vérifier 10 catégories purchase (9 SCI + 1 generic)
        result = conn.execute(text("SELECT COUNT(*) FROM purchase_categories")).fetchone()
        assert result[0] == 10
        
        # Vérifier 3 seuils
        result = conn.execute(text("SELECT COUNT(*) FROM procurement_thresholds")).fetchone()
        assert result[0] == 3

def test_migration_003_boolean_types_correct(test_engine):
    """
    Test CRITIQUE: Vérifie que colonnes boolean utilisent TRUE/FALSE.
    Régression test pour incident 2026-02-13.
    """
    with test_engine.connect() as conn:
        # Vérifier requires_technical_eval est bien boolean TRUE
        result = conn.execute(text("""
            SELECT requires_technical_eval 
            FROM procurement_categories 
            WHERE code = 'EQUIPMED'
        """)).fetchone()
        assert result[0] == True  # Python bool, pas integer 1
        
        # Vérifier is_high_risk est bien boolean
        result = conn.execute(text("""
            SELECT is_high_risk 
            FROM purchase_categories 
            WHERE code = 'TRAVEL'
        """)).fetchone()
        assert result[0] == False  # Python bool, pas integer 0
```

**Total:** 5 tests, ~1h

**Coverage attendue:** alembic/env.py: 0% → 40% (tests migrations couvrent partiellement env.py)

---

## 🧮 Calcul Coverage Projections

### Avant (actuel):
```
src/auth.py: 0% (97 stmts missed)
src/auth_router.py: 0% (36 stmts)
src/couche_a/routers.py: 0% (106 stmts)
src/db.py: 51% (38 stmts missed)
src/upload_security.py: 0% (44 stmts)
alembic/env.py: 0% (34 stmts)

TOTAL: 41% (564/1377 covered, 813 missed)
```

### Après Phase 1-4 (projections):
```
src/auth.py: 75% (+73 stmts covered)
src/auth_router.py: 60% (+22 stmts)
src/couche_a/routers.py: 70% (+74 stmts)
src/db.py: 80% (+23 stmts)
src/upload_security.py: 80% (+35 stmts)
alembic/env.py: 40% (+14 stmts)

Total ajouté: +241 stmts covered
Nouveau coverage: 564 + 241 = 805/1377 = 58%
```

**Objectif 60%:** Nécessite +21 stmts supplémentaires
- Ajouter 2-3 tests edge cases auth ou routers
- OU augmenter coverage src/mapping/ (actuellement 32-60%)

---

## 📚 Structure Tests Finale

```
tests/
├── conftest.py (fixtures globales PostgreSQL) ← NOUVEAU
├── migrations/ ← NOUVEAU
│   └── test_migration_chain.py (5 tests)
├── test_auth_core.py ← NOUVEAU (10 tests)
├── test_db_core.py ← NOUVEAU (5 tests)
├── couche_a/
│   ├── conftest.py ← AMÉLIORER (fixtures case, user)
│   ├── test_routers.py ← AMÉLIORER (8 tests)
│   ├── test_endpoints.py (existant - débloquer)
│   └── test_migration.py (existant)
├── test_upload_security_core.py ← AMÉLIORER (7 tests)
├── test_resilience.py (existant - ✅ 97% coverage)
├── test_templates.py (existant - ✅ 99% coverage)
└── mapping/
    └── test_engine_smoke.py (existant - 2 tests)
```

**Total tests après plan:**
- Actuels: 11 tests fonctionnels + ~15 tests bloqués = ~26 tests
- Nouveaux: +35 tests (auth, db, routers, security, migrations)
- **Total final: ~61 tests**

---

## 🚀 Ordre d'Exécution Recommandé

### Jour 1 (4h): Infrastructure
- Setup `tests/conftest.py` (fixtures PostgreSQL)
- Tests `src/db.py` (5 tests - module fondation)
- Débloquer tests existants (DATABASE_URL fixtures)

### Jour 2 (6h): Auth & Security
- Tests `src/auth.py` (10 tests - critique)
- Tests `src/upload_security.py` (7 tests)

### Jour 3 (5h): Routers & Migrations
- Tests `src/couche_a/routers.py` (8 tests)
- Tests migrations (5 tests)

**Total:** 3 jours (15h) pour 60% coverage ✅

---

## 📊 CI Integration

### Mise à jour `.github/workflows/ci.yml`

```yaml
- name: Run tests with coverage
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
    PYTHONPATH: ${{ github.workspace }}
  run: |
    pytest tests/ -v --cov=src --cov=alembic --cov-report=term-missing --cov-fail-under=60
    # ↑ CI échoue si coverage < 60%

- name: Upload coverage report
  if: always()
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    fail_ci_if_error: false
```

---

## 🎯 Critères de Succès

- [ ] Coverage total ≥ 60%
- [ ] Tous modules critiques (auth, db, routers) ≥ 70%
- [ ] Tests migrations passent (upgrade/downgrade)
- [ ] CI verte avec enforcement coverage 60%
- [ ] Documentation tests à jour

---

## ⚠️ Risques & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| Tests lents (>5 min) | Moyenne | Moyen | Fixtures session-scoped, rollback trans |
| DATABASE_URL absent local | Haute | Bloquant | Doc setup PostgreSQL obligatoire |
| Tests flaky | Faible | Moyen | Isolation via rollback, pas de données partagées |
| Effort sous-estimé | Moyenne | Moyen | Buffer 20% (18h au lieu de 15h) |

---

## 📚 Références

- **Coverage docs**: https://pytest-cov.readthedocs.io/
- **Pytest fixtures**: https://docs.pytest.org/en/stable/fixture.html
- **Alembic testing**: https://alembic.sqlalchemy.org/en/latest/cookbook.html#test-current-database-revision-is-at-head-s
- **FastAPI testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

**Établi par:** Ingénieur CI/CD + Infrastructure + QA  
**Date:** 2026-02-13  
**Status:** PLAN PRÊT À EXÉCUTION
