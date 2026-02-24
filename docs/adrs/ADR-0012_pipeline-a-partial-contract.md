# ADR-0012 — Pipeline A Partial : Contrat d'orchestration

**Date :** 2026-02-24
**Statut :** ACTIF
**Auteur :** CTO Senior — Abdoulaye Ousmane
**Milestone :** #10 M-PIPELINE-A-PARTIAL
**Références :** ADR-0002 / ADR-0008 / ADR-0009 / ADR-0010 / ADR-0011

---

## Contexte

Le milestone #10 introduit la **couche d'orchestration** du pipeline A pour les
dossiers d'appels d'offres DMS.

Les milestones précédents (#1–#9) ont livré des briques métier indépendantes
(extraction, scoring, normalisation, comité). Le pipeline A les assemble en une
exécution **séquencée, tracée et typée**, sans encore produire les exports CBA/PV
(réservés aux milestones #12/#13).

**Ce que #10 prouve :**

- Couche A sait exécuter un dossier de manière orchestrée
- Préflight robuste avec 4 reason_codes exacts (scope préflight uniquement)
- Étapes séquencées et tracées avec timing capturé à chaque step
- Statuts explicites : `blocked / incomplete / failed / partial_complete`
- Traces append-only en DB — `pipeline_runs` + `pipeline_step_runs`
- Résultat typé `CaseAnalysisSnapshot v1` — validé Pydantic, exploitable par #12/#13
- Zéro génération CBA/PV

---

## Décision

### 1. Tables append-only

Deux tables sont créées :

| Table | PK | Append-only |
|---|---|---|
| `public.pipeline_runs` | `pipeline_run_id UUID` | trigger `trg_pipeline_runs_append_only` |
| `public.pipeline_step_runs` | `step_run_id UUID` | trigger `trg_pipeline_step_runs_append_only` |

Les triggers BEFORE UPDATE OR DELETE lèvent une exception PostgreSQL.
Aucune mutation possible après INSERT — immutabilité garantie DB-level.

### 2. CaseAnalysisSnapshot v1 (CAS)

Le CAS est le **contrat canonique inter-milestones** entre #10, #12 et #13.

```
CaseAnalysisSnapshot v1
├── cas_version: Literal["v1"]
├── case_context: CASCaseContext (case_id, title, currency, status, case_type)
├── readiness: CASReadiness (export_ready: Literal[False])
├── criteria_summary: CASCriteriaSummary (count, categories, has_eliminatory)
├── offer_summary: CASOfferSummary (count, supplier_names)
├── score_summary: CASScoreSummary (scores_count, eliminations_count)
├── steps: list[PipelineStepResult]
└── generated_at: datetime
```

**Champs interdits dans CAS v1 (INV-P7) :** winner, rank, recommendation, best_offer.
Enforced par `model_validator` Pydantic + tests CI dédiés.

### 3. Statuts possibles dans #10

```
partial_complete | blocked | incomplete | failed
```

`complete` est **interdit dans #10** (réservé #14 — pipeline e2e finalisé).

### 4. export_ready = False TOUJOURS dans #10 (INV-P8)

`CASReadiness.export_ready` est `Literal[False]`. Toute tentative
d'instancier `CASReadiness(export_ready=True)` est rejetée par Pydantic.

### 5. Séquence d'orchestration

```
preflight
  → [blocked si CASE_NOT_FOUND | DAO_MISSING | OFFERS_MISSING | MIN_OFFERS_INSUFFICIENT]
extraction_summary   (lecture seule, offer_extractions)
criteria_summary     (lecture seule, dao_criteria)
normalization_summary (lecture seule, score_runs existants)
scoring              (délégation ScoringEngine — écrit score_runs append-only)
  → build CAS v1
  → persist atomique (pipeline_runs + pipeline_step_runs, 1 transaction)
```

### 6. Pattern connexion DB — Pattern B

`get_db_connection()` de `src/db/core.py` est un context manager qui commit à
la sortie du scope (`yield conn; conn.commit()`).

`_persist_pipeline_run_and_steps()` n'appelle **pas** `conn.commit()`.
Le commit est géré par le caller (router `_get_conn()` dependency).

### 7. Frontière Couche A/B (ADR-0011)

`src/couche_a/pipeline/` ne doit **jamais** importer :

- `couche_b`
- `market_signal`
- `mercuriale`
- `decision_history`
- `supplier_history`

Enforced par le test AST `test_pipeline_a_no_couche_b_import.py`.

---

## Invariants INV-P1 → INV-P12

| ID | Invariant | Enforcement |
|---|---|---|
| INV-P1 | `case_id` est TEXT — jamais cast UUID | Applicatif `_preflight_case_a_partial` |
| INV-P2 | `score_runs` append-only — pipeline ne le modifie pas | ScoringEngine seul propriétaire |
| INV-P3 | Pipeline idempotent sur le scoring — re-run = nouveau run_id | UUID généré à chaque run |
| INV-P4 | Persistance atomique — pipeline_runs + steps = 1 transaction | psycopg + trigger append-only |
| INV-P5 | `decision_snapshots` sans winner/rank (hérité #9) | trigger + Pydantic |
| INV-P6 | pipeline_run sans pipeline_step_runs = état interdit | `_persist_pipeline_run_and_steps` atomique |
| INV-P7 | CAS v1 sans winner/rank/recommendation/best_offer | `model_validator` Pydantic + tests CI |
| INV-P8 | `export_ready = False` toujours dans #10 | `Literal[False]` Pydantic |
| INV-P9 | `result_jsonb` = CAS v1 sérialisé complet récupérable | GET /last lit result_jsonb |
| INV-P10 | `step_name` fermé — valeurs exactes imposées par CHECK DB | CHECK + `Literal` Pydantic |
| INV-P11 | `triggered_by` non-vide + ≤ 255 chars | `field_validator` Pydantic + CHECK DB |
| INV-P12 | `duration_ms ≥ 0` — protégé contre NTP drift | `max(0, ...)` dans `_duration_ms()` |

---

## Conséquences

### Positives

- **#12 (CBA)** et **#13 (PV)** peuvent consommer `CAS v1` depuis `result_jsonb` sans recalcul
- **#11** peut étendre le moteur scoring sans toucher au contrat CAS
- **Traçabilité complète** : chaque run pipeline est immutable en DB
- **Préflight explicite** : les dossiers incomplets sont bloqués avec un reason_code clair

### Négatives / Contraintes

- `pipeline_runs` étant append-only, les runs de test s'accumulent (as designed, comme `score_runs`)
- Le scoring step requiert des `offer_extractions` (pas seulement des `offers`)
- `export_ready = False` bloquera les exports jusqu'à #14

---

## Non-objectifs (#10)

- ❌ Génération CBA (milestone #12)
- ❌ Génération PV (milestone #13)
- ❌ Appel Couche B / mercuriale / market signals
- ❌ `force_recompute` (reporté #11)
- ❌ `status = complete` (réservé #14)
- ❌ Winner / rank / recommendation dans le CAS
