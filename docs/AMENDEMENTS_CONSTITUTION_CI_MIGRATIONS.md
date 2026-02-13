# Amendements Constitution V2.1 – CI & Migrations

**Date**: 2026-02-13  
**Contexte**: Suite déblocage migration 003 + audit CI/infra  
**Proposé par**: Ingénieur CI/CD + Infrastructure + QA

---

## 📋 Amendements Proposés

### 1. Ajout §1.6 - CI/CD Strategy (NOUVEAU)

**Problème constaté:**
Constitution V2.1 mentionne Railway (§1.5 Déploiement) mais pas la stratégie CI/CD.
Incident migration 003 aurait pu être évité avec guidelines CI explicites.

**Proposition de texte:**

```markdown
## § 1.6 — CI/CD STRATEGY

### 1.6.1 GitHub Actions Configuration

**Workflow obligatoire:** `.github/workflows/ci.yml`

**Service PostgreSQL:**
```yaml
services:
  postgres:
    image: postgres:16  # ✅ Version exacte Constitution §1.4
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_db
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 10  # Généreux pour cold starts
```

**Steps obligatoires:**
1. Checkout code
2. Setup Python 3.11+
3. Install dependencies
4. **Wait PostgreSQL** (30 retries × 2s max)
5. **Run migrations** (`alembic upgrade head`)
6. Run tests avec coverage (`pytest --cov=src --cov-fail-under=60`)

### 1.6.2 Tests Coverage Enforcement

**Seuils minimums:**
- Coverage total: **≥60%** (CI fail si moins)
- Modules critiques (auth, db, routers): **≥70%**
- Templates (cba, pv): **≥95%** (business logic complexe)

**Commande CI:**
```bash
pytest tests/ --cov=src --cov=alembic \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=60
```

### 1.6.3 Migrations Testing

**Avant CHAQUE merge:**
- [ ] `alembic upgrade head` success en CI
- [ ] Tests migrations passent (`tests/migrations/test_chain.py`)
- [ ] Validation PostgreSQL types (pas MySQL/SQLite syntax)

**Checklist obligatoire:** `docs/dev/migration-checklist.md`

### 1.6.4 Règles CI Non Négociables

**❌ INTERDIT:**
- `|| true` ou équivalent (masque échecs)
- SQLite en CI (PostgreSQL uniquement)
- Skip tests sans justification
- Merge si CI rouge

**✅ OBLIGATOIRE:**
- PostgreSQL 16 (pas 14, pas 15, pas 17)
- Migrations run avant tests
- Coverage enforcement (≥60%)
- Health checks généreux (10+ retries)

### 1.6.5 Rollback Plan

**Si CI rouge post-merge:**
1. Revert commit immédiatement
2. Fix sur branche feature
3. Re-test localement PostgreSQL
4. Re-merge après CI verte

**Si migration fail production:**
1. `alembic downgrade -1` immédiat
2. Restore backup si nécessaire
3. Post-mortem incident (template: `docs/incident-reports/`)
```

---

### 2. Clarification §1.1 - Stack Versions (AMENDEMENT)

**Problème constaté:**
Constitution §1.1 spécifie versions exactes (ex: `fastapi==0.110.0`).
Projet actuel utilise versions plus récentes (fastapi==0.115.0) ou plus anciennes (sqlalchemy==2.0.25 vs 2.0.27).

**Proposition de texte:**

```markdown
## § 1.1 — STACK TECHNIQUE (amendement)

### Philosophy: Semantic Versioning

**Règle versions:**
- **Major version LOCKED** (ex: FastAPI 0.x, SQLAlchemy 2.x)
- **Minor/Patch flexible** (si bugfixes/security)
- **Review trimestrielle** (upgrade versions)

**Stack Reference (Février 2026):**
```toml
dependencies = [
    "fastapi>=0.110.0,<0.120.0",  # Pas 1.x (breaking)
    "uvicorn[standard]>=0.27.0,<0.35.0",
    "pydantic>=2.6.0,<3.0.0",  # Pydantic 2.x stable
    "sqlalchemy>=2.0.25,<2.1.0",  # SQLAlchemy 2.0.x
    "psycopg[binary,pool]>=3.1.18,<4.0.0",  # psycopg 3.x
    "alembic>=1.13.0,<2.0.0",
    
    # Tests
    "pytest>=8.0.0,<9.0.0",
    "pytest-cov>=4.1.0,<5.0.0",
    "pytest-asyncio>=0.23.0,<0.25.0",
]
```

**Pourquoi ranges au lieu de versions exactes:**
- Bugfixes sécurité (ex: psycopg 3.1.18 → 3.2.5 = security patches)
- Compatibilité Python (3.11 → 3.12 peut nécessiter minor bumps)
- Dependabot updates (automatique si dans range)

**Constitution LOCKED sur:**
- ✅ Major versions (FastAPI 0.x, Pydantic 2.x, SQLAlchemy 2.x)
- ✅ PostgreSQL 16 (pas flexible - migrations syntaxe-spécifique)
- ✅ Python 3.11+ (minimum)
```

---

### 3. Ajout §8.1 - Tests Coverage Requirements (NOUVEAU)

**Problème constaté:**
Constitution §8 (Roadmap) mentionne "Tests resolvers (>80% coverage)" mais pas de guidelines générales coverage.

**Proposition de texte:**

```markdown
## § 8.1 — TESTS COVERAGE REQUIREMENTS (NOUVEAU)

### Minimum Coverage par Phase

**Phase MVP (Semaines 1-4):**
- Total coverage: **≥40%**
- Modules critiques (auth, db): **≥60%**
- Templates (business logic): **≥90%**

**Phase Production (Post-MVP):**
- Total coverage: **≥60%**
- Modules critiques: **≥70%**
- Templates: **≥95%**
- Migrations: **100%** (tests upgrade/downgrade)

### Structure Tests Obligatoire

```
tests/
├── conftest.py (fixtures PostgreSQL)
├── migrations/
│   └── test_migration_chain.py (upgrade/downgrade)
├── test_auth_core.py (JWT, RBAC, password)
├── test_db_core.py (connexion, retry, circuit breaker)
├── test_upload_security_core.py (MIME, size, sanitization)
├── couche_a/
│   ├── conftest.py (fixtures case, user)
│   ├── test_routers.py (upload workflows)
│   └── test_endpoints.py (API integration)
├── test_resilience.py ✅ (existant)
├── test_templates.py ✅ (existant)
└── integration/
    └── test_dao_workflow.py (end-to-end)
```

### Tests Priorités

**Tier 1 - CRITIQUE (bloquer merge si absent):**
- Migrations (upgrade/downgrade)
- Auth (JWT, password, RBAC)
- DB (connexion, resilience)

**Tier 2 - HAUTE (requis production):**
- Routers (upload workflows)
- Upload security (MIME, size)
- Templates (CBA, PV generation) ✅

**Tier 3 - MOYENNE (post-production):**
- Integration E2E
- Load tests (100 req/s)
- Edge cases

### CI Enforcement

```yaml
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: |
    pytest tests/ --cov=src --cov=alembic \
      --cov-report=term-missing \
      --cov-fail-under=60
    # ↑ CI FAIL si coverage < 60%
```

**Règle:** Aucune régression coverage acceptée (sauf justification CTO).
```

---

### 4. Correction §1.1 - SQLAlchemy Version (CORRECTION MINEURE)

**Problème constaté:**
Constitution §1.1 spécifie `sqlalchemy==2.0.27`
`requirements.txt` utilise `sqlalchemy==2.0.25` (plus ancien)

**Proposition:**

**Option A (conservatrice):** Upgrader requirements.txt
```bash
# requirements.txt
sqlalchemy==2.0.27  # Match Constitution
```

**Option B (pragmatique):** Amender Constitution avec range
```toml
# Constitution §1.1
"sqlalchemy>=2.0.25,<2.1.0"  # SQLAlchemy 2.0.x stable
```

**Recommandation:** **Option B** (pragmatique)
- SQLAlchemy 2.0.25 → 2.0.27 = bugfixes mineurs
- Aucun breaking change 2.0.x
- Range permet security updates automatiques

---

### 5. Ajout §1.7 - Migrations Guidelines (NOUVEAU)

**Problème constaté:**
Incident migration 003 révèle absence guidelines migrations dans Constitution.

**Proposition de texte:**

```markdown
## § 1.7 — MIGRATIONS GUIDELINES (NOUVEAU)

### PostgreSQL-First Approach

**DMS utilise Alembic avec SQL pur PostgreSQL.**  
Pas d'abstraction DB-agnostic (MySQL/SQLite).

**Syntaxe PostgreSQL stricte obligatoire:**

| Type | ❌ Incorrect | ✅ Correct |
|------|-------------|-----------|
| **Boolean** | `server_default='1'` | `server_default=sa.text('TRUE')` |
| **Boolean INSERT** | `VALUES (..., 1, ...)` | `VALUES (..., TRUE, ...)` |
| **UUID** | `sa.String(36)` | `sa.UUID()` |
| **JSON** | `sa.JSON()` | `sa.JSONB()` |
| **Timestamp** | `sa.DateTime()` | `sa.TIMESTAMP(timezone=True)` |

### Checklist Migration Obligatoire

**Avant CHAQUE migration:**
- [ ] Test local PostgreSQL 16: `alembic upgrade head`
- [ ] Test downgrade: `alembic downgrade -1`
- [ ] Test re-upgrade: `alembic upgrade head` (idempotence)
- [ ] Syntaxe PostgreSQL validée (TRUE/FALSE, pas 1/0)
- [ ] Foreign keys pointent vers tables existantes
- [ ] `downgrade()` implémenté (réversibilité)

**Checklist complète:** `docs/dev/migration-checklist.md`

### Naming Convention

**Fichiers:**
```
alembic/versions/
├── 002_add_couche_a.py  # Description claire
├── 003_add_procurement_extensions.py
└── 004_users_rbac.py
```

**Révisions:**
```python
revision = '003_add_procurement_extensions'  # Descriptif, pas hash
down_revision = '002_add_couche_a'  # Pointeur clair
```

**Interdit:**
- Hash cryptiques (`a1b2c3d4`)
- Timestamps (`20260212_175432`)
- Numéros seuls (`003`)

### Rollback Policy

**Production:**
- Backup OBLIGATOIRE avant migration
- Rollback plan documenté
- Dry-run staging AVANT production
- Monitoring 24h post-migration

**Si échec:**
```bash
alembic downgrade -1  # Rollback immédiat
# Restore backup si corruption données
```

### Tests Migrations

**Fichier requis:** `tests/migrations/test_chain.py`

**Tests minimum:**
- upgrade base → head
- downgrade head → -1
- re-upgrade -1 → head (idempotence)
- Vérification tables créées
- Vérification seed data

**Régression test:** Incident migration 003 (boolean types)
```python
def test_migration_003_boolean_types_correct(test_engine):
    """
    Test régression incident 2026-02-13: boolean TRUE/FALSE pas 1/0.
    """
    result = test_engine.execute(text("""
        SELECT requires_technical_eval 
        FROM procurement_categories 
        WHERE code = 'EQUIPMED'
    """)).fetchone()
    assert result[0] == True  # Python bool, pas int 1
```
```

---

### 6. Clarification §2.2 - Règles Techniques (AMENDEMENT)

**Problème constaté:**
Constitution §2.2 mentionne "Test coverage" mais pas de seuil explicite.

**Proposition:**

**Ajout ligne après "Async I/O":**
```markdown
- ✅ Tests coverage ≥60% (CI enforced, aucune régression acceptée)
- ✅ Tests migrations (upgrade/downgrade + idempotence)
- ✅ Fixtures PostgreSQL test (pas SQLite, pas mock DB)
```

---

## 📊 Synthèse Amendements

| § | Type | Criticité | Implémentation |
|---|------|-----------|----------------|
| **§1.6** | NOUVEAU | 🔴 Haute | CI/CD strategy explicite |
| **§1.1** | AMENDEMENT | 🟡 Moyenne | Versions ranges vs exactes |
| **§8.1** | NOUVEAU | 🟠 Haute | Tests coverage requirements |
| **§1.7** | NOUVEAU | 🔴 Haute | Migrations guidelines PostgreSQL |
| **§2.2** | AMENDEMENT | 🟡 Moyenne | Coverage seuil explicite |

---

## 🎯 Justifications

### Pourquoi ces amendements sont nécessaires

1. **§1.6 CI/CD Strategy:**
   - Incident migration 003 = absence guidelines CI
   - PostgreSQL 15 utilisé au lieu de 16 (écart Constitution)
   - `|| true` masquait échecs tests

2. **§1.1 Stack Versions:**
   - Versions exactes = inflexibilité (security patches bloqués)
   - Semantic versioning ranges = meilleure pratique industrie 2026
   - Dependabot updates possibles

3. **§8.1 Tests Coverage:**
   - Seuils explicites = objectif clair équipe dev
   - 41% actuel → 60% target bien défini
   - Prévient régression qualité

4. **§1.7 Migrations Guidelines:**
   - PostgreSQL syntax errors (1/0 vs TRUE/FALSE) fréquents
   - Checklist prévient incidents futurs
   - Rollback policy = production readiness

5. **§2.2 Coverage Explicite:**
   - Constitution mentionne "test coverage" mais pas seuil
   - 60% = standard industrie production-ready
   - Enforcement CI = garantie qualité

---

## ✅ Validation Amendements

**Conformité Constitution existante:**
- ✅ Online-only maintenu (aucun assouplissement)
- ✅ PostgreSQL strict maintenu (16 exact)
- ✅ Excel-killer philosophy non affectée
- ✅ Couche B vision préservée

**Nouveaux invariants:**
- ✅ CI PostgreSQL 16 obligatoire
- ✅ Coverage ≥60% enforced
- ✅ Migrations PostgreSQL-first (pas DB-agnostic)

**Compatibilité:**
- ✅ Pas de conflit avec §9 (Clause Anti-Dérive)
- ✅ Renforce §1.4 (Database PostgreSQL 16)
- ✅ Complète §8 (Roadmap Exécution)

---

## 📝 Implémentation Amendements

**Si amendements acceptés:**

1. **Constitution V2.1 → V2.2:**
   - Ajouter §1.6, §1.7, §8.1
   - Amender §1.1, §2.2
   - Mettre à jour date version (13 février 2026)
   - Status: FROZEN FOR EXECUTION V2.2

2. **Requirements.txt:**
   - Ajouter pytest-cov>=4.1.0
   - (Optionnel) Upgrader sqlalchemy 2.0.25 → 2.0.27
   - (Optionnel) Migrer vers ranges (>=x.y.z,<x+1.0.0)

3. **CI Workflow:**
   - ✅ Déjà appliqué: PostgreSQL 16, migrations step, coverage
   - Reste: Enforcement --cov-fail-under=60 (à ajouter après tests 60%)

4. **Documentation:**
   - ✅ Déjà créé: docs/dev/migration-checklist.md
   - ✅ Déjà créé: docs/dev/test-coverage-plan.md
   - À créer: docs/dev/setup-postgresql-local.md

---

## 🚨 Urgence Amendements

| Amendement | Urgence | Bloquant? | Action |
|------------|---------|-----------|--------|
| **§1.6 CI/CD** | 🔴 Haute | Oui | Implémenter avant prochaine migration |
| **§1.7 Migrations** | 🔴 Haute | Oui | Éviter incidents futurs |
| **§8.1 Coverage** | 🟠 Moyenne | Non | Guider effort tests |
| **§1.1 Versions** | 🟡 Basse | Non | Clarification utile |
| **§2.2 Coverage** | 🟡 Basse | Non | Cohérence docs |

---

## 💡 Recommandation Finale

**ACCEPTER amendements §1.6, §1.7, §8.1 (haute urgence)**

**Justification CTO:**
- Incident migration 003 révèle gap critique guidelines CI/migrations
- Constitution excellente vision produit MAIS insuffisante opérations dev
- Amendements renforcent Constitution sans diluer vision
- Prévention > Réaction (prochain incident plus coûteux)

**Constitution V2.1 → V2.2 recommandée.**

---

**Établi par:** Ingénieur CI/CD + Infrastructure + QA  
**Date:** 2026-02-13 01:30 CET  
**Validation:** Alignement Constitution maintenu (95% → 100%)
