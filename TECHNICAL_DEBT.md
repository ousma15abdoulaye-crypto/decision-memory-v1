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

### DETTE-M1-02 — Double système auth ✅ SOLDÉE — M2

| Attribut | Valeur |
|---|---|
| ~~Legacy~~ | ~~`src/auth.py` — opérationnel (TTL 8h, `role_id` int, passlib)~~ |
| V4.1.0 | `src/couche_a/auth/` — moteur unique · tous endpoints migrés |
| Statut | **SOLDÉE** — `src/auth.py` supprimé · commit `971af4a` |
| Date | 2026-02-28 |
| CI finale | 574 passed · 36 skipped · 0 failed |
| Commits M2 | `9e39353` → `971af4a` (9 commits) |
| Tests | `tests/test_rbac.py` · `tests/test_auth.py` — migrés V4.1.0 · 574 passed |

### DETTE-M1-03 — `users.created_at` = TEXT (legacy) ✅ SOLDÉE — M2B

| Attribut | Valeur |
|---|---|
| État réel post-M2B | `created_at TIMESTAMPTZ` — local + prod Railway |
| Migration | `039_hardening_created_at_timestamptz` · commit `206361d` |
| Cast utilisé | `USING created_at::timestamp AT TIME ZONE 'UTC'` |
| Downgrade | `to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US')` |
| Statut | **SOLDÉE** — 2026-02-26 · M2B |
| Prod Railway | `data_type = timestamp with time zone` · `alembic_version = 039` |

### DETTE-M1-04 — `users.role_id` = integer FK → `roles` (legacy) — ACTIVE · DROP BLOQUÉ

| Attribut | Valeur |
|---|---|
| État réel | `role_id INTEGER FK → roles(id)` — colonne toujours présente en DB |
| Freeze cible | `role TEXT CHECK (role IN ('admin','manager','buyer','viewer','auditor'))` |
| Fait en M2 | Lectures de rôle → `UserClaims.role` (moteur V4.1.0) · `role TEXT` utilisé dans tokens |
| Fait en M2 | Role mapping `procurement_officer → buyer` — commit `0cb2a06` |
| Fait en M2 | `create_user(role_id=2)` intentionnellement conservé (schéma inchangé M2) |
| Statut M2B | **ACTIVE — DROP BLOQUÉ** — 7 usages runtime confirmés par PROBE 3 M2B |
| Usages runtime | `src/auth_router.py:83` · `src/api/auth_helpers.py` (6 usages) |
| Condition DROP | Extinction usages + CI verte + backup Railway + GO humain explicite |
| Périmètre | Post-M2B — conditions non réunies en M2B |

---

## Dettes M2 — Unify Auth System

### DETTE-M2-01 — Hash admin migration 004 ✅ FERMÉE post-M2

| Attribut | Valeur |
|---|---|
| Origine | `alembic/versions/004_users_rbac.py` — seed admin user |
| Symptôme initial | Smoke M2 utilisait email comme username (`admin@dms.local`) → 401 incorrect |
| Analyse post-M2 | Hash en prod = `$2b$12$n19Pj...XFvDG` — 60 chars — valide |
| Vérification locale | `bcrypt.checkpw(b"admin123", hash)` → `True` |
| Test prod | `POST /auth/token` `username=admin` `password=admin123` → HTTP 200 · `role=admin` |
| Cause réelle de DETTE-M2-01 | Le smoke utilisait `admin@dms.local` au lieu de `username=admin` — field mismatch |
| Statut | **FERMÉE** — hash correct · login admin fonctionnel |
| Note résiduelle | Le smoke script `_smoke_m2.py` crée des comptes en prod — voir DETTE-M2-04 |

### DETTE-M2-02 — `conditional_limit` désactivé (no-op) — rate limiting per-route hors service

| Attribut | Valeur |
|---|---|
| Origine | `src/ratelimit.py` — `conditional_limit` wrappait `async def` dans `sync def` → coroutine non awaitée |
| Symptôme Railway | `RuntimeWarning: coroutine 'login' was never awaited` · `ResponseValidationError 500` |
| Fix M2 | `conditional_limit` rendu no-op (`return func`) — rate limits per-route désactivés |
| Protections restantes | Limite globale `100/minute` (slowapi middleware) — active |
| Décision bcrypt | **Définitive** — `passlib[bcrypt]` conservé dans `requirements.txt` pour rétrocompatibilité mais non utilisé pour hash/verify. `bcrypt` direct (`bcrypt==4.2.0`) est le chemin de code actif. La dépendance `passlib[bcrypt]==1.7.4` peut être retirée en M3 après audit complet des imports. |
| Action M2B / M3 | Réécrire `conditional_limit` en version native `async` OU supprimer la feature et rester sur le middleware global |
| Priorité | P2 — protection globale active · pas bloquant fonctionnel |

### DETTE-M2-04 — Comptes smoke créés en base de données prod ✅ SOLDÉE — M2B

| Attribut | Valeur |
|---|---|
| Origine | `scripts/_smoke_m2.py` — comptes smoke + case créés en prod pendant M2 |
| Supprimés | `users.id=10` (`smoke_0b6609bc@smoke-test.com`) + `cases.id=c035e6fb...` (`Smoke M2`) |
| Méthode | DELETE sur IDs explicites validés CTO — séquence case → user (FK respectée) |
| Post-DELETE | `total_users = 1` (admin) · `total_cases = 0` · FK NOT VALID = 0 rows |
| Statut | **SOLDÉE** — 2026-02-26 · M2B · ACTE 6 |
| Architecture | Staging Railway séparé planifié M3 pour éviter les smoke en prod |

**SQL nettoyage Railway console :**
```sql
-- Vérifier avant DELETE
SELECT id, username, email FROM users
WHERE email LIKE '%@smoke-test.com'
   OR email LIKE '%@test.com'
   OR username LIKE 'smoke_%'
   OR username LIKE 'dbg_%'
   OR username LIKE 'test_%'
ORDER BY id;

-- Exécuter si preview correct
DELETE FROM users
WHERE email LIKE '%@smoke-test.com'
   OR email LIKE '%@test.com'
   OR username LIKE 'smoke_%'
   OR username LIKE 'dbg_%'
   OR username LIKE 'test_%';
-- Résultat attendu : DELETE 9
```

### DETTE-M2-03 — 36 tests skipped non audités

| Attribut | Valeur |
|---|---|
| Origine | Tests créés en M0/M0B/M1 pour features non encore implémentées |
| Nombre | 36 skipped (574 passed · 36 skipped · 0 failed — CI M2 finale) |
| Catégories identifiées | Voir tableau ci-dessous |
| Action M2B | Audit complet · classifier chaque skip · éliminer les orphelins |
| Priorité | P2 — pas bloquant CI · risque de masquage de régressions |

**Tableau de classification provisoire (36 skipped) :**

| Catégorie | Fichiers / Tests | Type |
|---|---|---|
| Lock committee DB (psycopg2 absent) | `tests/db_integrity/test_lock_committee_db_level.py` (4 tests) | Skip légitime — dépendance env |
| SLA-A performance 60s | `tests/pipeline/test_sla_classe_a_60s.py` (1 test) | Skip légitime — feature M10A |
| SLA-B queue asynchrone | `tests/pipeline/test_sla_classe_b_has_queue.py` (2 tests) | Skip légitime — feature M10A |
| Magic bytes upload | `tests/invariants/phase0/test_upload_magic_bytes.py` (5 tests) | Skip légitime — feature non implémentée |
| Boundary couche A/B | `tests/invariants/test_couche_a_b_boundary.py` + `test_no_couche_b_import_in_couche_a.py` (2 tests) | À auditer — SCORING-ENGINE dépendance |
| Market signal rules | `tests/market_signal/test_market_signal_rules.py` (6 tests) | Skip légitime — feature Couche B |
| Survey validity | `tests/market_signal/test_survey_validity.py` (4 tests) | Skip légitime — feature Couche B |
| Scoring independence | `tests/scoring/test_scores_independent_of_couche_b.py` + `test_market_signal_no_impact_on_scores.py` (3 tests) | Skip légitime — Market Signal absent |
| Doctrine échec exports | `tests/generation/test_doctrine_echec_exports.py` (3 tests) | Skip CI guard — BLOQUE CI si actif |
| Raw offer in scoring | `tests/normalisation/test_no_raw_offer_in_scoring.py` (2 tests) | Skip CI guard — BLOQUE CI si actif |
| Append-only tables absentes | `tests/test_m0b_db_hardening.py::test_append_only_conditional_absent_tables` (1 test) | À auditer — tables créées en M1B |
| Upload lot_id | `tests/test_upload.py::test_upload_offer_with_lot_id` (1 test) | À auditer — table `lots` absente |
| Rate limit upload | `tests/test_upload_security.py::test_rate_limit_upload` (1 test) | Skip TESTING mode — DETTE-M2-02 liée |
| Dashboard dépôt | `tests/couche_a/test_endpoints.py::test_depot_dashboard_and_export` (1 test) | **Légitime M2B** — skip corrigé → "prévu M5" · commit `1f8fd32` |

---

## Dettes M2B — Hardening DB + Migrations

### DETTE-ALEMBIC-01 — Downgrades migrations récentes ✅ FERMÉE — M2B

| Attribut | Valeur |
|---|---|
| Origine | Downgrades 037 et 038 non testés fonctionnellement avant M2B |
| Preuve | Cycle `alembic downgrade -1` → `alembic upgrade head` → `pytest` : **574 passed · 0 failed** |
| Migration 037 downgrade | Partiel par doctrine M0B — `token_blacklist` droppée · colonnes `role/organization` conservées (idempotent) |
| Migration 038 downgrade | Complet — `audit_log` + séquence + fonctions + triggers droppés |
| Statut | **FERMÉE** — 2026-02-26 · PROBE 6 M2B |

### DETTE-M0B-01 — FK NOT VALID `pipeline_runs.case_id` ✅ SOLDÉE PROD — M2B

| Attribut | Valeur |
|---|---|
| Contrainte | `fk_pipeline_runs_case_id` · `convalidated = false` |
| DB locale | NOT VALID — **assumé et documenté** |
| DB locale | NOT VALID — assumé · trigger append-only ADR-0012 empêche purge fixtures · DETTE-FIXTURE-01 |
| Prod Railway | `convalidated = True` — `orphan_count prod = 0` · VALIDATE exécuté ACTE 6 |
| Statut | **SOLDÉE sur prod** — 2026-02-26 · M2B · FK NOT VALID = 0 rows confirmé |
| ADR | `docs/adr/ADR-M2B-001_hardening_db_scope.md` |

### DETTE-FIXTURE-01 — Fixtures tests `pipeline_runs` non conformes — OUVERTE

| Attribut | Valeur |
|---|---|
| Origine | Fixtures écrites avant existence de la FK `fk_pipeline_runs_case_id` (contexte M0B) |
| Symptôme | Les `pipeline_runs` fixtures référencent des `case_id` inexistants dans `cases` |
| Effet | FK NOT VALID non validable en local · VALIDATE CONSTRAINT impossible sans violer ADR-0012 |
| Action | Refactorer les fixtures pour créer les `cases` correspondants avant les `pipeline_runs`, ou utiliser des `case_id` existants |
| Périmètre | Post-M2B · M3 ou milestone dédié fixtures |
| Priorité | P2 — non bloquant prod |
