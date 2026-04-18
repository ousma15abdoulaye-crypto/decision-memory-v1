# DÉCISION P3.2 — CRITERION_ASSESSMENTS EXCLUSIF

**Date** : 2026-04-17  
**Émetteur** : CTO Senior DMS  
**Référence** : MANDAT_P3.2_SCORING_ENGINE_PILOTE_V2 — Article 10, Condition 1  
**Statut** : Opposable

---

## DÉCISION

P3.2 Scoring Engine opère **exclusivement** sur la table **`criterion_assessments`** (existante).

La table **`score_runs`** est **hors périmètre** P3.2 — **jamais écrite, jamais lue** par le moteur de scoring P3.2.

---

## JUSTIFICATION

### Doctrine gravée (Article 2, règle #2)
> **P3.2 n'écrit pas dans `score_runs`.**

### Critique technique

`score_runs` est une table **legacy** du système de scoring V1 (`src/couche_a/scoring/engine.py` — ScoringEngine). Ce système legacy est **interdit permanent** dans le chemin pipeline V5 (Article 13, Article 14.1).

P3.2 construit un **nouveau composant de scoring** qui :
- Produit des scores **traçables ligne à ligne** (SubCriterionScore + FamilyScore + SupplierEvaluation — Article 6)
- Persiste dans **`criterion_assessments`** via bridge M14→M16 idempotent (Gate E préservé — Article 11)
- Évite toute **vérité concurrente** sur le scoring

---

## PERSISTANCE P3.2 (rappel)

| Objet | Table cible | Mode |
|---|---|---|
| `SubCriterionScore` | `criterion_assessments` | 1 row par (bundle_id, criterion_id), clé UUID pure, idempotent |
| `FamilyScore` | Dérivé en lecture | **Non persisté en table dédiée** |
| `SupplierEvaluation` | `evaluation_documents.scores_matrix` | Payload étendu via `save_evaluation` |

**Aucune nouvelle table créée par P3.2.**  
**`score_runs` hors périmètre (doctrine #2). Cette règle est non négociable.**

---

## CONSÉQUENCES OPÉRATIONNELLES

1. Toute référence à `score_runs` dans le code P3.2 est refusée en revue de PR
2. Le test de gouvernance (Condition 4) bloque tout accès à `src.couche_a.scoring.*` depuis `pipeline_v5_service.py`
3. `get_latest_score_run` (AttributeError) reste un bug legacy hors périmètre P3.2 — documenté par Issue GitHub (Condition 2)

---

**Document archivé. Opposable dès signature CTO principal.**
