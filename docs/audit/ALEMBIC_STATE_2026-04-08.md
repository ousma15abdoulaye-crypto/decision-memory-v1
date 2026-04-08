# Alembic State — Audit Due Diligence 2026-04-08

## Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Migrations trackées | 108 |
| Schéma de nommage #1 | Numérique séquentiel : `002_` → `086_` |
| Schéma de nommage #2 | Milestone-based : `m4_` → `m7_7_` |
| Merge-heads historiques | 2 (`008_merge_heads.py`, `784a8b003d2d_merge_heads_020_and_022.py`) |
| CI single-head check | Oui (ci-main.yml — bloquant) |

## Anomalies constatées

### Numérotation dupliquée (5 occurrences)

| Préfixe | Fichiers |
|---------|----------|
| `009_` | `009_add_supplier_scoring_tables.py` / `009_supplier_scores_eliminations.py` |
| `040_` | `040_geo_master_mali.py` / `040_mercuriale_ingest.py` |
| `042_` | `042_market_surveys.py` / `042_vendor_fixes.py` |
| `043_` | `043_market_signals_v11.py` / `043_vendor_activity_badge.py` |
| `046_` | `046_imc_category_item_map.py` / `046b_imc_map_fix_restrict_indexes.py` |

Ces doublons n'empêchent pas le fonctionnement car Alembic résout la chaîne via
`revision` / `down_revision`, pas via le nom de fichier. Mais ils nuisent à la
lisibilité et compliquent le debugging.

### Migrations "fix" (correctifs de migrations précédentes)

| Migration | Corrige |
|-----------|---------|
| `016_fix_015_views_triggers.py` | 015 |
| `018_fix_alembic_heads.py` | Multi-head |
| `784a8b003d2d_merge_heads_020_and_022.py` | Multi-head |
| `fix_alembic_version_017_to_018.py` (scripts/) | Version bump |

4 migrations de type "fix" sur 108 (3.7%) — acceptable mais signe de précipitation
historique.

### Deux conventions de nommage coexistantes

- **Numérique** (`002_` → `086_`) : utilisé pour les migrations structurelles
- **Milestone** (`m4_` → `m7_7_`) : utilisé pour les patches milestone-specific

Pas de conflit technique mais la convention numérique est à privilégier pour la
lisibilité chronologique.

## Recommandations

### Court terme (sans mandat Alembic)
- **Ne rien toucher** — respect strict de RÈGLE-12 (dms-core)
- Maintenir le guard CI single-head
- Documenter toute nouvelle migration avec slug descriptif

### Moyen terme (mandat CTO requis)
1. **Squash** les migrations 002→050 en une seule migration "baseline"
   - Snapshot du schéma actuel post-050
   - Nouveau point de départ pour alembic
   - Gain : ~48 fichiers en moins, chaîne simplifiée
2. **Unifier** la convention de nommage sur le format `NNN_slug.py`
3. **Éliminer** les doublons de numérotation

### Long terme (post-M16)
- Migration vers un schéma baseline-only (un seul fichier = état actuel)
- Cleanup des migrations m4_→m7_ vers le schéma numérique unifié

## Règles en vigueur

- `alembic/versions/` : **JAMAIS** sans mandat dédié (CLAUDE.md, dms-core)
- `autogenerate` : **INTERDIT** (RÈGLE-12)
- `upgrade()` **et** `downgrade()` obligatoires
- Max ~3 tables créées/modifiées par migration
