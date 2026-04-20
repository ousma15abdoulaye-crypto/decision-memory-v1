# DMS — P3.4 E1 rapport : modèles canoniques matrice

**Référence** : P3.4-E1-MATRIX-MODELS  
**Date** : 2026-04-19  
**Branche** : `feat/p3-4-matrixrow-builder-summary`  
**Statut** : **READY FOR E2** (sous revue CTO Senior)

---

## 1. Modèles créés

| Modèle | Fichier | Rôle |
|--------|---------|------|
| `MatrixRow` | `src/procurement/matrix_models.py` | Ligne matrice canonique (4 familles logiques) |
| `MatrixSummary` | idem | Synthèse cohorte (compte-rendu, champs interdits absents) |
| `MatrixRowExplainability` | idem | Sous-structure déterministe P6bis |
| `OverrideRef` | idem | Contrat préparatoire P3.4B (inactif) |
| `RegularizationRef` | idem | Contrat préparatoire P3.4C (inactif) |

---

## 2. Enums créés (valeurs)

| Enum | Valeurs |
|------|---------|
| `EligibilityStatus` | `ELIGIBLE`, `INELIGIBLE`, `PENDING`, `REGULARIZATION_PENDING` |
| `ComparabilityStatus` | `COMPARABLE`, `NON_COMPARABLE`, `INCOMPLETE` |
| `RankStatus` | `RANKED`, `EXCLUDED`, `PENDING`, `NOT_COMPARABLE`, `INCOMPLETE` |
| `CohortComparabilityStatus` | `FULLY_COMPARABLE`, `PARTIALLY_COMPARABLE`, `NOT_COMPARABLE` |
| `TechnicalThresholdMode` | `INFORMATIVE`, `MANDATORY` (défaut champ = `MANDATORY`) |
| `CorrectionNature` | 7 codes G2 (lecture, preuve, retard, régularisation, override, dérogation) |
| `StatusOrigin` | `PIPELINE_SYSTEM`, `COMMITTEE_OVERRIDE`, `REGULARIZATION`, `DEFAULT_APPLIED` |

Implémentation : **`StrEnum`** (Python 3.11) — conformité Ruff UP042, sérialisation JSON stable.

---

## 3. Champs par famille (`MatrixRow`)

1. **Identité** : `workspace_id`, `bundle_id`, `supplier_name`, `pipeline_run_id`, `matrix_revision_id`, `computed_at`  
2. **État** : `eligibility_status`, `eligibility_reason_codes`, `technical_threshold_mode`, `technical_threshold_value`, `technical_qualified`  
3. **Scores / comparabilité / rang** : `*_score_system`, `*_score_override`, `total_comparability_status`, `rank`, `rank_status`, `exclusion_reason_codes`, `warning_flags`, `human_review_required`, `override_summary`, `last_override_at`, `regularization_summary`, `has_regularization_history`  
4. **Trace / explication** : `evidence_refs`, `explainability`, `status_origin`

**Scores `*_score_effective` et `has_any_override`** : exposés via **`@computed_field`** (dérivés de `override ?? system` et de la présence d’overrides). Motif : éviter l’anti-pattern Pydantic v2 « `model_validator(mode='after')` qui retourne un `model_copy` » lors d’une construction par `__init__` (comportement non supporté / avertissement). Sémantique mandat **inchangée** : pas d’édition directe des effectifs ; lecture = vue calculée.

---

## 4. Validateurs d’invariants

| ID | Implémentation |
|----|----------------|
| **I1** | `INELIGIBLE` ⇒ `total_score_system is None`, `rank is None`, `rank_status == EXCLUDED` |
| **I2** | `rank_status` ∈ {`EXCLUDED`,`PENDING`,`NOT_COMPARABLE`,`INCOMPLETE`} ⇒ `rank is None` ; `RANKED` ⇒ `rank >= 1` |
| **I3** | Cohérence **additivité** : si les trois piliers effectifs sont non-`None` et pas de `total_score_override`, alors `total_score_effective` non-`None` et ≈ somme (ε = 1e-6) ; message d’erreur joint I3 / additivité |
| **I4** | `total_comparability_status == INCOMPLETE` et `rank_status == EXCLUDED` ⇒ rejet |
| **I5** | **Documenté** sur `warning_flags` (append-only) — pas de validator qui efface la liste |
| **I6** | `MatrixSummary` : pas de champs `recommended_winner` / `average_total_score` / `suggested_rank_order` ; constante `FORBIDDEN_MATRIX_SUMMARY_FIELDS` ; test d’introspection `model_fields` |

**Règles contractuelles additionnelles** : si aucun override, `override_summary` vide et `last_override_at` is `None`.  
**Defaults `mode='before'`** : `technical_threshold_mode` → `MANDATORY` si absent ; `matrix_revision_id` ← `pipeline_run_id` si absent.

---

## 5. Justification system / override / effective

- **System** : vérité moteur M14 / scoring (immuabilité future G1 côté persistance).  
- **Override** : réservé P3.4B ; `None` en P3.4.  
- **Effective** : **toujours** `override if override is not None else system` ; exposé en `computed_field` pour garantir l’alignement sans champ saisi incohérent.

---

## 6. Hors E1 (volontairement)

- `ReviewState` : non introduit (mandat OUT).  
- Builder, pipeline, DB, UI, migrations : **OUT** (cf. mandat).  
- Pas de modification de `m14_engine`, `m14_bridge`, `eligibility_models`, P3.2 / P3.3.

**Vocabulaire code** : alignement sur **`OfferEvaluation` / `EvaluationReport`** (repo) — pas de type `SupplierEvaluation` dans le code.

---

## 7. Pytest

| Commande | Résultat |
|----------|----------|
| `pytest tests/unit/procurement/test_matrix_models.py -q` | **18 passed** |
| `pytest tests/unit/ -q --tb=line` | **434 passed** en **844,48 s** (~14 min), **6 warnings** — exécution complète **immédiatement avant** le commit E1 |

*Ruff* : `ruff check` sur les deux fichiers `.py` E1 — **OK**.

---

## 8. Fichiers livrables E1

1. `src/procurement/matrix_models.py`  
2. `tests/unit/procurement/test_matrix_models.py`  
3. `decisions/p34_e1_matrix_models.md` (ce document)

---

## 9. Verdict

**READY FOR E2** — ouverture builder / agrégation, sous feu vert CTO Senior après relecture des trois fichiers.

**Format ultra-court (mandat)**

1. `matrix_models.py` créé : **OUI**  
2. `MatrixRow` + `MatrixSummary` définis : **OUI**  
3. Enums métier (7 `StrEnum` + constante interdits) : **OUI**  
4. Validators I1–I6 implémentés (I5 doc, I6 test) : **OUI**  
5. Tests de contrat : **PASSED** (18 + suite unitaire 434 selon §7)  
6. Verdict global : **READY FOR CTO REVIEW / E2**
