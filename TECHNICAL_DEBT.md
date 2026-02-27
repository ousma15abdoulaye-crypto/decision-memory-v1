# TECHNICAL_DEBT.md — DMS V4.1.0
**Généré :** 2026-02-26
**Milestone :** M0 / M0B
**Branche :** feat/m0b-db-hardening
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
| `pipeline_runs` | `case_id` | `cases` | FK créée NOT VALID (M0B) — voir section "FK non validées" |
| `analysis_summaries` | `case_id` | `cases` | FK existante via migration 035 |
| `score_runs` | `case_id` | `cases` | À confirmer par inspection schéma DB actuel |
| `offers` | `case_id` | `cases` | présente — créée par 002_add_couche_a |

---

## FK non validées (NOT VALID)

| Contrainte | Table | Référence | Cause | Action |
|---|---|---|---|---|
| fk_pipeline_runs_case_id | pipeline_runs | cases(id) | Lignes orphelines détectées au PROBE-SQL-01 M0B | Auditer pipeline_runs.case_id orphelins → supprimer si sans valeur → VALIDATE CONSTRAINT |

Commande de validation future :
```sql
ALTER TABLE pipeline_runs
  VALIDATE CONSTRAINT fk_pipeline_runs_case_id;
```

Commande d'audit orphelins :
```sql
SELECT pr.id, pr.case_id
FROM pipeline_runs pr
LEFT JOIN cases c ON c.id = pr.case_id
WHERE c.id IS NULL;
```

---

## Tables ambiguës — noms réels à confirmer avant migrations futures

| Nom référencé dans le code | Statut | Fichier source | Note |
|---|---|---|---|
| `public.offers` | présente — créée par 002_add_couche_a | `src/couche_a/pipeline/service.py:preflight` | aucune action requise |
| `public.scoring_configs` | À confirmer | `src/couche_a/scoring/engine.py` | Chargement des poids scoring |
| `public.criteria` | Existante (migration antérieure) | `src/couche_a/criteria/service.py` | Colonne `is_essential` (pas `is_eliminatory`) |
| `public.pipeline_runs` | créée par 032_create_pipeline_runs.py | `src/couche_a/pipeline/service.py` | FK case_id NOT VALID — M0B |
| `public.analysis_summaries` | créée par 035 | `src/couche_a/analysis_summary/engine/service.py` | Append-only, trigger DB |
| `public.committee_snapshots` | À confirmer | `src/couche_a/committee/snapshot.py` | Snapshot scellé comité |
| `public.audit_log` | Absente — PROBE-SQL-01 M0B | — | Trigger append-only en attente |
| `public.score_history` | Absente — PROBE-SQL-01 M0B | — | Trigger append-only en attente |
| `public.elimination_log` | Absente — PROBE-SQL-01 M0B | — | Trigger append-only en attente |
| `public.decision_history` | Absente — PROBE-SQL-01 M0B | — | Trigger append-only en attente |
| `public.submission_registries` | Absente — PROBE-SQL-01 M0B | — | Triggers SRE attachés à M16A |
| `public.submission_registry_events` | Absente — PROBE-SQL-01 M0B | — | Triggers SRE attachés à M16A |
| `public.mercurials` | Absente — PROBE-SQL-01 M0B | — | Index conditionnel 036 |

---

## Tests absents sur invariants critiques

| Invariant | Statut couverture | Note |
|---|---|---|
| `public.offers` preflight complet | Tests SKIPPED | Table présente (002_add_couche_a) — skipped par configuration |
| SLA-B extraction (Tesseract/Azure) | 2 tests SKIPPED (`test_sla_classe_b_has_queue`) | Queue déclarée, non implémentée — M10A |
| SLA-A timing 60s | 1 test SKIPPED (`test_sla_classe_a_60s`) | Test de performance désactivé |
| Market signal impact scoring | 1 test SKIPPED | Hors scope M0 |
| LLM router (`llm_router.py`) | Absent | Module non créé — défini dans freeze V4.1.0, M10A |
| `ExtractionField` / `TDRExtractionResult` | Absent | Modèles définis dans freeze V4.1.0, M10A |
| Annotation protocol | Absent | Hors scope beta |
| VALIDATE CONSTRAINT fk_pipeline_runs_case_id | Absent | Après nettoyage données orphelines |

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

---

## Types PK non conformes au freeze (text vs uuid)

| Table | Colonne | Type réel | Type freeze | Action post-beta |
|---|---|---|---|---|
| procurement_references | id | text | UUID | Normaliser UUID — migration dédiée post-beta |
| documents | id | text | UUID | Normaliser UUID — migration dédiée post-beta |
| committee_members | PK | member_id | id | Aligner nom sur freeze — renommer post-beta |

---

## Colonnes ajoutées nullable (backfill requis)

| Table | Colonne | Ajouté par | Statut | Action |
|---|---|---|---|---|
| documents | sha256 | 036_db_hardening | nullable | Backfill hash SHA256 fichiers existants → ALTER COLUMN SET NOT NULL |

Commande backfill (hors scope M0B) :
```sql
UPDATE documents
SET sha256 = encode(digest(storage_uri, 'sha256'), 'hex')
WHERE sha256 IS NULL;
-- À valider avec données réelles avant NOT NULL
```

---

## Risque de flakiness CI multi-worker — test_upgrade_downgrade

| Fichier | Fonction | Risque | Priorité |
|---|---|---|---|
| `tests/couche_a/test_migration.py` | `_restore_schema` | Écriture `alembic_version` non atomique avec les DDL 002 → 036 | Faible (CI séquentielle) |

**Détail :** `_restore_schema` s'exécute en deux transactions séparées :
1. `migration_002.upgrade(engine)` — crée les tables (`engine.begin()` propre)
2. `engine.begin()` — stamp `alembic_version = 036` + colonnes critiques

**Fenêtre de risque :** entre les deux `BEGIN`, `alembic_version` = état post-downgrade (036 déjà stamped ou vide) mais le schéma est dans l'état 002 (sans `sha256`, sans `document_id`, etc.). Un worker parallèle lisant `alembic_version = 036` trouverait un schéma incomplet.

**Mitigation actuelle :** CI séquentielle (pas de `pytest-xdist -n auto`). Si multi-worker activé → refactoriser `_restore_schema` en une seule transaction avec `engine.begin()`.

---

## Dettes d'environnement

| Item | Local | Cible repo | Action |
|---|---|---|---|
| Python | 3.11.0 | 3.11.9 (runtime.txt) | Aligner env local avant M1 |
| REVOKE app_user | app_user absent (PROBE-SQL-01 M0B) | Rôle DB à créer | Reporté M1 |

---

## Dettes M1 — Security Baseline

### DETTE-M1-01 — `users.id` = integer (legacy)

| Attribut | Valeur |
|---|---|
| État réel | `id INTEGER` (auto-increment) |
| Freeze cible | `id UUID DEFAULT gen_random_uuid()` |
| Bloquant pour | FK UUID vers `users` dans schéma cible |
| Action | Migration dédiée post-beta avec backfill complet |
| Milestone cible | Post-beta ou dédié (décision humaine requise) |
| Risque | Toutes les FK pointant vers `users.id` à recréer lors du basculement |

**Extension M1B — `actor_id` FK reportée (ADR-M1B-001)** :
- `audit_log.actor_id` est `TEXT` nullable — pas de FK formelle vers `users(id)`
- Motif : `users.id` est `INTEGER`, incompatible avec UUID cible du freeze
- La FK `actor_id → users(id)` sera ajoutée lors de la résolution de cette dette
- Certaines actions système (jobs, triggers) n'ont pas d'acteur humain → nullable assumé

### DETTE-M1-02 — Double système auth (cohabitation intentionnelle)

| Attribut | Valeur |
|---|---|
| Legacy | `src/auth.py` — opérationnel (TTL 8h, `role_id` int, passlib) |
| V4.1.0 | `src/couche_a/auth/` — nouveau moteur (30min/7j, `jti`, rotation) |
| Cohabitation | Assumée et intentionnelle — décision CTO 2026-02-27 |
| Action | Basculement complet à **M2 UNIFY SYSTEM** |
| Condition | Décision humaine explicite avant toute bascule |
| Tests legacy | `tests/test_rbac.py` — 5 tests sur le système legacy (non modifiés) |

### DETTE-M1-03 — `users.created_at` = TEXT (legacy)

| Attribut | Valeur |
|---|---|
| État réel | `created_at TEXT` |
| Freeze cible | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` |
| Bloquant pour | Requêtes temporelles sur `users`, ORDER BY dates |
| Action | `ALTER TYPE` + backfill post-beta |
| Milestone cible | Lors de la migration dédiée `users` (DETTE-M1-01) |

### DETTE-M1-04 — `users.role_id` = integer FK → `roles` (legacy)

| Attribut | Valeur |
|---|---|
| État réel | `role_id INTEGER FK → roles(id)` |
| Freeze cible | `role TEXT CHECK (role IN ('admin','manager','buyer','viewer','auditor'))` |
| Cohabitation | `role TEXT` ajouté en M1 (cohabite avec `role_id`) |
| Action | `DROP COLUMN role_id` lors du basculement M2 (après bascule auth) |
| Condition | DETTE-M1-02 résolue en premier |
