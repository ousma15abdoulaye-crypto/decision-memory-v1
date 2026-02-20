# Lot A — Preuves (PR Description)

**Milestone**: M-EXTRACTION-CORRECTIONS (#4)  
**Date**: 2026-02-20  
**Règle**: Lot A terminé avant toute ligne de code.

---

## A0.0 — Pattern migrations Alembic

```text
002_add_couche_a.py
003_add_procurement_extensions.py
004_users_rbac.py
005_add_couche_b.py
006_criteria_types.py
007_add_scoring_tables.py
008_merge_heads.py
009_add_supplier_scoring_tables.py
009_supplier_scores_eliminations.py
010_enforce_append_only_audit.py
011_add_missing_schema.py
012_m_extraction_engine.py
013_add_m_extraction_engine_documents_columns.py
014_ensure_extraction_tables.py
caf949970819_merge_heads_for_single_alembic_revision_.py
```

**Pattern**: 0XX style dominant (002 → 014). Une migration hash (caf949970819) pour merge.  
**Décision**: Nouvelle migration = **015_** (suivre le style 0XX).

---

## A0.1 — Dernière révision Alembic

```text
Rev: 014_ensure_extraction_tables (head)
Revision ID: 014_ensure_extraction_tables
Revises: 013_m_extraction_docs
```

**down_revision** pour 015 = `014_ensure_extraction_tables`

---

## A0.2 — Chemins réels imports DB & auth

| Fonction           | Fichier               | Ligne |
|--------------------|------------------------|-------|
| `get_db_cursor`    | `src/db/connection.py` | 18    |
| `get_current_user` | `src/auth.py`          | 104   |

---

## A0.3 — Extensions DB

```sql
-- À exécuter si DB disponible :
-- psql $DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto','uuid-ossp');"
```

**État repo**: pgcrypto créé dans 012_m_extraction_engine. CI utilise pgcrypto.  
**Décision**: pgcrypto autorisé (déjà utilisé).

---

## A0.4 — Triggers existants sur extractions

```sql
-- À exécuter si DB disponible :
-- psql $DATABASE_URL -c "SELECT trigger_name FROM information_schema.triggers WHERE event_object_table='extractions';"
```

**État migrations**: Aucun trigger sur `extractions` dans 002–014. Trigger FSM uniquement sur `extraction_jobs`.  
**Décision**: Trigger immuabilité `extractions` autorisé (A0.5 vide + pas existant).

---

## A0.5 — UPDATE extractions dans le code

```bash
Get-ChildItem src/ -Recurse -Filter "*.py" | Select-String "UPDATE extractions"
```

**Résultat**: **Vide** (0 match).  
**Conséquence**: Trigger immuabilité sur `extractions` **autorisé** dans ce milestone.

---

## A0.6 — Fichier routes extractions

- Fichier: `src/api/routes/extractions.py`
- Lignes: **255** (< 400)
- **Décision**: Endpoints ajoutés dans ce fichier existant. Pas de nouveau fichier routes.

---

## A0.7 — main.py + src/api/main.py (BLOCAGE #1)

**Preuve grep extraction :**

```powershell
Get-Content main.py | Select-String "extraction"
Get-Content src/api/main.py | Select-String "extraction"
```

**Résultat — main.py :**
```
from src.api.routes.extractions import router as extraction_router
app.include_router(extraction_router)
```

**Résultat — src/api/main.py :**
```
from src.api.routes.extractions import router as extraction_router
app.include_router(extraction_router)
```

✅ **Router extraction inclus dans LES DEUX apps.** Aucune correction requise.
