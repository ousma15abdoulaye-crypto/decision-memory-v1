# P3.3 — Rapport de tests rectification (avant PR)

**Date** : 2026-04-18

---

## Tests ajoutés ou modifiés

| Fichier | Modification |
|---------|----------------|
| `tests/scoring/test_p33_rectification_case_28b05d85.py` | **Ajout** — T1, T2, T3 (enum + log), corpus `CASE-28b05d85` / UUID équivalent |
| `tests/scoring/test_commercial_normalizer_p33.py` | Assertions `QualificationConfidence` ; cas **MEDIUM** (lignes OK+ANOMALY) |
| `tests/couche_a/test_scoring.py` | `test_calculate_total_scores_p33_no_rescale_when_all_commercial_suppressed` ; assertions `p33_commercial_score_semantic_null` ; `case_id` sur commercial |
| `tests/pipeline/test_pipeline_force_recompute.py` | **Réécrit** — stubs sans `get_latest_score_run` ; plus de `lookup_warning` |

---

## Commandes exécutées

```text
python -m pytest tests/scoring/test_p33_rectification_case_28b05d85.py tests/scoring/test_commercial_normalizer_p33.py tests/pipeline/test_pipeline_force_recompute.py tests/couche_a/test_scoring.py::TestScoringEngine::test_calculate_total_scores_p33_no_rescale_when_all_commercial_suppressed tests/couche_a/test_scoring.py::TestScoringEngine::test_calculate_commercial_scores_basic tests/couche_a/test_scoring.py::TestScoringEngine::test_calculate_commercial_scores_no_prices -q --tb=line
```

```text
python -m pytest tests/scoring/test_commercial_normalizer_p33.py::test_qualify_mixed_ok_and_anomaly_lines_yields_medium_confidence -q
```

---

## Résultats bruts utiles

```text
19 passed in 0.52s
```

(dernière exécution ciblée mandat T1–T4 + normalizer + commercial de base + pipeline scoring.)

---

## Verdict binaire par scénario

| Scénario | Verdict |
|----------|---------|
| **T1** — Aucun prix qualifiable pour tous les vendors | **PASS** |
| **T2** — Aucun prix qualifiable pour un seul vendor | **PASS** |
| **T3** — Politique de confiance (enum, float rejeté, log) | **PASS** |
| **T4** — Faux cache retiré | **PASS** |

---

## Hors périmètre explicite (non relancé ici)

- `tests/couche_a/test_scoring.py::test_save_scores_to_db` — I/O Postgres requis.
- `tests/couche_a/test_scoring.py::TestScoringIntegration::test_full_scoring_pipeline` — idem.
