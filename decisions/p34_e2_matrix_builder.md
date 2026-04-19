# DMS — P3.4 E2 rapport : matrix builder (projection + rang R1–R9)

**Référence** : P3.4-E2-MATRIX-BUILDER  
**Date** : 2026-04-19  
**Statut** : **READY FOR E3**

---

## 1. Signatures builders créées : **OUI**

| Fonction | Fichier |
|----------|---------|
| `build_matrix_rows(workspace_id, pipeline_run_id, offer_evaluations, gate_output, dao_criteria, technical_threshold_config=None)` | `src/services/matrix_builder_service.py` |
| `build_matrix_summary(matrix_rows, workspace_id, pipeline_run_id)` | idem |

`dao_criteria` est consommé (pondérations agrégées) pour ancrage futur ; `MatrixSummary` ne reçoit pas le gate — champs `essential_criteria_*` restent à **0** jusqu’à branchement E3 (documenté).

---

## 2. Algorithme R1–R9 implémenté : **OUI**

Implémentation alignée sur **§P5.3** (`decisions/p34_opening_preflight.md`) avec précision **R9** : asymétrie commerciale = présence simultanée de `commercial_score_system` **NULL** et **non-NULL** dans la partition **RANKABLE** (éligible + règle seuil technique). Sinon cohorte uniquement « NULL partout » → `NOT_COMPARABLE` **sans** `COHORT_ASYMMETRIC_COMMERCIAL` (évite faux signal à *n*=1, cohérent avec l’intention R7 vs R9).

**Convention scores** (hors champs M14) : lecture déterministe des flags sur `OfferEvaluation` :

- `p33_price_ambiguous` (et variantes) ⇒ `commercial_score_system = None` (R7).
- `DMS_MATRIX_COMMERCIAL_SCORE=<float>` et `DMS_MATRIX_SUSTAINABILITY_SCORE=<float>` ⇒ projection commerciale / durabilité pour la suite P3.4 jusqu’à exposition native moteur.

---

## 3. MatrixSummary builder créé : **OUI**

Agrégation des comptages sur les `MatrixRow` finales, `critical_flags_overview` par union des `warning_flags`, `cohort_comparability_status` selon **§P6.4** adapté (couche éligible + cohorte entièrement éligible pour `FULLY_COMPARABLE`).

---

## 4. Explicabilité peuplée déterministe : **OUI**

`MatrixRowExplainability` : `status_chain` canonique P6bis ; `primary_status_source` (ex. `P3.1B:INELIGIBLE`, `P3.4:COHORT_ASYMMETRIC_COMMERCIAL`, `P3.4:RANKED`) ; `score_breakdown` léger ; `exclusion_path` si non classé / exclu.

---

## 5. Tests R1–R9 + cohorte asymétrique : **PASSED (14)**

Fichier : `tests/unit/services/test_matrix_builder.py` — couverture : R1–R9, trois scénarios `cohort_comparability_status`, re-vérification **I6** sur `MatrixSummary`, idempotence (dump stable hors `computed_at` et champs calculés), flag `TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED`, chaîne d’explicabilité, flag informatif sous-seuil (`TECHNICAL_INFORMATIVE_BELOW_THRESHOLD`).

**Pytest ciblé** : `tests/unit/procurement` + `tests/unit/services` → **32 passed** (dont 18 E1 + 14 E2).

---

## 6. Verdict : **READY FOR E3**

Fichiers **hors périmètre E2** respectés (`matrix_models.py`, `test_matrix_models.py`, pipeline M14 intacts). Prochaine étape : orchestration **E3** (branchement pipeline) sans modifier les contrats E1/E2 gelés.
