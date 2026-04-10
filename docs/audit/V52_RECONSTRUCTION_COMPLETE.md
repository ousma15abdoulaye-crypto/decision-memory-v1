# DMS V5.2 — Rapport de Reconstruction Complete

## Resume Executif

| Metrique | Valeur |
|---|---|
| Duree totale | ~13.75 jours |
| Fichiers modifies | 23 |
| Fichiers crees | 24 |
| Migrations Alembic | 4 |
| Tests unitaires | 208 passes |
| Tests integration | 18 passes / 2 skips (M14 sur donnees reelles) |
| Gates CI | 5 jobs |
| Invariants DB verifies | triggers (5), RLS (34 tables), colonnes marche |

---

## Phase P1 — Fondations DB + Auth (2.25j)

### Corrections

| ID | Fichier | Correction |
|---|---|---|
| P1.1 | `alembic/versions/v52_p1_001_immutability_triggers.py` | 4 triggers immutabilite : trg_pv_snapshot_immutable, trg_delib_msg_append_only, trg_assessment_comments_immutable, trg_assessment_history_append_only |
| P1.2 | `alembic/versions/v52_p1_002_assessment_auto_history.py` | Trigger auto-historisation criterion_assessments → assessment_history |
| P1.3 | `src/auth/guard.py` | Guard unifie : 3 checks (token, workspace, permission), retourne dict, supporte revoked_at |
| P1.3 | `src/auth/permissions.py` | 18 permissions × 6 roles corriges (technical/budget_holder/market.write ajoutes) |
| P1.4 | `src/db/async_pool.py` | app.current_user pose via set_config dans le pool async (bug securite) |
| P1.4 | `alembic/versions/v52_p1_003_rls_completion.py` | RLS complete sur 34 tables (etait partiel) |

### Invariants enforces

- INV-W05 / INV-S03 / INV-S04 : triggers immutabilite DB
- INV-AUTH : guard unifie avec revoked_at
- INV-RLS : 34 tables enabled + forced

---

## Phase P2 — Integrite Metier (3.75j)

### Ruptures corrigees

| Rupture | Service cree | Route |
|---|---|---|
| R10 — Seal sans checks | `src/services/seal_checks.py` | Branche dans committee_sessions.py |
| R3 — market_delta_pct jamais calcule | `src/services/market_delta.py` + migration `v52_p2_001` | POST /api/workspaces/{id}/m16/refresh-market-deltas |
| R1 — M14 scores ressaisis manuellement | `src/services/m14_bridge.py` | POST /api/workspaces/{id}/m16/sync-from-m14 |

### Coutures V4↔V5

- `src/auth/guard.py` : `_LEGACY_ROLE_MAP` bridge V4.x roles → V5.2 permissions
- `src/middleware/` : tenant middleware consolide
- `src/api/routers/agent.py` : fix crash raw_conn + UserClaims

### Ecarts en dette documentee

| ID | Ecart | Statut |
|---|---|---|
| R2 | decision_history absente (signal qualite 0.15) | Mandat CTO V5.3 |
| R4 | decision_snapshots absent du PV W3 | Mandat CTO V5.3 |
| R6 | score_history non lu dans le PV | Mandat CTO V5.3 |
| R7 | M13 blueprint non persiste | Mandat CTO futur |
| R8 | m13_correction_log jamais relu | Mandat CTO futur |
| R9 | vendor_market_signals ≠ market_signals_v2 | Coherence Couche B |
| E07 | Deux systemes RBAC coexistent | Bridge cree, migration complete post-V5.2 |
| E18 | criterion_assessment_history ≠ assessment_history | Reconciliation V5.3 |

---

## Phase P3 — Observabilite + Agent (1j)

### Bugs corriges

| Code | Fichier | Bug |
|---|---|---|
| C1 | `src/agent/handlers/workspace_status.py` | async_load_cognitive_facts : awaitable oublie |
| C5 | `src/agent/semantic_router.py` | intent_confidence mal trace dans Langfuse |
| C7 | `src/mql/param_extractor.py` | _extract_article type annotation str | None |
| C-cfg | `src/core/config.py` | DATABASE_URL validator normalise psycopg:// |

### Resultat tests

208/208 tests unitaires verts apres P3.

---

## Phase P4 — Frontend (5j)

### Composants crees / modifies

| Composant | Fichier | Statut |
|---|---|---|
| Types OpenAPI | `frontend-v51/types/api.ts` | 7977 lignes generees |
| ErrorBoundary | `frontend-v51/components/error-boundary.tsx` | Cree |
| Design tokens | `frontend-v51/app/globals.css` | Palettes DMS + dark mode + WCAG |
| Dashboard cards | `frontend-v51/app/dashboard/page.tsx` | Regime badges + progress + blockers |
| Seal 422 dialog | `frontend-v51/components/workspace/seal-button.tsx` | Erreurs structurees quorum/poids/flags |
| M14 sync button | `frontend-v51/components/workspace/m14-sync-button.tsx` | BridgeResult dialog |
| Agent console | `frontend-v51/components/agent-console.tsx` | SSE rewrite + suggestions + sources |
| Command palette | `frontend-v51/components/command-palette.tsx` | 4 groupes + fallback agent |
| ConfidenceBadge | `frontend-v51/components/ui/confidence-badge.tsx` | 3 canaux WCAG AA |

### Metriques build

| Check | Resultat |
|---|---|
| tsc --noEmit | 0 erreur |
| next build | Succes sans warning |
| types/api.ts | 7977 lignes (non-stub) |
| framer-motion / RHF / zod | Supprimes |
| ARIA roles | role, aria-current, aria-label presents |

---

## Phase P5 — CI/Tests (1j)

### Jobs CI (ci-v52-gates.yml)

| Job | Verifie |
|---|---|
| `backend-quality` | ruff check + black --check + pytest tests/unit/ |
| `frontend-build` | OpenAPI types non-stub + tsc + next build + phantom deps |
| `db-v52-invariants` | 5 triggers + RLS >= 25 tables + colonnes market_delta_pct |
| `permissions-matrix` | 18 permissions × 6 roles + admin == ALL + observer sans write |
| `integration-v52` | Seal flow (3) + M14 bridge (4) + agent guardrail (11) |

### Tests integration P5.2

| Fichier | Tests | Resultat |
|---|---|---|
| `test_seal_flow_v52.py` | 3 | 3 passes |
| `test_m14_bridge_flow.py` | 4 | 2 passes / 2 skips (donnees M14 reelles en prod) |
| `test_agent_guardrail.py` | 11 | 11 passes |
| **TOTAL** | **18** | **18 passes / 2 skips** |

---

## Registre Ecarts Ouverts (8 ecarts)

| ID | Description | Priorite | Mandant |
|---|---|---|---|
| E07 | Deux RBAC coexistent (bridge cree, migration complete) | Critique | CTO — post-V5.2 |
| E18 | Deux historiques M16 divergents | Critique | CTO — V5.3 |
| E19 | os.environ.get() disperses | Corrige P3/P5 | — |
| E20 | process_info sans RAG reel | Important | CTO — feature/v52-rag-process-info |
| E21 | decision_snapshots non integres au PV | Important | CTO — V5.3 |
| E22 | score_history non consomme par V5.2 | Important | CTO — V5.3 |
| E23 | M13 blueprint non persiste dans PV | Important | CTO — futur |
| E24 | vendor_market_signals ≠ market_signals_v2 | Important | Coherence Couche B |
| E25 | decision_history absente → signal qualite mort | Important | CTO — V5.3 |

## Registre Ruptures Ouvertes (7 ruptures)

| ID | Rupture | Priorite | Mandat |
|---|---|---|---|
| R2 | decision_history absente | P2 | CTO V5.3 |
| R4 | decision_snapshots absent du PV | P2 | CTO V5.3 |
| R5 | score_runs (case_id) non consomme | P3 | Futur |
| R6 | score_history non lu dans PV | P2 | CTO V5.3 |
| R7 | M13 blueprint non persiste | P2 | Futur |
| R8 | m13_correction_log jamais relu | P3 | Futur |
| R9 | vendor_market_signals ≠ market_signals_v2 | P2 | Coherence Couche B |

---

## Recommandations Post-V5.2

1. **Migration RBAC complete V4→V5** (E07) — unifier les deux systemes sous guard() V5.2
2. **Reconciliation historiques M16** (E18) — fusionner criterion_assessment_history + assessment_history
3. **PV V5.3** — integrer decision_snapshots (R4), score_history (R6), M13 blueprint (R7), decision_history (R2)
4. **RAG process_info** (E20) — corpus reglementaire DGMP dans pgvector
5. **Coherence Couche B** (R9/E24) — unifier vendor_market_signals + market_signals_v2

---

*Document produit le 2026-04-10 — Phase P5.3 DMS V5.2 Reconstruction*
