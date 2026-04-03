# H0.5 — Table Health Report

**Date** : 2026-04-03
**Horizon** : H0 — Fondations
**Référence** : DMS_VIVANT_V2_FREEZE §5.5

## Objectif

Auditer les tables semi-mortes identifiées par la sonde profonde V2 :
`decision_snapshots`, `analysis_summaries`, `memory_entries`.

## Résultats

### decision_snapshots (migration 029)

| Critère | Résultat |
|---|---|
| Writer actif | Oui — `committee_service.seal_committee_decision()` |
| Append-only | Oui — trigger en place |
| case_id nullable | Non — `NOT NULL` dans migration |
| Statut | **SAIN** — table activement alimentée par le committee service |

### analysis_summaries (migration 035)

| Critère | Résultat |
|---|---|
| Writer actif | Oui — `pipeline_analysis._persist_summary()` |
| pipeline_run_id | Nullable — `NULL` pour les summaries bloqués (`_build_and_persist_blocked`) |
| Orphaned refs | Possible si pipeline_run supprimé (non prévu par append-only) |
| Statut | **ATTENTION** — `pipeline_run_id` nullable par design (blocked paths). Pas une anomalie, mais à documenter. |

### memory_entries (migration 002)

| Critère | Résultat |
|---|---|
| Writer actif | Oui — `add_memory()` dans `src/core/dependencies.py` |
| Contenu | `entry_type` = `"extraction"` ou `"decision"` (via `src/api/analysis.py`) |
| Manque | Pas de `entry_type = "case_summary"` structuré — **CaseMemoryWriter H0.4 comble ce gap** |
| Statut | **FONCTIONNEL** — alimentation partielle, enrichie par H0.4 |

## Actions

| Action | Composant | Horizon |
|---|---|---|
| CaseMemoryWriter créé (H0.4) | `memory_entries` + `case_summary` | H0 **FAIT** |
| Documenter pipeline_run_id nullable | `analysis_summaries` | H0 **FAIT** (ce rapport) |
| Aucune action corrective nécessaire | `decision_snapshots` | N/A |

## Verdict

**3/3 tables opérationnelles.** Aucune table morte. `memory_entries` enrichi par CaseMemoryWriter.
Le probe automatisé (`scripts/probe_h0_table_health.py`) est disponible pour exécution sur DB réelle.
