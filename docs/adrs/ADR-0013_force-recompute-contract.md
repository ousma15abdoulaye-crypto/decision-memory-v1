# ADR-0013 — Contrat `force_recompute` & comportement ScoringEngine

**Statut :** Accepté  
**Date :** 2026-02-24  
**Milestone :** M-PIPELINE-A-E2E (#11)  
**Auteur :** Agent pipeline  
**Références :** INV-P14, INV-P15A, INV-P18, ADR-0012

---

## Contexte

Le milestone #11 introduit un paramètre `force_recompute` dans le pipeline A pour contrôler
si le scoring doit obligatoirement recalculer (`True`) ou tenter de réutiliser un score
déjà calculé (`False`).

La question se pose : comment se comporte ce contrat face à l'implémentation actuelle
du `ScoringEngine` qui **n'expose pas** `get_latest_score_run()` ?

---

## Décision

### INV-P15A — `force_recompute=True`

Quand `force_recompute=True`, `_run_scoring_step()` appelle **toujours**
`engine.calculate_scores_for_case()` sans aucune tentative de réutilisation.

Cette invariante est stricte et ne dépend pas de l'état du `ScoringEngine`.

### INV-P14 — `force_recompute=False`

Quand `force_recompute=False`, `_run_scoring_step()` tente d'abord d'appeler
`engine.get_latest_score_run(case_id)` pour réutiliser le dernier score valide.

**Comportement observé (#11) :**  
`ScoringEngine.get_latest_score_run` est **absent** de l'implémentation courante.
L'appel lève une `AttributeError`, ce qui déclenche le fallback systématique vers
`calculate_scores_for_case()`.

Le meta du step scoring tracera `lookup_warning: "SCORE_CACHE_UNAVAILABLE_FALLBACK"`
dans ce cas, permettant l'observabilité sans lever d'exception.

**Conséquence fonctionnelle :** Dans #11, `force_recompute=False` est fonctionnellement
équivalent à `force_recompute=True` en pratique — les deux calculent. La distinction
est **traçable** (via `pipeline_runs.force_recompute` et `meta.lookup_warning`) et
**sémantiquement correcte** pour les milestones futurs.

### INV-P18 — Traçabilité dans `pipeline_runs`

La colonne `pipeline_runs.force_recompute BOOLEAN NOT NULL DEFAULT FALSE`
(migration `034_pipeline_force_recompute`) trace la valeur passée par le caller.
Cette donnée est **immuable** (table append-only, trigger protection).

---

## Alternatives rejetées

| Alternative | Raison du rejet |
|---|---|
| Lever une exception si `get_latest_score_run` absent | Viole le principe fail-forward du pipeline — un scoring calculé vaut mieux qu'une erreur |
| Retourner `None` sans fallback si méthode absente | Perd le résultat de scoring, rend #12/#13 impossible |
| Implémenter `get_latest_score_run` dans #11 | Hors scope #11 — réservé #12 ou milestone dédié |
| Rendre `force_recompute` opaque (pas de trace DB) | Viole l'observabilité — contredit ADR-0012 |

---

## Conséquences

- `run_pipeline_a_e2e()` passe `force_recompute` à `_run_scoring_step()` et `_persist_pipeline_run_and_steps()`.
- `run_pipeline_a_partial()` utilise les defaults (`force_recompute=False`) — **inchangée** (GUARD-OPS-01).
- Les milestones futurs qui implémentent `get_latest_score_run` bénéficieront automatiquement de INV-P14 sans modifier le pipeline.
- Le test L7 (`test_pipeline_force_recompute.py`) valide ce contrat.

---

## Schéma de décision `_run_scoring_step`

```
force_recompute=True
    └─→ calculate_scores_for_case()  [INV-P15A]

force_recompute=False
    ├─→ get_latest_score_run() disponible ET résultat non-None
    │       └─→ réutilise scores  [INV-P14]
    │           meta.lookup_warning = "SCORE_REUSED_FROM_CACHE"
    ├─→ get_latest_score_run() disponible MAIS retourne None
    │       └─→ calculate_scores_for_case()  [fallback]
    └─→ get_latest_score_run() ABSENT (AttributeError)
            └─→ calculate_scores_for_case()  [ADR-0013 fallback]
                meta.lookup_warning = "SCORE_CACHE_UNAVAILABLE_FALLBACK"
```
