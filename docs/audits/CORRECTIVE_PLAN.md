# PLAN DE CORRECTION — DMS V3.3.2
**Date :** 2026-02-18  
**Référence :** AUDIT_2026-02-18.md  
**Branche cible :** `fix/audit-urgent`

---

## OBJECTIF

Corriger les violations critiques identifiées dans l'audit pour rétablir la conformité avec la Constitution V3.3.2.

---

## ACTIONS CORRECTIVES

### FIX-001 : Implémenter tests invariants (INV-1 à INV-9)

**Priorité :** 🔴 Haute (Bloquant)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M-CI-INVARIANTS  
**Référence Constitution :** §2 Invariants

**Description :**
Créer les tests pour chaque invariant de la Constitution V3.3.2 dans `tests/invariants/`.

**Fichiers à créer :**
- `tests/invariants/test_inv_01_cognitive_load.py`
- `tests/invariants/test_inv_02_couche_a_primacy.py`
- `tests/invariants/test_inv_03_memory_non_prescriptive.py`
- `tests/invariants/test_inv_04_online_only.py`
- `tests/invariants/test_inv_05_ci_green.py`
- `tests/invariants/test_inv_06_append_only.py`
- `tests/invariants/test_inv_07_erp_agnostic.py`
- `tests/invariants/test_inv_08_survivability.py`
- `tests/invariants/test_inv_09_fidelity_neutrality.py`

**Critère de succès :**
- Tous les tests passent (`pytest tests/invariants/ -v`)
- Workflow `ci-invariants.yml` exécute les tests correctement
- Couverture minimale : chaque invariant testé avec au moins 3 cas

**Estimation :** 8h

---

### FIX-002 : Appliquer formatage Black sur code Python

**Priorité :** 🔴 Haute (Bloquant)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M-TESTS (qualité code)  
**Référence Constitution :** Standards qualité

**Description :**
Formater tout le code Python avec Black selon les standards du projet.

**Commandes à exécuter :**
```bash
black src tests
```

**Fichiers concernés :**
- Tous les fichiers `.py` dans `src/` et `tests/`

**Critère de succès :**
- `black --check src tests` passe sans erreur
- Ajouter gate CI dans `ci-main.yml` pour vérifier formatage

**Estimation :** 1h

---

### FIX-003 : Régénérer checksums freeze sous Linux

**Priorité :** 🔴 Haute (Bloquant)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** Freeze integrity  
**Référence Constitution :** Intégrité freeze

**Description :**
Régénérer les checksums SHA256 des fichiers freezés sous Linux (CI) pour éviter les différences CRLF/LF.

**Action :**
1. Créer workflow CI temporaire ou utiliser workflow existant
2. Exécuter `sha256sum docs/freeze/v3.3.2/*.md docs/freeze/v3.3.2/adrs/*.md > docs/freeze/v3.3.2/SHA256SUMS.txt`
3. Commiter le nouveau fichier

**Critère de succès :**
- `sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt` passe sous Linux
- Workflow `ci-freeze-integrity.yml` passe

**Estimation :** 30min

---

### FIX-004 : Ajouter contraintes append-only sur tables d'audit

**Priorité :** 🟠 Moyenne (Majeur)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M4A-F (Sécurité)  
**Référence Constitution :** §8 Append-only

**Description :**
Créer migration Alembic pour révoquer DELETE et UPDATE sur les tables d'audit.

**Fichier à créer :**
- `alembic/versions/010_enforce_append_only_audit.py`

**Contenu migration :**
```python
"""Enforce append-only constraints on audit tables.

Revision ID: 010_enforce_append_only_audit
Revises: 009_supplier_scores_eliminations
Create Date: 2026-02-18

Constitution V3.3.2 §8: Tables d'audit doivent être append-only.
"""
from alembic import op
from sqlalchemy import text

revision = '010_enforce_append_only_audit'
down_revision = '009_supplier_scores_eliminations'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    bind.execute(text("""
        REVOKE DELETE, UPDATE ON audits FROM PUBLIC;
        REVOKE DELETE, UPDATE ON market_signals FROM PUBLIC;
        REVOKE DELETE, UPDATE ON memory_entries FROM PUBLIC;
    """))

def downgrade():
    bind = op.get_bind()
    bind.execute(text("""
        GRANT DELETE, UPDATE ON audits TO PUBLIC;
        GRANT DELETE, UPDATE ON market_signals TO PUBLIC;
        GRANT DELETE, UPDATE ON memory_entries TO PUBLIC;
    """))
```

**Critère de succès :**
- Migration s'exécute sans erreur (`alembic upgrade head`)
- Tentative DELETE/UPDATE sur tables d'audit échoue avec erreur PostgreSQL
- Tests d'intégration vérifient l'append-only

**Estimation :** 2h

---

### FIX-005 : Consolider workflows CI

**Priorité :** 🟠 Moyenne (Majeur)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M-CI-INVARIANTS  
**Référence Constitution :** Optimisation CI

**Description :**
Supprimer workflow redondant `ci.yml` et conserver `ci-main.yml` comme workflow principal.

**Action :**
1. Supprimer `.github/workflows/ci.yml`
2. Vérifier que `ci-main.yml` couvre tous les besoins

**Critère de succès :**
- Un seul workflow principal pour tests/lint
- Pas de duplication de jobs
- CI toujours fonctionnelle

**Estimation :** 2h

---

### FIX-006 : Configurer Ruff pour linting

**Priorité :** 🟡 Basse (Mineur)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M-TESTS (qualité code)  
**Référence Constitution :** Standards qualité

**Description :**
Créer configuration Ruff et ajouter gate CI pour linting automatique.

**Fichier à créer :**
- `pyproject.toml` (ou `.ruff.toml`)

**Configuration recommandée :**
```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = []

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

**Critère de succès :**
- `ruff check src tests` passe sans erreur
- Gate CI ajouté dans `ci-main.yml`

**Estimation :** 1h

---

### FIX-007 : Nettoyer code mort (imports/variables non utilisés)

**Priorité :** 🟡 Basse (Mineur)  
**Responsable :** Lead Développeur Senior  
**Milestone concerné :** M-TESTS (qualité code)  
**Référence Constitution :** Standards qualité

**Description :**
Identifier et supprimer les imports et variables non utilisés dans le code.

**Commandes à exécuter :**
```bash
ruff check src --select F401,F841 --output-format=json
```

**Critère de succès :**
- Aucun import/variable non utilisé détecté
- Code plus propre et maintenable

**Estimation :** 2h

---

## ORDRE D'EXÉCUTION

### Phase 1 : Correctifs bloquants (48h)

1. **FIX-002** : Formatage Black (1h) — **DÉMARRAGE IMMÉDIAT**
2. **FIX-003** : Régénérer checksums (30min) — **DÉMARRAGE IMMÉDIAT**
3. **FIX-001** : Tests invariants (8h) — **EN PARALLÈLE**

### Phase 2 : Correctifs majeurs (1 semaine)

4. **FIX-004** : Contraintes append-only (2h)
5. **FIX-005** : Consolider CI (2h)

### Phase 3 : Correctifs mineurs (2 semaines)

6. **FIX-006** : Configurer Ruff (1h)
7. **FIX-007** : Nettoyer code mort (2h)

---

## VALIDATION

Chaque correctif doit être :
1. ✅ Testé localement
2. ✅ Validé par CI verte
3. ✅ Documenté dans commit message (référence FIX-XXX)
4. ✅ Reviewé avant merge dans `main`

**Critère de succès global :**
- ✅ Tous les tests passent (`pytest tests/ -v`)
- ✅ CI verte sur branche `fix/audit-urgent`
- ✅ Formatage Black vérifié (`black --check`)
- ✅ Freeze integrity vérifiée (`sha256sum -c`)
- ✅ Tests invariants présents et passants

---

**Signature :** Lead Développeur Senior  
**Date :** 2026-02-18
