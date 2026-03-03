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

### DETTE-FIXTURE-01 — Fixtures tests `pipeline_runs` non conformes — SOLDÉE

| Attribut | Valeur |
|---|---|
| Statut | **SOLDÉE** — M2B-PATCH · 2026-02-28 |
| Origine | Fixtures écrites avant existence de la FK `fk_pipeline_runs_case_id` (contexte M0B) |
| Résolution | Probe M2B-PATCH confirme que les tests actuels utilisent `case_factory()` (case réel) avant tout INSERT dans `pipeline_runs`. Les tests avec `case_id` fantôme (`ghost-case-inexistant`, `00000000-...`) utilisent `pytest.raises(ForeignKeyViolation)` — tests délibérés de rejet FK, aucun orphelin créé. Les 166 orphelins historiques sont du legacy pré-FK (non supprimables ADR-0012). |
| Solution | `case_factory()` réutilisée dans tous les tests pipeline · isolation transactionnelle via rollback dans `db_transaction` · aucun `DELETE teardown` sur `pipeline_runs` |
| CI M2B-PATCH | 57 passed · 0 failed sur `pytest -k pipeline` |

---

## Notes architecturales M3

### NOTE-ARCH-M3-001 — Schéma géographique normalisé 7 tables (M3 GEO MASTER MALI)

| Attribut | Valeur |
|---|---|
| Décision | Schéma normalisé 7 tables remplace l'approche monolithique `geo_master` |
| Tables | `geo_countries`, `geo_regions`, `geo_cercles`, `geo_communes`, `geo_localites`, `geo_zones_operationnelles`, `geo_zone_commune_mapping` |
| Migration | `040_geo_master_mali` — raw SQL (`op.execute()`) — downgrade explicite |
| Neutralité | Schéma agnostique : zéro DEFAULT organisationnel, zéro hardcode ONG |
| Colonne-clé | `organisation_code TEXT NOT NULL` (pas de DEFAULT) sur `geo_zones_operationnelles` — unicité `(code, organisation_code)` |
| Zones M3 | `geo_zones_operationnelles` existe au schéma mais n'est pas seedée en M3 — données chargées dans un jalon ultérieur |
| Endpoint | `GET /geo/zones/{zone_id}/communes` hors périmètre M3 — reporté (pas d'API zombie) |
| Milestone | M3 · 2026-03-01 |

---

### DETTE-ARCH-01 — Hardcodes organisationnels legacy hors périmètre M3

| Attribut | Valeur |
|---|---|
| Statut | **ACTIVE** |
| Nature | Occurrences organisationnelles hardcodées (`SCI`, `WFP`, `UNICEF`, etc.) détectées hors périmètre M3 |
| Fichiers concernés | `alembic/versions/003_add_procurement_extensions.py` · `alembic/versions/004_users_rbac.py` · `src/templates/pv_template.py` · `src/couche_a/routers.py` · `src/templates/cba_template.py` · `src/evaluation/profiles.py` |
| Règle | Migrations historiques non réécrites — faits historiques opposables |
| Action | Corriger uniquement dans le code applicatif futur concerné ; ne pas réécrire les migrations 003/004 et antérieures |
| Détecté | PROBE ACTE 1 — MANDAT CORRECTIF M3 · 2026-03-01 |

---

### TD-001 · vendor_id MAX()+1 non atomique

| Attribut | Valeur |
|---|---|
| Statut | **ACTIVE** |
| Sévérité | Modérée |
| Contexte | M4 import séquentiel opérateur |
| Fichier | `src/vendors/repository.py` · `get_next_sequence()` |

**Problème :**
Le calcul du prochain numéro de séquence par région utilise
`MAX(CAST(SPLIT_PART(vendor_id,'-',4) AS INTEGER)) + 1`.
Cette opération n'est pas atomique.
Deux imports parallèles dans la même région peuvent obtenir
la même séquence et provoquer une collision UNIQUE sur `vendor_id`.

**Mitigation M4 :**
Import séquentiel · un opérateur · un process.
Risque faible mais réel si jamais lancé en parallèle.

**Solution M5+ :**
- Option A : `pg_try_advisory_xact_lock(hashtext(region_code))`
- Option B : table `vendor_sequences(region_code TEXT PK, current_seq INT)`
  avec `SELECT current_seq FROM vendor_sequences WHERE region_code = :rc FOR UPDATE`
  puis `UPDATE vendor_sequences SET current_seq = current_seq + 1`

**Propriétaire :** CTO · à résoudre avant tout import concurrent.

---

## TD-002 · index GIN trigram pour vendor_match_rate (mis à jour 2026-03-02)

| Attribut | Valeur |
|---|---|
| Sévérité | Modérée |
| Contexte | DoD M15 exige `vendor_match_rate ≥ 60%` |
| Fichier | `src/vendors/repository.py` · `match_vendor_by_name()` (à créer M11) |

**IMPORTANT :** `pg_trgm` est **déjà activée** via `005_add_couche_b`.
Ne pas recréer l'extension. Elle est disponible.

**Ce qui reste à implémenter avant M11 :**

1. Index GIN trigram sur `vendor_identities(canonical_name)` :
   ```sql
   CREATE INDEX idx_vi_canonical_trgm
   ON vendor_identities
   USING gin(canonical_name gin_trgm_ops);
   ```

2. `match_vendor_by_name()` dans `src/vendors/repository.py` :
   - Logique : `rapidfuzz WRatio ≥ 80` sur `canonical_name` + `aliases`
   - Retour : `vendor_id` · score · méthode (exact / fuzzy / unresolved)
   - RÈGLE-20 : score < seuil → UNRESOLVED explicite · jamais silencieux

**Mitigation M4 :**
Pas de matching en M4. Déduplication par fingerprint uniquement.

**Propriétaire :** CTO · à activer avant M11.

---

## TD-003 · zones_covered et category_ids vides en M4

| Attribut | Valeur |
|---|---|
| Sévérité | Faible · attendu |
| Contexte | Colonnes ajoutées par PATCH-A · peuplement prévu milestones suivants |
| Fichier | `alembic/versions/m4_patch_a_vendor_structure_v410.py` |

**Situation :**
`zones_covered UUID[] DEFAULT '{}'` et `category_ids UUID[] DEFAULT '{}'`
sont présentes en schéma depuis PATCH-A mais restent vides en M4.

**Plan :**
- `zones_covered` : peuplé en M5 (Mercuriale · couverture géographique fournisseur)
- `category_ids` : peuplé en M6 (Catégories · référentiel achats)

**Action en M4 :** aucune · attendu et documenté.

**Propriétaire :** CTO · suivi M5/M6.

---

## TD-004 · Table vendors legacy hors alembic — **FERMÉE**

| Attribut | Valeur |
|---|---|
| Statut | **FERMÉE** — 2026-03-03 |
| Sévérité | ~~Modérée · bloquante pour renommage vendor_identities → vendors~~ · RÉSOLUE |
| Découverte | PATCH-A probe P2 · 2026-03-02 |
| Résolu par | Migration `m5_pre_vendors_consolidation` · VERDICT A CTO · 2026-03-03 |
| Contexte | Table créée hors alembic ~2026-02-17 · origine inconnue (test ou script pré-M3) |

**Résolution appliquée :**
- vendors legacy (4 colonnes · était vide · 0 lignes confirmé probe 2026-03-03) : **SUPPRIMÉE**
- vendor_identities (référentiel canonique · 34 colonnes) : **RENOMMÉE → vendors**
- Contraintes renommées : `vendor_identities_pkey → vendors_pkey`, `uq_vi_canonical_name → uq_vendors_canonical_name`, etc.
- Index renommés : `idx_vi_canonical → idx_vendors_canonical`, `idx_vi_verification → idx_vendors_verification`
- Toutes les requêtes SQL `vendor_identities` → `vendors` mises à jour dans `src/vendors/repository.py`
- Tests `tests/vendors/*` mis à jour pour référencer `vendors`

**Données prod préservées :**
- 661 lignes prod survivent sous `vendors` (ex `vendor_identities`)
- Aucune FK cassée (market_signals.vendor_id : colonne sans FK formelle · non bloquant)

**Propriétaire :** CTO · FERMÉE.

---

---

## Dettes pré-M5 — Audit architecture agent (ADR-M5-PRE-001)

> Identifiées lors de l'audit technique de clôture sprint M4/PATCH.
> Ref complète : `docs/adr/ADR-M5-PRE-001_pre-m5-hardening.md`
> Date : 2026-03-02

### TD-005 · DATABASE_URL évalué à l'import module — ACTIF · planifié Phase 1

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIF · Phase 1 M5** |
|| Sévérité | Haute |
|| Fichier | `src/db/core.py` ligne 42 |
|| Ref ADR | ADR-M5-PRE-001 § D1.1 |

**Problème :**
```python
_DATABASE_URL = _get_database_url()  # ligne 42 — exécuté à l'import
```
Tout environnement sans `DATABASE_URL` (build CI sans DB, test unitaire pur)
plante à l'import du module. Couplage startup/runtime inacceptable.

**Solution :**
Lazy init via `_get_or_init_db_url()` avec cache `_DB_URL_CACHE`.
L'évaluation se fait au premier appel `get_connection()`, pas à l'import.

**Résolution :** Lazy init `_get_or_init_db_url()` + `_DB_URL_CACHE`. Commit bb3aa09. 726 passed CI.

**Propriétaire :** CTO · FERMÉE.

---

### TD-006 · SELECT * exposé en API vendor — FERMÉE

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIF · Phase 1 M5** |
|| Sévérité | Haute (données sensibles) |
|| Fichier | `src/vendors/repository.py` · `list_vendors()` · `get_vendor_by_id()` |
|| Ref ADR | ADR-M5-PRE-001 § D1.2 |

**Problème :**
`SELECT * FROM vendor_identities` expose automatiquement toute nouvelle colonne
via `GET /vendors`, y compris `nif`, `rib`, `rccm`, `verified_by`, `verification_source`.
En contexte Mali avec données fournisseurs réelles — risque RGPD/sécurité.

**Solution :**
Constante `_PUBLIC_COLUMNS` dans `repository.py` avec liste explicite des colonnes safe.
Endpoint `/vendors/{id}/details` (admin RBAC, M6+) pour les colonnes complètes.

**Résolution :** `_PUBLIC_COLUMNS` dans `repository.py`. NIF/RIB/RCCM exclus de l'API publique. Commit bb3aa09.

**Propriétaire :** CTO · FERMÉE.

---

### TD-007 · Absence de connection pooling — ACTIF · planifié Phase 2

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIF · Phase 2 M6+** |
|| Sévérité | Haute (performance sous charge) |
|| Fichier | `src/db/core.py` · `get_connection()` |
|| Ref ADR | ADR-M5-PRE-001 § D2.1 |

**Problème :**
Chaque `get_connection()` ouvre/ferme une connexion psycopg raw.
Railway Starter PostgreSQL = 25 connexions max.
À charge >10 req/s concurrentes, saturation et `OperationalError` inévitables.

**Solution :**
`psycopg_pool.ConnectionPool` synchrone (`min_size=2, max_size=10`).
Instance singleton initialisée au démarrage FastAPI.
Interface `_ConnectionWrapper` inchangée — zéro impact callers.

**Mitigation actuelle :** faible charge opérateur unique. Acceptable jusqu'à M6.

**Propriétaire :** CTO · résoudre avant activation API write ou charge >1 opérateur.

---

### TD-008 · ImportError silencieux dans main.py — FERMÉE

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIF · Phase 1 M5** |
|| Sévérité | Modérée |
|| Fichier | `src/api/main.py` · 12 blocs try/except ImportError |
|| Ref ADR | ADR-M5-PRE-001 § D1.3 |

**Problème :**
12 blocs `try: from x import y except ImportError: pass` avalent silencieusement
les bugs réels (circular imports, NameError, dépendances manquantes).
Un router peut disparaître en production sans alerte.

**Solution :**
- Routers obligatoires (auth, cases, health) : import direct sans try/except.
- Routers optionnels : conserver try/except mais logger WARNING avec détail.
- `startup_check()` dans `@app.on_event("startup")` liste les routers actifs.

**Résolution :** Routers obligatoires import direct. Optionnels: logger WARNING. `startup_check()` au démarrage. Commit bb3aa09.

**Propriétaire :** CTO · FERMÉE.

---

### TD-009 · Chaîne Alembic hors convention séquentielle — ACTIF · BLOQUANT M5

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIF · BLOQUANT M5** |
|| Sévérité | Haute |
|| Fichiers | `m4_patch_a_vendor_structure_v410.py` · `m4_patch_a_fix.py` |
|| Ref ADR | ADR-M5-PRE-001 § D0.1 |

**Problème :**
Les deux dernières migrations ne suivent pas la convention `NNN_nom.py`.
La prochaine migration `044_` DOIT déclarer `down_revision = "m4_patch_a_fix"`
explicitement (nom complet, pas numéro). Si un agent oublie et met
`down_revision = "043_vendor_activity_badge"`, le résultat est un **double head**
et un crash deploy Railway identique à PROD-HOTFIX-001.

**Solution :**
- Ne PAS renommer les fichiers existants (déployés en prod — règle absolue).
- Toute migration `04X_` vérifie `alembic heads` avant push.
- `down_revision = "m4_patch_a_fix"` dans `044_consolidate_vendors.py`.
- Documenter dans `docs/dev/migration-checklist.md`.

**Vérification immédiate :**
```bash
alembic heads
# DOIT retourner exactement 1 résultat
```

**Propriétaire :** CTO · vérifier avant premier commit M5.

---

> **MISE À JOUR 2026-03-03 — PARTIELLEMENT FERMÉE**
>
> La chaîne contient maintenant 3 migrations hors convention numérique post-freeze V4.1.0 :
> `m4_patch_a_vendor_structure_v410` → `m4_patch_a_fix` → `m5_pre_vendors_consolidation` (HEAD)
>
> Chaîne propre confirmée : `alembic heads` → 1 seul résultat.
> Cycle down/up validé x2 · idempotent.
> down_revision documenté dans `docs/dev/migration-checklist.md` section 8.
> Prochain down_revision : `m5_pre_vendors_consolidation`
> Statut : PARTIELLEMENT FERMÉE · résidu non bloquant · surveillance continue.
> Update 2026-03-03 post-merge PR #152 : tête = m5_pre_vendors_consolidation
> Tag : v4.1.0-m5-pre-hardening
> Prochain down_revision M5 : m5_pre_vendors_consolidation

---

## TD-010 · market_signals.vendor_id type mismatch INTEGER vs UUID

|| Attribut | Valeur |
||---|---|
|| Statut | **FERMÉE** — 2026-03-03 · M5-FIX |
|| Sévérité | ~~Haute~~ · RÉSOLUE |
|| Découverte | Sprint M5-PRE · handover HANDOVER_M5PRE_TRANSMISSION.md § F2 |
|| Fichier | `alembic/versions/m5_fix_market_signals_vendor_type.py` |
|| ADR | `docs/adr/ADR-M5-FIX-001.md` |

**Résolution :**
- `market_signals.vendor_id` : `INTEGER` → `UUID`
- FK **non recréée dans la migration** : `market_signals` est protégée append-only
  (`FOR KEY SHARE` bloqué lors de tout `DELETE FROM vendors`, quelle que soit l'action FK)
  → Contrainte logique documentée dans `docs/adr/ADR-M5-FIX-001.md`
  → FK appliquée en prod via `scripts/apply_fk_prod.py` (`ON DELETE RESTRICT`)
- Index `idx_signals_vendor` recréé sur type UUID (idempotent)
- 4 gardes upgrade idempotentes : Garde 0 (déjà UUID → skip) · Garde 1 (table vide) · Garde 2 (type INTEGER) · Garde 3 (vendors.id UUID)
- Downgrade honnête : bloqué si `vendor_id` non NULL · DROP FK si présente
- 6 tests invariants dans `tests/db_integrity/test_m5_fix_market_signals.py`

**Résidu documenté :** FK enforced uniquement en prod (Railway). En local, contrainte logique seulement.

**Propriétaire :** CTO · FERMÉE.

---

## TD-011 · Protection append-only market_signals incompatible avec FK locale

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIVE** |
|| Sévérité | Moyenne |
|| Découverte | Sprint M5-FIX · 2026-03-03 · STOP-5 + STOP-6 |
|| Impact | FK `market_signals → vendors` enforced uniquement en prod |

**Description :**
`market_signals` est protégée append-only (REVOKE UPDATE ou équivalent).
PostgreSQL déclenche `SELECT ... FOR KEY SHARE` sur `market_signals` lors de tout
`DELETE FROM vendors`, quelle que soit l'action FK (RESTRICT · SET NULL · CASCADE · NO ACTION).
Ce verrou est bloqué par la protection append-only dans l'environnement local.

**Conséquence :** La FK `market_signals_vendor_id_fkey` ne peut pas exister localement.
Les tests qui font `DELETE FROM vendors` en teardown échoueraient avec `InsufficientPrivilege`.

**Mitigation actuelle :** FK absente de la migration · appliquée manuellement en prod via `scripts/apply_fk_prod.py`.

**Action recommandée M5+ :** Comprendre et documenter exactement quelle protection est appliquée
sur `market_signals` (trigger, REVOKE, RLS) et évaluer si elle peut être assouplie pour le rôle de test
sans compromettre l'intégrité en prod.

---

## TD-012 · Contrainte chk_vendor_id_format limitée à 4 chiffres (9999 vendors/région max)

|| Attribut | Valeur |
||---|---|
|| Statut | **ACTIVE** |
|| Sévérité | Basse (locale) · Haute (prod long terme) |
|| Découverte | Sprint M5-FIX · 2026-03-03 · PIÈGE-9 |
|| Fichier | Contrainte DB `vendors.chk_vendor_id_format` |

**Description :**
Le format `DMS-VND-{REGION}-{SEQ:04d}-{CHK}` avec contrainte `^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$`
limite chaque région à exactement 4 chiffres (0001–9999).
Après saturation du compteur (runs intensifs de debug ou import massif), les inserts `CheckViolation`.

**Symptôme local :** `DMS-VND-BKO-10000-M` → `CheckViolation: chk_vendor_id_format`

**Action recommandée M5+ :**
- Étendre la regex à `[0-9]{4,6}` pour permettre jusqu'à 999999 vendors/région
- Et/ou implémenter une table `vendor_sequences` (résout aussi TD-001)

---

### DETTE-UTC-01 — Timestamps naïfs code applicatif — SOLDÉE

| Attribut | Valeur |
|---|---|
| Statut | **SOLDÉE** — M2B-PATCH · 2026-02-28 |
| Découverte | PR#139 review Copilot — commentaire post-merge M2B |
| Solution | `datetime.now(UTC)` remplace `datetime.utcnow()` dans 8 fichiers `src/` (`UTC` alias de `timezone.utc` importé depuis `datetime`) |
| Fichiers corrigés | `src/api/cases.py` · `src/couche_a/routers.py` · `src/core/dependencies.py` · `src/couche_a/scoring/models.py` · `src/couche_a/scoring/engine.py` · `src/api/analysis.py` · `src/couche_a/extraction.py` · `src/business/templates.py` |
| Exclu intentionnel | `src/api/auth_helpers.py` — hors périmètre M2B-PATCH (DETTE-M1-04 active) |
| Résidu | 2 occurrences `utcnow()` dans `auth_helpers.py` — accepté · traitement avec DETTE-M1-04 |
