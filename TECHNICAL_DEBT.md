# TECHNICAL_DEBT.md — DMS V4.1.0
**Généré :** 2026-02-26
**Milestone :** M0 FIX-CI & REPO TRUTH SYNC
**Branche :** feat/m0-fix-ci
**Ref :** docs/freeze/DMS_V4.1.0_FREEZE.md

---

## Erreurs M0 identifiées

> Aucune erreur CI détectée lors du PROBE M0.
> CI verte : 479 passed / 35 skipped / 0 failed / 0 errors.
> Alembic heads : 035 unique.

```
import_error    : aucune
schema_mismatch : aucune
logic_error     : aucune
fixture_residue : aucune
```

---

## Erreurs M0 corrigées

> Aucune correction applicative requise.
> CI était verte avant toute intervention sur le code source.

---

## Stubs actifs

### `time.sleep` (réservé M10A — NE PAS SUPPRIMER)

| Fichier | Ligne | Description |
|---|---|---|
| `src/couche_a/extraction.py` | 416 | Stub `extract_offer_content` — simule extraction avec `time.sleep(2)`, retourne `{"status": "completed"}`. Réservé M10A (LLM extraction engine). |

### `return {}` dans `src/couche_a/`

| Fichier | Ligne | Description |
|---|---|---|
| `src/couche_a/price_check/engine.py` | 79 | Retour `{}` dans le cas où aucune anomalie de prix n'est détectée — comportement légitime, non un stub. |

### Stub extraction (fonctions placeholder — réservé M10A)

| Fichier | Fonction | Description |
|---|---|---|
| `src/couche_a/extraction.py` | `extract_offer_content` | Corps stub complet : `time.sleep(2)` + retour statique. SLA-B non implémenté. |
| `src/couche_a/extraction.py` | `extract_dao_criteria_structured` | Utilise regex basique + critères hardcodés si aucun critère trouvé. |

---

## FK manquantes identifiées

| Table source | Colonne | Table cible | Statut |
|---|---|---|---|
| `pipeline_runs` | `case_id` | `cases` | Aucune contrainte FK définie dans les migrations (colonne ajoutée en 032, lien logique uniquement) |
| `analysis_summaries` | `case_id` | `cases` | Aucune contrainte FK définie dans les migrations (colonne ajoutée en 035, lien logique uniquement) |
| `score_runs` | `case_id` | `cases` | Aucune FK explicite dans les migrations à ce jour — à confirmer via inspection du schéma DB actuel |
| `offers` | `case_id` | `cases` | Table `public.offers` absente du schéma actuel — voir section "Tables ambiguës" |

> Note : La table `public.offers` est référencée dans `src/couche_a/pipeline/service.py` (preflight check)
> mais absente du schéma Alembic courant. Les tests preflight concernés sont marqués SKIPPED.
> Création de cette table : hors scope M0, nécessite instruction explicite (STOP-4 potentiel).

---

## Tables ambiguës — noms réels à confirmer avant migrations futures

| Nom référencé dans le code | Statut | Fichier source | Note |
|---|---|---|---|
| `public.offers` | **ABSENTE** du schéma Alembic | `src/couche_a/pipeline/service.py:preflight` | Référencée dans COUNT(*) preflight ; tests associés SKIPPED |
| `public.scoring_configs` | À confirmer | `src/couche_a/scoring/engine.py` | Chargement des poids scoring |
| `public.criteria` | Existante (migration antérieure) | `src/couche_a/criteria/service.py` | Colonne `is_essential` (pas `is_eliminatory`) |
| `public.pipeline_runs` | Existante — migration 035 | `src/couche_a/pipeline/service.py` | Append-only, trigger DB |
| `public.analysis_summaries` | Existante — migration 035 | `src/couche_a/analysis_summary/engine/service.py` | Append-only, trigger DB |
| `public.committee_snapshots` | À confirmer | `src/couche_a/committee/snapshot.py` | Snapshot scellé comité |

---

## Tests absents sur invariants critiques

| Invariant | Statut couverture | Note |
|---|---|---|
| `public.offers` preflight complet | Tests SKIPPED | Table absente — réactivation post-création `offers` |
| SLA-B extraction (Tesseract/Azure) | 2 tests SKIPPED (`test_sla_classe_b_has_queue`) | Queue déclarée, non implémentée — M10A |
| SLA-A timing 60s | 1 test SKIPPED (`test_sla_classe_a_60s`) | Test de performance désactivé |
| Market signal impact scoring | 1 test SKIPPED | Hors scope M0 |
| LLM router (`llm_router.py`) | Absent | Module non créé — défini dans freeze V4.1.0, M10A |
| `ExtractionField` / `TDRExtractionResult` | Absent | Modèles définis dans freeze V4.1.0, M10A |
| Annotation protocol | Absent | Hors scope beta |

---

## Hors scope beta

| Fonctionnalité | Raison du report |
|---|---|
| Interface bambara | Décision produit — hors beta V4.1.0 |
| Interface peul | Décision produit — hors beta V4.1.0 |
| Interface anglais | Décision produit — hors beta V4.1.0 |
| Mailbox intégrée | Architecture non définie — hors beta V4.1.0 |
| Email automatique (notifications) | Dépendance SMTP/service externe — hors beta V4.1.0 |

---

## Violations RÈGLE-09 (winner/rank/recommendation dans src/)

> **0 violation.**
>
> Toutes les occurrences de `winner`, `rank`, `recommendation` dans `src/` sont :
> - Dans des listes de rejet (`_FORBIDDEN_FIELDS`, `_FORBIDDEN_IN_CONTENT`) — guards Pydantic corrects
> - Dans des commentaires/docstrings explicitant l'interdiction
> - Dans `COMMITTEE_EVENT_TYPES` : `"recommendation_set"` est un événement de délibération humaine,
>   non un champ décisionnel automatique — conforme à l'architecture comité.

---

## Résumé DoD M0

| Condition | Statut |
|---|---|
| pytest → 0 failed / 0 errors | **VERT** (479 passed, 35 skipped) |
| alembic heads → exactement 1 résultat = 035 | **VERT** |
| TECHNICAL_DEBT.md toutes sections remplies | **VERT** |
| ci_diagnosis.txt committé | **VERT** |
| time.sleep src/ → inventorié (pas supprimé) | **VERT** (`extraction.py:416`) |
| winner/rank/recommendation src/ → 0 violation | **VERT** |
| AUCUNE migration créée dans alembic/versions/ | **VERT** |
| AUCUN fichier hors périmètre modifié | **VERT** |
