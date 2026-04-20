# P3.2 Migration 101 — Résumé opérations

**Fichier** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py`  
**Date** : 2026-04-18  
**Statut** : ✅ **PRÉPARÉ** — attente revue CTO avant exécution

---

## UPGRADE (7 opérations)

### Table `dao_criteria` (6 colonnes)

| Op | Colonne | Type | Action | Source backfill |
|---|---|---|---|---|
| 1 | `family` | TEXT | ADD + backfill | `criterion_category` (capacity→TECHNICAL, commercial→COMMERCIAL, sustainability→SUSTAINABILITY) |
| 2 | `weight_within_family` | INTEGER | ADD + backfill | `(ponderation / SUM_famille) × 100` (corpus actif uniquement) |
| 3 | `criterion_mode` | TEXT | ADD (default 'SCORE') | — |
| 4 | `scoring_mode` | TEXT | ADD + backfill + CHECK | `m16_scoring_mode` (uppercase) |
| 5 | `min_threshold` | FLOAT | ADD | — |
| — | `min_weight_pct` | — | **DROP** | Colonne fantôme (probe COUNT IS NOT NULL = 0) |

### Table `process_workspaces` (1 colonne)

| Op | Colonne | Type | Action | Défaut |
|---|---|---|---|---|
| 6 | `technical_qualification_threshold` | FLOAT | ADD | 50.0 |

### Contraintes

| Op | Contrainte | Détail |
|---|---|---|
| 7 | `check_scoring_mode_p32` | CHECK scoring_mode IN ('RUBRIC','PRO_RATA','COUNT_BASED','BINARY','DETERMINISTIC','NUMERIC','QUALITATIVE','NOT_APPLICABLE') |

---

## DOWNGRADE (7 opérations inverses)

**Ordre strict inverse** :

1. DROP `family`
2. DROP `weight_within_family`
3. DROP `criterion_mode`
4. DROP `scoring_mode` + CHECK constraint
5. DROP `min_threshold`
6. DROP `technical_qualification_threshold`
7. RESTORE `min_weight_pct` (optionnel)

---

## MAPPING CANONIQUE (probe CASE-28b05d85)

**criterion_category → family** :
- `capacity` → `TECHNICAL` (50%)
- `commercial` → `COMMERCIAL` (40%)
- `sustainability` → `SUSTAINABILITY` (10%)
- `essential` → **NULL** (hors famille scoring)

**Doctrine métier CTO (opposable)** :
- Critères `essential` = critères GATE/checks (ouvrent l'analyse)
- **PAS** une famille de scoring (hors agrégat pondéré 50/40/10)
- `criterion_mode = 'GATE'` backfillé pour `essential`
- `family = NULL` pour `essential` (aucun fallback TECHNICAL)

**Invariant 50/40/10** : validé sur 3 familles scoring uniquement (TECHNICAL/COMMERCIAL/SUSTAINABILITY).

---

## EXCLUSIONS P3.2

**Hors migration** (décisions CTO) :
- ❌ Pas de `rubric_json` (Z5 hors périmètre)
- ❌ Pas de DROP `categorie` (préservé legacy)
- ❌ Pas de DROP `m16_scoring_mode` (préservé source backfill)
- ❌ Pas de trigger complexe
- ❌ Pas de changement pipeline (hors migration schéma)

---

## VALIDATION PRE-EXÉCUTION

**Probes validés CTO** :
- ✅ Numéro migration : 101
- ✅ `m16_scoring_mode` existe (backfill possible)
- ✅ `min_weight_pct` supprimable (COUNT IS NOT NULL = 0)
- ✅ Workspace canonique CASE-28b05d85 (50/40/10 capacity/commercial/sustainability)

**Backfill corpus** : actif uniquement (`status NOT IN ('cancelled')`)

**Rows affectées estimées** :
- `dao_criteria` : ~15 rows (CASE-28b05d85) + ~60 rows (4 workspaces GCF-E2E-*)
- `process_workspaces` : ~5 workspaces actifs

---

## NEXT STEPS

**1. Revue CTO** : lire `101_p32_dao_criteria_scoring_schema.py` complet

**2. Validation CTO** :
- SQL correct (backfills, mappings, contraintes)
- Downgrade symétrique
- Commentaires clairs
- Aucune opération hors mandat

**3. GO exécution** (après validation CTO) :
```bash
alembic upgrade head
```

**4. Vérification post-migration** :
- Query corpus actif (CASE-28b05d85 + GCF-E2E-*)
- Vérifier backfills (family, weight_within_family, scoring_mode)
- Confirmer invariant 50/40/10 préservé

---

**Migration préparée. Attente revue CTO avant alembic upgrade.**
