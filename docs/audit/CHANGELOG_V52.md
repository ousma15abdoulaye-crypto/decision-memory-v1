# DMS V5.2 — Changelog Reconstruction

**Branche :** `fix/v51-p1-corrections-audit`
**Période :** 2026-04-09
**Statut :** P1 ✅ P2 ✅ P3 ✅ — P4 Frontend 🔜

---

## Vue d'ensemble

```
PHASE  ITEM                        STATUT    DURÉE
─────  ──────────────────────────  ────────  ──────
P1     Fondations DB + Auth         ✅        2.25j
P2.1-4 Investigation + Bridge RBAC  ✅        1.25j
P2.5a  Investigation scellement     ✅        0.5j
P2.5-R1 Radiographie V4.1          ✅        0.5j
P2.5b-R10 Seal checks branchés     ✅        0.5j
P2.5b-R3  market_delta_pct         ✅        0.75j
P2.5b-R1  Bridge M14→M16           ✅        1j
P3     Observabilité + Agent        ✅        1j
P2.6   Validation + Cleanup         ✅        0.5j
──────────────────────────────────────────────────
       TOTAL                        ✅        8j
─────  ──────────────────────────  ────────  ──────
P4     Frontend                     🔜        ~5-7j
P5     CI/Tests complets            🔜        ~1j
```

---

## P1 — Fondations DB + Auth (2.25j)

### P1.1 — Triggers d'immutabilité
**Fichier :** `alembic/versions/v52_p1_001_immutability_triggers.py`

| Trigger | Table | Invariant | Description |
|---|---|---|---|
| `trg_pv_snapshot_immutable` | `committee_sessions` | INV-W05 | pv_snapshot immutable après premier SET |
| `trg_dm_append_only` | `deliberation_messages` | INV-S03 | Messages de délibération append-only |
| `trg_ac_content_immutable` | `assessment_comments` | INV-S04 | Contenu des commentaires immutable |
| `trg_assessment_history_append_only` | `assessment_history` | INV-W05 | Historique assessments append-only |

### P1.2 — Auto-historisation criterion_assessments
**Fichier :** `alembic/versions/v52_p1_002_assessment_auto_history.py`

- Trigger `trg_assessment_auto_history` sur `criterion_assessments` (AFTER UPDATE)
- Colonnes `assessment_history` étendues : `workspace_id`, `bundle_id`, `criterion_id`, `old_cell_json`, `new_cell_json`, `changed_by_uuid`
- Capture automatique du `changed_by_uuid` depuis GUC `app.current_user`

**Fichier :** `src/middleware/tenant.py` (créé)

- Middleware canonical V5.2
- Pose `app.current_tenant` et `app.current_user` en contextvars Python
- Compatible asyncpg (transactions scoped)

**Fichier :** `src/db/core.py` (modifié)

- `set_config('app.current_user', :uid, true)` sur chaque acquire connection
- `is_local=true` → reset automatique en fin de transaction

### P1.3 — Guard unifié
**Fichier :** `src/auth/guard.py` (réécrit)

- 3 checks en séquence : membership → RBAC → seal protection
- Retourne `dict` (pas `UserClaims`) pour compatibilité asyncpg
- Accepte `revoked_at` : révocation de membres vérifiée
- `_LEGACY_ROLE_MAP` : bridge V4.x → V5.2 (8 rôles legacy mappés)
- `WRITE_PERMISSIONS` : frozenset de 9 permissions d'écriture (inclut `market.write`)

**Fichier :** `src/auth/permissions.py` (corrigé)

- `ROLE_PERMISSIONS` : dict[str, set[str]], 6 rôles, 18 permissions totales
- supply_chain: 15 | finance: 11 | technical: 9 | budget_holder: 9 | observer: 5 | admin: 18
- `agent.query` déplacé de `technical` vers `budget_holder` (correction métier)
- `market.write` ajouté à `WRITE_PERMISSIONS`

### P1.4 — RLS complétée + fix app.current_user async
**Fichier :** `alembic/versions/v52_p1_003_rls_completion.py`

- RLS activé + FORCED sur 25 tables (était partiel sur plusieurs)
- Politique `tenant_isolation` ajoutée pour toutes les tables GROUPE A
- Politique spéciale `plbv_tenant_isolation` pour `price_line_bundle_values` (sous-requête)

**Fichier :** `src/db/async_pool.py` (corrigé)

- Bug : `app.current_user` non posé dans le pool async → trigger P1.2 `changed_by_uuid` = NULL
- Fix : `acquire_with_rls()` pose maintenant `app.user_id` + `app.current_user` depuis contextvar
- `AsyncpgAdapter` : convertit params `:name` → `$N` pour compatibilité asyncpg

---

## P2 — Intégrité Métier (4.5j)

### P2.1 — Routes RBAC + Fix agent.py
**Fichier :** `src/auth/guard.py` (modifié)

- `_LEGACY_ROLE_MAP` : bridge 8 rôles V4.x vers les 6 rôles V5.2
- Compatibilité rétroactive sans modifier les routes V4.x

**Fichier :** `src/api/routers/agent.py` (corrigé)

- Bug crash : `guard()` appelé avec `raw_conn` au lieu de `AsyncpgAdapter` → fix
- Bug crash : `guard()` appelé avec `UserClaims` au lieu de `dict` → fix
- `intent_confidence` transmis au handler `mql_stream_handler` via `handler_kwargs`

**Fichier :** `src/api/routers/market.py` (corrigé)

- Ajout vérification `tenant_id` dans `annotate_market_item`

### P2.5b-R10 — Seal checks branchés

**Fichier :** `src/services/seal_checks.py` (créé)

Collecte TOUTES les erreurs avant de bloquer (pas de fail-fast partiel) :
1. **Quorum** (INV-W01) : ≥4 membres actifs, ≥1 par rôle critique
2. **Poids** (INV-W03) : SUM(ponderation) non-éliminatoires ∈ [99.5, 100.5]
3. **Flags** : 0 assessment_comments.is_flag non résolus
4. **Cohérence M14** : committees.status si legacy_case_id existe (WARNING)

**Fichier :** `src/api/routers/committee_sessions.py` (modifié)

- `run_all_seal_checks()` appelé AVANT `build_pv_snapshot()`
- HTTP 422 si `check_result.passed = False` avec liste complète des erreurs
- Permission corrigée : `committee.manage` → `committee.seal`

### P2.5b-R3 — market_delta_pct calculé (Option B — persisté)

**Fichier :** `alembic/versions/v52_p2_001_price_line_market_delta.py` (créé)

- Colonnes `market_delta_pct NUMERIC` + `market_delta_computed_at TIMESTAMPTZ`
- Index `idx_plbv_delta_stale` pour batch sync

**Fichier :** `src/services/market_delta.py` (refactoré)

- Jointure floue item via `pg_trgm` (seuil similarity 0.55)
- Zone : exact match sur `geo_master`
- `δ = abs(prix_fournisseur − prix_signal) / prix_signal`
- Persisté en arrière-plan (background task) au write, pas à l'affichage

**Fichier :** `src/services/m16_evaluation_service.py` (modifié)

- Retourne `market_delta_pct` + `market_delta_computed_at` dans les bundles

**Fichier :** `src/schemas/m16/api.py` (modifié)

- `PriceLineBundleValueOut` : ajout `market_delta_pct: float | None` + `price_signal`

**Fichier :** `src/api/routers/m16_comparative.py` (modifié)

- Route `POST /api/workspaces/{ws}/m16/refresh-market-deltas` (batch sync)
- Calcul delta retiré du read path (zéro calcul à l'affichage)

### P2.5b-R1 — Bridge M14→M16

**Fichier :** `src/services/m14_bridge.py` (créé)

- Mapping `offer_document_id → bundle_id` via `supplier_bundles`
- Mapping `criterion_key → criterion_id` via `dao_criteria.code`
- Règle non-écrasement : `cell_json->>'score' IS NOT NULL` → SKIP
- Tag `"source": "m14"` dans `cell_json` pour distinguer automatique/manuel
- `BridgeResult` : created/updated/skipped/unmapped_offers/unmapped_criteria/errors

**Fichier :** `src/api/routers/m16_comparative.py` (modifié)

- Route `POST /api/workspaces/{ws}/m16/sync-from-m14` (permission: `evaluation.write`)
- Retourne `BridgeResult` en JSON

---

## P3 — Observabilité + Agent (1j)

### C1 — async_load_cognitive_facts
**Fichier :** `src/api/cognitive_helpers.py` (modifié)

- Bug : `workspace_status_handler` appelait `load_cognitive_facts()` synchrone avec `AsyncpgAdapter`
- Fix : nouvelle fonction `async_load_cognitive_facts(db, workspace_row)` avec `await db.fetch_one()` / `await db.fetch_val()`

**Fichier :** `src/agent/handlers.py` (modifié)

- `workspace_status_handler` utilise maintenant `await async_load_cognitive_facts()`

### C5 — intent_confidence corrigé
**Fichier :** `src/agent/handlers.py` (modifié)

- `mql_stream_handler` accepte `intent_confidence: float = 0.0` en paramètre
- Log dans `mql_query_log.intent_confidence` = valeur du semantic router (pas `mql_result.confidence`)

**Fichier :** `src/api/routers/agent.py` (modifié)

- `handler_kwargs["intent_confidence"] = intent.confidence` pour `MARKET_QUERY`

### C7 — type annotation _extract_article
**Fichier :** `src/mql/param_extractor.py` (modifié)

- `_extract_article` : retour corrigé `str` → `str | None`

### Config — DATABASE_URL validator
**Fichier :** `src/core/config.py` (modifié)

- `validate_database_url` normalise `postgresql+psycopg://` → `postgresql://` avant validation
- Tests pytest `conftest.py` compatibles sans modification

### Tests — 127/127 verts
**Fichiers modifiés :**
- `tests/unit/test_guard_workspace_mocked.py` : `_make_user` retourne `dict`, mocks `AsyncpgAdapter.fetch_one` corrigés, permissions V5.2 (`evaluation.write`, `evaluation.read`)
- `tests/unit/test_permissions.py` : `WRITE_PERMISSIONS` attendu inclut `market.write`
- `tests/conftest.py` : normalisation DATABASE_URL `postgresql+psycopg://`

---

## P2.6 — Validation Production + Cleanup (0.5j)

### État Railway (vérifié 2026-04-09)

| Migration | Statut | Artefact vérifié |
|---|---|---|
| `v52_p1_001_immutability_triggers` | ✅ En production | `trg_pv_snapshot_immutable` présent |
| `v52_p1_002_assessment_auto_history` | ✅ En production | `trg_assessment_auto_history` présent |
| `v52_p1_003_rls_completion` | ✅ En production | 34 tables RLS+FORCE |
| `v52_p2_001_price_line_market_delta` | ✅ En production | colonnes `market_delta_pct`/`market_delta_computed_at` |

**HEAD Alembic Railway :** `v52_p2_001_price_line_market_delta`
**Triggers totaux trg_* :** 89 (dont les 4 nouveaux V5.2)
**Tables RLS+FORCE :** 34

### État des données (Railway)

| Table | Rows | Impact tests |
|---|---|---|
| `market_signals_v2` | 1112 | R3 : données prix disponibles (zones Bamako, Mopti, Sikasso, Gao, Ségou) |
| `price_line_bundle_values` | 0 | R3 test live : pas encore de dossiers saisis |
| `evaluation_documents` | 0 | R1 test live : pas encore de scores M14 |
| `criterion_assessments` | 0 | R1 test live : tables vides, bridge prêt |
| `price_line_comparisons` | 0 | R3 test live : pas de comparatifs prix |
| `committee_sessions` | 7 | R10 : 7 sessions (2 avec PV, 5 non scellées) |
| `process_workspaces` | 62 | |
| `workspace_memberships` (actifs) | 5400 | |
| `dao_criteria` | 66 | R10 poids : 66 critères définis |

### Tests fonctionnels R10/R3/R1

**R10 — Seal checks (TESTABLE sur Railway) :**

Procédure test quorum insuffisant :
```bash
# Trouver un workspace sans quorum (< 4 membres actifs)
# POST /api/workspaces/{ws_id}/committee/seal
# Résultat attendu : HTTP 422
# {
#   "error": "seal_preconditions_failed",
#   "errors": ["Quorum insuffisant : 2/4 membres requis"],
#   "warnings": []
# }
```

**R3 — Market delta (TESTABLE quand prix saisis) :**

```bash
# POST /api/workspaces/{ws_id}/m16/refresh-market-deltas
# Quand price_line_bundle_values aura des lignes :
# → market_delta_pct calculé via jointure pg_trgm item/zone sur market_signals_v2
# → Exemple attendu : delta 0.12 (< 0.15) → signal VERT
```

**R1 — M14 bridge (TESTABLE quand M14 a tourné) :**

```bash
# POST /api/workspaces/{ws_id}/m16/sync-from-m14
# Quand evaluation_documents aura scores_matrix :
# → Résultat : {"created": N, "updated": M, "skipped": 0, ...}
```

### Imports legacy — État
```
grep workspace_access_service src/ :
  → src/couche_a/auth/workspace_access.py : import WorkspaceAccessService (légitime V4.x)
  → src/api/routers/workspace_members.py  : import WorkspaceRole (légitime V4.x)
  → src/auth/guard.py                      : commentaire seul (pas d'import)

grep WORKSPACE_WRITE_PERMISSIONS src/ : aucun résultat hors workspace_access_service.py
grep check_workspace_permission src/  : aucun résultat (bridge uniquement dans le service)
```

Conclusion : les usages restants sont des imports V4.x légitimes dans leur domaine. Aucun nettoyage requis.

### Ruff F401 : clean ✅

`ruff check src/ --select F401` → 0 erreur.

---

## Mandats futurs en attente (CTO)

| Réf | Titre | Statut | Document |
|---|---|---|---|
| `refactor/v52-pydantic-settings` | Migration `src/core/config.py` → Pydantic Settings | SOUMIS CTO | `docs/audit/AUDIT_V52_PYDANTIC_SETTINGS.md` |
| `feature/v52-rag-process-info` | RAG pgvector pour `process_info_handler` | SOUMIS CTO | `docs/audit/AUDIT_V52_RAG_PROCESS_INFO.md` |
