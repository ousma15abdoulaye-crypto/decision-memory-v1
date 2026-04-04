# DMS V4.2.0 — PLAN DE MIGRATION 068→075

**Référence** : DMS-V4.2.0-ADDENDUM-WORKSPACE §VI
**Date freeze** : 2026-04-04
**Statut** : FREEZE DÉFINITIF après hash
**Pré-requis** : Alembic head = 067 (une seule ligne)

---

## Séquence des migrations

| # | Nom | Tables créées/modifiées | Triggers | Index | RLS |
|---|---|---|---|---|---|
| 068 | `068_create_tenants` | tenants | — | — | non |
| 069 | `069_process_workspaces_events_memberships` | process_workspaces, workspace_events, workspace_memberships | fn_workspace_sealed_final, trg_workspace_events_append_only | 5 index | oui (pw, we) |
| 070 | `070_supplier_bundles_documents` | supplier_bundles, bundle_documents | — | 3 index | oui (sb, bd) |
| 071 | `071_committee_sessions_deliberation` | committee_sessions, committee_session_members, committee_deliberation_events | fn_committee_session_sealed_final, trg_cde_append_only | 1 index | oui (cs, cde) |
| 072 | `072_vendor_market_signals_watchlist` | vendor_market_signals, market_watchlist_items | trg_vms_append_only | — | non |
| 073 | `073_add_workspace_id_to_canon_tables` | ALTER 10 tables + CHECK constraint | — | — | — |
| 074 | `074_drop_case_id_rename_deprecated` | SET NOT NULL + DROP case_id + RENAME 6 tables + DROP triggers | — | — | — |
| 075 | `075_rbac_permissions_roles` | rbac_permissions, rbac_roles, rbac_role_permissions, user_tenant_roles | — | — | non |

---

## Détail par migration

### 068 — `068_create_tenants`

**Pré-condition** : head = 067
**Tables créées** : `tenants`
**Validation** :
- [ ] `SELECT count(*) FROM tenants` → 0 (table vide créée)
- [ ] `INSERT INTO tenants (code, name) VALUES ('sci_mali', 'Save the Children Mali')` → OK
- [ ] CI verte

### 069 — `069_process_workspaces_events_memberships`

**Pré-condition** : 068 validée
**Tables créées** : `process_workspaces`, `workspace_events`, `workspace_memberships`
**Triggers** : `fn_workspace_sealed_final`, `trg_workspace_events_append_only`
**Policies RLS** : `pw_tenant_isolation`, `we_tenant_isolation`
**Index** : `idx_pw_tenant_status`, `idx_pw_zone`, `idx_pw_created`, `idx_we_workspace_time`, `idx_we_tenant_type`, `idx_we_emitted`
**Validation** :
- [ ] workspace_events INSERT → OK
- [ ] workspace_events UPDATE → exception fn_reject_mutation
- [ ] workspace_events DELETE → exception fn_reject_mutation
- [ ] RLS : SELECT process_workspaces sans SET LOCAL → 0 lignes
- [ ] RLS : SELECT avec SET LOCAL tenant_a → lignes tenant_a seul
- [ ] UNIQUE(workspace_id, user_id, role) sur workspace_memberships → testé
- [ ] CI verte

### 070 — `070_supplier_bundles_documents`

**Pré-condition** : 069 validée
**Tables créées** : `supplier_bundles`, `bundle_documents`
**Policies RLS** : `sb_tenant_isolation`, `bd_tenant_isolation`
**Index** : `idx_sb_workspace`, `idx_bd_bundle`, `idx_bd_workspace`
**Validation** :
- [ ] UNIQUE(workspace_id, bundle_index) → testé
- [ ] UNIQUE(workspace_id, sha256) sur bundle_documents → testé
- [ ] RLS isolation → testé
- [ ] CI verte

### 071 — `071_committee_sessions_deliberation`

**Pré-condition** : 070 validée
**Tables créées** : `committee_sessions`, `committee_session_members`, `committee_deliberation_events`
**Triggers** : `fn_committee_session_sealed_final`, `trg_cde_append_only`
**Policies RLS** : `cs_tenant_isolation`, `cde_tenant_isolation`
**Index** : `idx_cde_session`
**Validation** :
- [ ] committee_sessions : sealed → draft → exception trigger
- [ ] committee_sessions : sealed → closed → OK
- [ ] committee_sessions : closed → sealed → exception trigger
- [ ] committee_deliberation_events UPDATE → exception
- [ ] committee_deliberation_events DELETE → exception
- [ ] UNIQUE(session_id, user_id) → testé
- [ ] CI verte

### 072 — `072_vendor_market_signals_watchlist`

**Pré-condition** : 071 validée
**Tables créées** : `vendor_market_signals`, `market_watchlist_items`
**Triggers** : `trg_vms_append_only`
**Validation** :
- [ ] vendor_market_signals append-only : UPDATE → exception
- [ ] vendor_market_signals append-only : DELETE → exception
- [ ] CI verte

### 073 — `073_add_workspace_id_to_canon_tables`

**Pré-condition** : 072 validée
**Tables modifiées** : ALTER 10 tables ADD workspace_id (nullable)
**Contrainte** : CHECK `no_winner_field` sur `evaluation_documents`
**Validation** :
- [ ] evaluation_documents INSERT payload `{"winner":"X"}` → rejeté CHECK
- [ ] evaluation_documents INSERT payload `{"scores":{}}` → OK
- [ ] 10 tables ont workspace_id (nullable pour l'instant)
- [ ] CI verte

### 074 — `074_drop_case_id_rename_deprecated`

**PRÉ-CONDITION BLOQUANTE** : script `migrate_cases_to_workspaces.py` exécuté ET `verify_migration` retourne 0 sur toutes les tables.
**Tables modifiées** : SET NOT NULL (9 tables) + DROP case_id (10 tables)
**Tables renommées** : 6 tables → `_deprecated_*`
**Triggers supprimés** : 3 triggers sur tables deprecated
**Validation** :
- [ ] `verify_migration` → 0 orphelins sur 10 tables
- [ ] 0 artefact avec workspace_id NULL (sauf market_surveys)
- [ ] `_deprecated_cases` existe (RENAME, pas DROP)
- [ ] `grep -r "case_id" src/` → 0 (hors commentaires et migrations)
- [ ] CI verte (tous tests adaptés)

### 075 — `075_rbac_permissions_roles`

**Pré-condition** : 074 validée
**Tables créées** : `rbac_permissions`, `rbac_roles`, `rbac_role_permissions`, `user_tenant_roles`
**Données insérées** : 17 permissions, 6 rôles, matrice complète
**Validation** :
- [ ] 17 permissions insérées
- [ ] 6 rôles insérés
- [ ] Matrice : `SELECT count(*) FROM rbac_role_permissions` → nombre attendu
- [ ] Users existants migrés vers user_tenant_roles
- [ ] CI verte

---

## Script de migration données — BLOC-01 et BLOC-02 corrigés

```python
"""
scripts/migrate_cases_to_workspaces.py

Migration des cases existants vers process_workspaces.
Exécuté manuellement en maintenance window.
Idempotent — peut être relancé sans risque.

BLOC-01 : whitelist frozenset + assertion
BLOC-02 : map_status avec exception explicite
"""
import asyncio
import asyncpg


ALLOWED_TABLES: frozenset = frozenset([
    'documents',
    'evaluation_criteria',
    'offer_extractions',
    'extraction_review_queue',
    'score_history',
    'elimination_log',
    'evaluation_documents',
    'decision_history',
    'dict_proposals',
    'market_surveys',
])


def map_procedure_type(canon_type: str) -> str:
    mapping = {
        'devis_unique': 'devis_unique',
        'devis_simple': 'devis_simple',
        'devis_formel': 'devis_formel',
        'appel_offres_ouvert': 'appel_offres_ouvert',
    }
    if canon_type not in mapping:
        raise ValueError(
            f"Procedure type non mappé : '{canon_type}'. "
            f"Ajouter au mapping avant de continuer."
        )
    return mapping[canon_type]


def map_status(canon_status: str) -> str:
    mapping = {
        'draft': 'draft',
        'open': 'assembling',
        'evaluation': 'in_analysis',
        'committee': 'in_deliberation',
        'sealed': 'sealed',
        'awarded': 'closed',
        'cancelled': 'cancelled',
    }
    if canon_status not in mapping:
        raise ValueError(
            f"Statut non mappé : '{canon_status}'. "
            f"Ajouter au mapping avant de continuer."
        )
    return mapping[canon_status]


async def migrate_cases_to_workspaces(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> int:
    cases = await conn.fetch("""
        SELECT * FROM cases
        WHERE id NOT IN (
            SELECT pw.legacy_case_id FROM process_workspaces pw
            WHERE pw.legacy_case_id IS NOT NULL
        )
    """)

    migrated = 0
    for case in cases:
        process_type = map_procedure_type(case['procedure_type'])
        status = map_status(case['status'])

        ws_id = await conn.fetchval("""
            INSERT INTO process_workspaces (
                tenant_id, created_by, reference_code, title,
                process_type, estimated_value, currency,
                humanitarian_context, min_offers_required,
                response_period_days, sealed_bids_required,
                committee_required, zone_id, category_id,
                submission_deadline, profile_applied,
                procurement_file, status, created_at,
                legacy_case_id
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,
                $15,$16,$17,$18,$19,$20
            )
            RETURNING id
        """,
            tenant_id, case['created_by'], case['reference'],
            case['title'], process_type, case['estimated_value'],
            case['currency'], case['humanitarian_context'],
            case['min_offers_required'], case['response_period_days'],
            case['sealed_bids_required'], case['committee_required'],
            case['zone_id'], case['category_id'],
            case['submission_deadline'], case['profile_applied'],
            case['procurement_file'], status, case['created_at'],
            case['id'],
        )

        for table in ALLOWED_TABLES:
            assert table in ALLOWED_TABLES, f"Table non autorisée : {table}"
            await conn.execute(f"""
                UPDATE {table}
                SET workspace_id = $1
                WHERE case_id = $2
                  AND workspace_id IS NULL
            """, ws_id, case['id'])

        migrated += 1

    return migrated


async def verify_migration(conn: asyncpg.Connection) -> dict:
    results = {}
    for table in ALLOWED_TABLES:
        assert table in ALLOWED_TABLES
        count = await conn.fetchval(f"""
            SELECT count(*) FROM {table}
            WHERE workspace_id IS NULL AND case_id IS NOT NULL
        """)
        results[table] = count
    return results
```

---

## Migration 074 — DROP case_id (après script)

```sql
-- PRÉ-CONDITION : verify_migration retourne 0 sur toutes les tables
-- PRÉ-CONDITION : script exécuté sur staging ET vérifié

-- SET NOT NULL
ALTER TABLE documents ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE evaluation_criteria ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE offer_extractions ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE extraction_review_queue ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE score_history ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE elimination_log ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE evaluation_documents ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE decision_history ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE dict_proposals ALTER COLUMN workspace_id SET NOT NULL;
-- market_surveys.workspace_id reste NULLABLE (W2 hors processus)

-- DROP case_id
ALTER TABLE documents DROP COLUMN case_id;
ALTER TABLE evaluation_criteria DROP COLUMN case_id;
ALTER TABLE offer_extractions DROP COLUMN case_id;
ALTER TABLE extraction_review_queue DROP COLUMN case_id;
ALTER TABLE score_history DROP COLUMN case_id;
ALTER TABLE elimination_log DROP COLUMN case_id;
ALTER TABLE evaluation_documents DROP COLUMN case_id;
ALTER TABLE decision_history DROP COLUMN case_id;
ALTER TABLE dict_proposals DROP COLUMN source_case_id;
ALTER TABLE market_surveys DROP COLUMN case_id;

-- RENAME (pas DROP — rollback possible 30 jours)
ALTER TABLE cases RENAME TO _deprecated_cases;
ALTER TABLE committees RENAME TO _deprecated_committees;
ALTER TABLE committee_members RENAME TO _deprecated_committee_members;
ALTER TABLE committee_delegations RENAME TO _deprecated_committee_delegations;
ALTER TABLE submission_registries RENAME TO _deprecated_submission_registries;
ALTER TABLE submission_registry_events RENAME TO _deprecated_submission_registry_events;

-- DROP deprecated triggers
DROP TRIGGER IF EXISTS trg_sre_append_only ON _deprecated_submission_registry_events;
DROP TRIGGER IF EXISTS trg_sre_reject_after_close ON _deprecated_submission_registry_events;
DROP TRIGGER IF EXISTS trg_sync_registry_on_lock ON _deprecated_committees;
```

---

## Calendrier semaine par semaine

### Semaine 0 — Pré-conditions (2 jours)

**ACTIONS** :
1. Résoudre P0-DOC-01 : réconcilier MRD (1 vérité par date)
2. Résoudre P0-OPS-01 : checklist release dual-app
3. Confirmer Redis Railway opérationnel (P1-INFRA-01)
4. Probe live : alembic current sur Railway = 067
5. Confirmer plan Railway Pro (100 connexions)

**GATE SEMAINE 0** :
- [ ] P0-DOC-01 résolu — MRD avec probe date unique
- [ ] P0-OPS-01 résolu — checklist dual-app documentée
- [ ] Redis confirmé opérationnel sur Railway
- [ ] alembic current Railway = 067 (probe live)
- [ ] Plan Railway = Pro (100 connexions) OU upgrade planifié
→ 5/5 avant de continuer. 4/5 = STOP.

### Semaine 1 — Fondations (migrations 068-069)

**ACTIONS** :
- 068 : tenants + pgvector + pgvectorscale extensions
- 069 : process_workspaces + workspace_events + workspace_memberships
- Langfuse self-hosted sur Railway (Docker compose)
- AsyncPostgresSaver LangGraph configuré (DATABASE_URL)

**POOL CONNEXIONS** :
```
FastAPI       : 10
ARQ           :  3
LangGraph     :  3
Langfuse      :  3
Marge         :  6
Total         : 25 / 100
```

**GATE SEMAINE 1** :
- [ ] workspace_events INSERT → OK
- [ ] workspace_events UPDATE → exception fn_reject_mutation
- [ ] workspace_events DELETE → exception fn_reject_mutation
- [ ] RLS : SELECT process_workspaces sans SET LOCAL → 0 lignes
- [ ] RLS : SELECT avec SET LOCAL tenant_a → lignes tenant_a seul
- [ ] Langfuse UI accessible sur Railway
- [ ] pgvector : CREATE EXTENSION vector → OK
- [ ] CI verte

### Semaine 2 — Bundles + Committee + Market + ALTER (migrations 070-073)

**ACTIONS** :
- 070 : supplier_bundles + bundle_documents
- 071 : committee_sessions + committee_session_members + committee_deliberation_events
- 072 : vendor_market_signals + market_watchlist_items
- 073 : ALTER TABLE (10 tables) ADD workspace_id + contrainte CHECK no_winner_field

**GATE SEMAINE 2** :
- [ ] committee_sessions : sealed → draft → exception trigger
- [ ] committee_sessions : sealed → closed → OK
- [ ] committee_sessions : closed → sealed → exception trigger
- [ ] committee_deliberation_events UPDATE → exception
- [ ] committee_deliberation_events DELETE → exception
- [ ] evaluation_documents INSERT payload `{"winner":"X"}` → rejeté CHECK
- [ ] evaluation_documents INSERT payload `{"scores":{}}` → OK
- [ ] 10 tables ont workspace_id (nullable)
- [ ] supplier_bundles RLS isolation tenant → OK
- [ ] vendor_market_signals append-only → OK
- [ ] CI verte

### Semaine 3 — Migration données + DROP + RBAC (script + 074-075)

**ACTIONS** :
- Jour 1 : Exécuter `migrate_cases_to_workspaces.py` sur STAGING. Vérifier : `verify_migration` retourne 0.
- Jour 2 : 074 — SET NOT NULL + DROP case_id + RENAME deprecated
- Jour 3-5 : Adapter tests (batch + validation manuelle). Estimation : 200-300 tests.
- Jour 5 : 075 — RBAC tables + données + user migration

**CONTRAINTE** : CI ne peut pas être rouge > 1 jour. Jour 2 (074) cassera les tests → Jour 3-5 = freeze features, batch tests uniquement.

**GATE SEMAINE 3** :
- [ ] verify_migration → 0 orphelins sur 10 tables
- [ ] 0 artefact avec workspace_id NULL (sauf market_surveys)
- [ ] `grep -r "case_id" src/` → 0 (hors commentaires et migrations historiques)
- [ ] `grep -r "case_id" tests/` → 0 (tous adaptés)
- [ ] `_deprecated_cases` existe (RENAME, pas DROP — rollback 30j)
- [ ] 17 permissions insérées
- [ ] 6 rôles insérés avec matrice complète
- [ ] Users existants migrés vers user_tenant_roles
- [ ] CI verte — tous tests adaptés

### Semaines 4-5 — Pass -1 Assembler

**ACTIONS** :
- Mistral OCR 3 client async + retry policy (3 tentatives, backoff exp.)
- Azure Document Intelligence client (fallback si Mistral timeout > 30s)
- Détection PDF natif vs scan
- Pré-validation déterministe ZIP AVANT tout LLM
- PydanticAI tools : ocr, classify, link_vendor, completeness_check
- LangGraph Pass -1 graph : extract → classify → bundle → [HITL interrupt] → finalize
- AsyncPostgresSaver checkpoint PostgreSQL
- ARQ job : run_pass_minus_1 (async, rejouable)
- Langfuse tracing

**GATE SEMAINES 4-5** :
- [ ] ZIP invalide (mauvais format) → 422, 0 token consommé
- [ ] ZIP 15 fichiers SCI Mali → 4 bundles < 30s
- [ ] Bundle incomplet → HITL interrupt() déclenché
- [ ] HITL résolu → bundle_status = complete
- [ ] 0 bundle orphelin après HITL
- [ ] Langfuse trace complète avec coût USD
- [ ] AsyncPostgresSaver : checkpoint rejouable
- [ ] Fallback Azure si Mistral timeout → transparent
- [ ] CI verte

### Semaines 6-7 — Adapter M12/M13/M14 au workspace

**ACTIONS** :
- M12 : workspace_id obligatoire, émet workspace_event M12_CLASSIFICATION_COMPLETE
- M13 : workspace_id obligatoire, émet workspace_event M13_PROFILE_COMPLETE
- M14 : consomme supplier_bundles (pas inp.offers), construit offers[] depuis bundles, émet workspace_event M14_EVALUATION_READY

**LE TROU EST COMBLÉ** :
```
AVANT : M14 attend inp.offers pré-structuré. Personne ne le produit.
APRÈS : M14 charge supplier_bundles, assemble offers[], évalue.
Composition : Pass-1 → supplier_bundles → M12 → bundle_documents classifiés → M14
```

**GATE SEMAINES 6-7** :
- [ ] Pipeline complet : ZIP → Pass-1 → M12 → M13 → M14
- [ ] workspace_events trace chaque étape (4 events minimum)
- [ ] M14 construit offers[] depuis supplier_bundles
- [ ] 0 champ winner/rank dans aucune sortie M14
- [ ] 3 dossiers SCI Mali réels passent bout en bout
- [ ] Langfuse trace pipeline complet avec coûts
- [ ] CI verte

### Semaine 8 — W2 + W3 routes API + WebSocket + ARQ projector

**ROUTES W1** :
- GET /workspaces/{id}
- GET /workspaces/{id}/bundles
- GET /workspaces/{id}/evaluation
- POST /workspaces
- POST /workspaces/{id}/upload-zip

**ROUTES W2** (hors processus) :
- GET /market/overview
- GET /market/items/{item_key}/history
- GET /market/vendors/{vendor_id}/signals
- GET /market/watchlist
- POST /market/watchlist
- PATCH /market/items/{item_key}/annotate

**ROUTES W3** :
- GET /workspaces/{id}/committee
- POST /workspaces/{id}/committee/open-session
- POST /workspaces/{id}/committee/add-member
- POST /workspaces/{id}/committee/add-comment
- POST /workspaces/{id}/committee/challenge-score
- POST /workspaces/{id}/committee/seal

**WebSocket** : `ws://host/ws/workspace/{id}/events` — push depuis workspace_events uniquement (INV-W07)

**ARQ Couche B projector** :
- `on_workspace_sealed` → decision_history + mercuriale update
- `on_cba_approved` → recalcul mercuriale moyenne
- `alert_watchlist` → trigger si price delta > threshold
- Tous jobs idempotents

**GATE SEMAINE 8** :
- [ ] W2 : GET /market/overview SANS workspace_id → données retournées
- [ ] W3 : seal session → pv_snapshot + seal_hash SHA-256
- [ ] W3 : seal → workspace_event SESSION_SEALED
- [ ] W3 : seal → workspace status = sealed
- [ ] WebSocket : événement = row de workspace_events
- [ ] WebSocket : 0 calcul côté gateway (INV-W07)
- [ ] ARQ : SEALED → decision_history INSERT < 2s
- [ ] ARQ : SEALED → mercuriale update < 2s
- [ ] ARQ : tous jobs rejouables (idempotent test)
- [ ] CI verte

### Semaines 9-10 — Pilote + Hardening + Go/No-Go

**ACTIONS** :
- 5 processus SCI Mali réels de bout en bout
- Langfuse evals : CBA accuracy ≥ 0.75
- Performance : Pass-1 < 30s, Signal < 200ms, Export PV < 10s
- Tests de régression complets

**GATE GO/NO-GO PILOTE** :
- [ ] 5 workspaces sealed avec pv_hash non NULL
- [ ] 5 processus : ZIP → sealed en < 2 jours
- [ ] 0 artefact flottant sans workspace_id
- [ ] 0 winner/rank/recommendation
- [ ] 0 case_id dans le code vivant
- [ ] W2 interrogeable hors processus confirmé
- [ ] Langfuse coût tracé par workspace_id + tenant_id
- [ ] Performance SLA respectés
- [ ] Pool connexions Railway < 50%
- [ ] Procurement officer a validé l'expérience
- [ ] 12 STOP SIGNALS vérifiés négatifs
→ 11/11 = GO. 10/11 = STOP, corriger, relancer.

---

*Gelé après hash. Tout amendement → DMS_V4.2.1_PATCH.md*
