# P3.3 — Rectification avant PR (paquet CTO)

**Date** : 2026-04-18  
**Référence mandat** : `MANDAT_P3.3_RECTIFICATION_AVANT_PR.md`  
**Verdict document** : `READY FOR CTO REVIEW`

---

## 1. Rectification commerciale effectuée

- Suppression de la **repondération automatique** des poids dans `_calculate_total_scores` (`src/couche_a/scoring/engine.py`).
- Lorsque **tous** les résultats `category == "commercial"` portent `p33_commercial_suppressed` :
  - le total reste la **somme pondérée avec les poids DAO inchangés** (contribution commercial = score 0 × poids commercial) ;
  - `calculation_details` inclut **`total_not_comparable: true`**, **`p33_total_score_semantic_incomplete: true`**, **`human_review_required: true`**.
- Lorsqu’**au moins un** commercial est supprimé mais **pas tous** :
  - **`p33_total_cohort_commercial_incomplete: true`** sur chaque ligne `total` (cohorte prix asymétrique).
- Chaque ligne `commercial` supprimée P3.3 inclut désormais **`p33_commercial_score_semantic_null: true`** et **`human_review_required: true`** (en plus de `p33_commercial_suppressed`).
- Contrainte persistance SQL : `score_runs.score_value` reste **NOT NULL** ; la sémantique « null » prix est portée par **`calculation_details`**, pas par violation de schéma DB (hors périmètre Alembic).

---

## 2. Décision finale sur le total quand prix non qualifiable

| Situation | Total numérique | Comparabilité déclarée |
|-----------|-----------------|-------------------------|
| Aucun prix qualifiable pour **tous** les fournisseurs actifs | Somme pondérée standard (commercial × 0) | **`total_not_comparable: true`** |
| Prix qualifiable pour une partie seulement du lot | Somme pondérée standard | **`p33_total_cohort_commercial_incomplete: true`** (pas `total_not_comparable`) |

---

## 3. Rectification confiance

- Nouveau type **`QualificationConfidence`** (`LOW` / `MEDIUM` / `HIGH`) dans `src/couche_a/scoring/qualified_price.py` ; champ **`confidence`** de `QualifiedPrice` n’accepte plus de float libre.
- `commercial_normalizer.py` : **HIGH** si aucun drapeau de cohérence ligne ; **MEDIUM** si drapeaux présents (ex. mélange OK/ANOMALY).
- Export public : `src/couche_a/scoring/__init__.py` réexporte `QualificationConfidence`.

---

## 4. Option retenue pour `get_latest_score_run`

- **Option 2 (préférence CTO)** : retrait du bloc cache dans `src/couche_a/pipeline/service.py` (`_run_scoring_step`). Appel **direct** systématique à `ScoringEngine.calculate_scores_for_case`.
- Suppression du `# type: ignore` et du chemin nominal basé sur **`AttributeError`**.
- **Note** : `ADR-0013` / docs citant l’ancien fallback « cache indisponible » sont désormais **divergents** du code ; mise à jour ADR hors périmètre de ce mandat.

---

## 5. Logging structuré minimal

- Nouveau module `src/couche_a/scoring/p33_trace.py` : `log_p33_structured(event, **fields)` → logger `dms.p33`, message préfixé `p33` + **JSON** (stdlib).
- Émissions obligatoires :
  - chaque **`p33_commercial_suppressed`** (commercial) : `case_id`, `supplier_name`, `reason_code` ;
  - chaque **`p33_total_not_comparable`** : `case_id`, `supplier_name`, `reason_code` (`P33_ALL_COMMERCIAL_SUPPRESSED`).

---

## 6. Fichiers modifiés ou ajoutés

| Fichier | Action |
|---------|--------|
| `src/couche_a/scoring/engine.py` | Politique total / commercial / logging |
| `src/couche_a/scoring/qualified_price.py` | Enum confiance |
| `src/couche_a/scoring/commercial_normalizer.py` | Valeurs confiance discrètes |
| `src/couche_a/scoring/p33_trace.py` | **Ajout** — trace JSON |
| `src/couche_a/scoring/__init__.py` | Export `QualificationConfidence` |
| `src/couche_a/pipeline/service.py` | Retrait faux cache |
| `tests/couche_a/test_scoring.py` | Assertions P3.3 / total sans rescale |
| `tests/scoring/test_commercial_normalizer_p33.py` | Confiance enum + cas MEDIUM |
| `tests/scoring/test_p33_rectification_case_28b05d85.py` | **Ajout** — T1–T3 + log |
| `tests/pipeline/test_pipeline_force_recompute.py` | **Réécrit** — T4 |
| `decisions/p33_rectification_test_report.md` | **Ajout** |
| `decisions/p33_rectification_before_pr.md` | **Ajout** (ce fichier) |

---

## 7. Verdict

**`READY FOR CTO REVIEW`**

---

## Rapport exécutif — 7 blocs (format mandat ARTICLE 10)

1. **politique commerciale corrigée** : **OUI**
2. **repondération supprimée / neutralisée** : **OUI**
3. **politique de confiance fermée** : **OUI**
4. **faux cache traité** : **OUI**
5. **logging structuré ajouté** : **OUI**
6. **tests T1/T2/T3/T4** : **PASS** (voir `decisions/p33_rectification_test_report.md` ; hors tests DB bloquants `test_save_scores_to_db` / `test_full_scoring_pipeline` non exigés par ce mandat)
7. **verdict final** : **`READY FOR CTO REVIEW`**
