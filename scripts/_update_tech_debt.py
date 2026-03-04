"""Update TECHNICAL_DEBT.md for M5-CLEANUP-A mandate."""
from pathlib import Path

TD = Path("TECHNICAL_DEBT.md")
content = TD.read_text(encoding="utf-8")

# ── 1. TD-005 heading ─────────────────────────────────────────────────────────
content = content.replace(
    "### TD-005 · DATABASE_URL évalué à l'import module — ACTIF · planifié Phase 1",
    "### TD-005 · lazy init DATABASE_URL — FERMÉE (réelle · 2026-03-03)",
)

# ── 2. TD-005 status row ──────────────────────────────────────────────────────
content = content.replace(
    "||| Statut | **ACTIF · Phase 1 M5** |",
    "||| Statut | **FERMÉE (réelle · 2026-03-03)** |",
    # only first occurrence (TD-005 section)
)

# ── 3. TD-005 fichier row ─────────────────────────────────────────────────────
content = content.replace(
    "||| Fichier | `src/db/core.py` ligne 42 |\n||| Ref ADR | ADR-M5-PRE-001 § D1.1 |",
    "||| Fichiers | `src/db/core.py` · `src/db/__init__.py` |\n||| Ref ADR | ADR-M5-PRE-001 § D1.1 |",
)

# ── 4. TD-005 severity row (only in TD-005) ───────────────────────────────────
# We replace the specific block between the heading and the problem block
OLD_BLOCK = """||| Sévérité | Haute |
||| Fichiers | `src/db/core.py` · `src/db/__init__.py` |
||| Ref ADR | ADR-M5-PRE-001 § D1.1 |

**Problème :**
```python
_DATABASE_URL = _get_database_url()  # ligne 42 — exécuté à l'import
```
Tout environnement sans `DATABASE_URL` (build CI sans DB, test unitaire pur)
plante à l'import du module. Couplage startup/runtime inacceptable.

**Solution :**
Lazy init via `_get_or_init_db_url()` avec cache `_DB_URL_CACHE`.
L'évaluation se fait au premier appel `get_connection()`, pas à l'import.

**Résolution :** Lazy init `_get_or_init_db_url()` + `_DB_URL_CACHE`. Commit bb3aa09. 726 passed CI."""

NEW_BLOCK = """||| Sévérité | Haute · RÉSOLUE |
||| Fichiers | `src/db/core.py` · `src/db/__init__.py` |
||| Ref ADR | ADR-M5-PRE-001 § D1.1 |

**Résolu :**
- `src/db/__init__.py` : appel eager `_get_database_url()` supprimé · M5-CLEANUP-A
- `src/db/core.py` : `_get_or_init_db_url()` · seul point d'entrée · lazy init

**Note :** précédemment fermée de façon incorrecte (core.py seulement).
`__init__.py` bypassait le cache via appel direct `_get_database_url()` à l'import.
Corrigé M5-CLEANUP-A · `python -c "import src.db"` → OK sans DATABASE_URL."""

content = content.replace(OLD_BLOCK, NEW_BLOCK)

# ── 5. Rename existing TD-011 → TD-015 (append-only market_signals, M5-FIX) ─
content = content.replace(
    "## TD-011 · Protection append-only market_signals incompatible avec FK locale",
    "## TD-015 · Protection append-only market_signals incompatible avec FK locale",
)
content = content.replace(
    "||| Statut | **ACTIVE** |\n||| Sévérité | Moyenne |\n||| Découverte | Sprint M5-FIX",
    "||| Statut | **ACTIVE** |\n||| Sévérité | Moyenne |\n||| Découverte | Sprint M5-FIX",
)

# ── 6. Rename existing TD-012 → TD-016 (chk_vendor_id_format, M5-FIX) ───────
content = content.replace(
    "## TD-012 · Contrainte chk_vendor_id_format limitée à 4 chiffres (9999 vendors/région max)",
    "## TD-016 · Contrainte chk_vendor_id_format limitée à 4 chiffres (9999 vendors/région max)",
)

# ── 7. Add new TDs 011-014 after TD-010 section ───────────────────────────────
NEW_TDS = """
---

## TD-011 · extract_dao_criteria_structured stub

| Attribut | Valeur |
|---|---|
| Statut | **OUVERTE · TRACÉE** |
| Sévérité | Haute |
| Fichier | `src/api/analysis.py` |
| Échéance | M10B Gateway Calibration |

**Action :** 501 explicite posé en M5-CLEANUP-A · implémentation complète M10B.
LlamaParse + Mistral OCR + instructor structured output.
Commentaire `CRITICAL BUG` supprimé · HTTPException 501 retourné explicitement.

**Propriétaire :** CTO · ouvert · M10B.

---

## TD-012 · SELECT * persistant hors vendors

| Attribut | Valeur |
|---|---|
| Statut | **OUVERTE** |
| Sévérité | Modérée |
| Modules | `committee/service.py` · `api/analysis.py` · `api/cases.py` · `geo/repository.py` · `core/dependencies.py` |
| Échéance | traité module par module dans chaque milestone concerné |

**Règle :** toute colonne sensible ajoutée en M5+ = exclusion explicite dans le SELECT.
Risque : exposition automatique de nouvelles colonnes via API sans décision explicite.

**Propriétaire :** CTO · suivi milestone par milestone.

---

## TD-013 · SLA-B LlamaParse + Mistral OCR non connectés

| Attribut | Valeur |
|---|---|
| Statut | **OUVERTE** |
| Sévérité | Haute |
| Échéance | M10A-SLA-PROVIDERS (sprint dédié · après M5 Mercuriale) |

**Action :** providers lazy key management · `get_available_providers()`.
Sprint séparé · ne pas mélanger avec data ingest M5.
Providers actuels : stubs non connectés · retournent données statiques.

**Propriétaire :** CTO · M10A.

---

## TD-014 · Migration 017 supprimée · script fix manuel

| Attribut | Valeur |
|---|---|
| Statut | **OUVERTE · RISQUE FAIBLE** |
| Script | `scripts/fix_alembic_version_017_to_018.py` |
| Échéance | documenter dans RUNBOOK.md avant M5 |

**Action :** ajouter section RUNBOOK.md · DATABASE_URL requis · exécution manuelle.
Environnements concernés : toute DB ayant sauté la migration 017.

**Propriétaire :** CTO · avant merge M5 Mercuriale.

"""

# Insert new TDs after the TD-010 closing block
AFTER_TD010 = "**Propriétaire :** CTO · FERMÉE.\n\n---\n\n## TD-011 · Protection"
content = content.replace(
    AFTER_TD010,
    "**Propriétaire :** CTO · FERMÉE.\n" + NEW_TDS + "\n---\n\n## TD-015 · Protection",
)

TD.write_text(content, encoding="utf-8")
print("TECHNICAL_DEBT.md updated — TD-005 closed, TD-011/012/013/014 added, TD-015/016 renamed")
