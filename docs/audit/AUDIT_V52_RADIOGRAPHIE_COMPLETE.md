# DMS V5.1 — Radiographie Complète & Matrice de Diagnostic

> **Date :** 2026-04-09  
> **Branche :** `refactor/v52-pydantic-settings`  
> **Méthode :** 13 prompts d'audit, 11 agents d'exploration parallèles, lecture intégrale du code  

---

## Phase 2 — Matrice de Diagnostic

| # | Organe | Canon V5.1 | État Réel | Écarts Critiques | Criticité |
|---|--------|-----------|-----------|------------------|-----------|
| O1 | **Auth/JWT** | §5.1-5.3 : guard unifié, JWT access+refresh, RLS, rate limit, 18 perms × 6 rôles | guard.py (73L) + permissions.py (134L) + jwt_handler.py (207L) + middleware.py (234L) — **FONCTIONNEL** | DEUX auth routers coexistent ; `/auth/refresh` **n'a pas de route HTTP** ; middleware ne fait pas `SET` SQL (contextvars) ; DEUX matrices RBAC (V5.1 vs Couche A legacy) | 🟡 |
| O2 | **Workspace** | §4/O2 : CRUD, transitions validées, events | workspaces.py (843L) — 10 routes, transitions validées via `validate_transition`, trigger DB `sealed_final` | Fichier **dépasse 800L** (seuil découpage) ; `status_transitions.py` est un réexport vide (10L) | 🟢 |
| O3 | **Cognitif** | §4/O3 : fonction pure, E0→E6, advance_blockers FR | cognitive_state.py (248L) — **PURE**, E0→E6 recalculé, blockers en FR, route GET cognitive-state | **Conforme au canon** — aucun écart significatif | 🟢 |
| O4 | **Membres** | §4/O4 : quorum ≥4, rôles critiques, invite/revoke | workspace_members.py (221L), quorum_service.py (63L) — QUORUM_MIN=4, CRITICAL_ROLES={supply_chain, finance, technical} | **Conforme au canon** | 🟢 |
| O5 | **Documents** | §4/O5 : upload 50MB, OCR→extraction→confidence, Langfuse trace | extraction/engine.py (873L), upload_security.py (117L), assembler/ocr_mistral.py (161L) | engine.py **dépasse 800L** ; route legacy `api/documents.py` **sans** limite 50MB ni magic bytes ; extraction SLA-A **non tracée** Langfuse ; confidence {0.6,0.8,1.0} ≠ canon [0,1] continu | 🟡 |
| O6 | **M16 Évaluation** | §4/O6 : domaines, critères, assessments, poids=100%, éliminatoires=0 | m16_comparative.py (553L), m16_evaluation_service.py (343L), weight_validator.py (112L) — **14 routes**, poids=100% validé application, éliminatoires=0 | Pas de CHECK DB « somme=100 » ; `criterion_assessment_history` **jamais alimentée par INSERT applicatif** (table vide) ; seuils en **valeurs littérales** pas en constantes nommées | 🟡 |
| O7 | **Signaux** | §4/O7 : 3 fonctions signal, seuils canon | signal_engine.py (109L) — `compute_assessment_signal`, `compute_price_signal`, `compute_domain_signal` + 2 helpers | **5 fonctions** au lieu de 3 pures ; seuils numériques corrects (0.80/0.50/0.15/0.30) mais pas de constantes nommées `CONFIDENCE_GREEN` etc. | 🟢 |
| O8 | **Délibération** | §4/O8 : threads, messages append-only, smart comments | m16_deliberation_service.py (193L), comments_service.py (363L) — `add_smart_comment` crée thread auto, trigger `trg_dm_append_only` sur messages | Route comments **pas bloquée** par `m16_guard` post-seal (pas de 409 systématique) | 🟡 |
| O9 | **Scellement** | §4/O9 : quorum+poids+flags, snapshot SHA-256, 409 post-seal | pv_builder.py (525L), committee_sessions.py (527L) — snapshot SHA-256 sur JSON complet, export JSON/PDF/XLSX | Seal W3 **ne vérifie pas** quorum/poids/flags explicitement (seulement transition cognitive) ; **pas de trigger** immutabilité `pv_snapshot` (seulement statut) ; DEUX piles de scellement coexistent (W3 vs Couche A) | 🔴 |
| O10 | **DocGen** | §4/O10 : WeasyPrint CSS table, DataBarRule, XOF Babel, snapshot scellé | pv_builder.py (525L), xlsx_builder.py (156L), pv_design_system.css — `table-layout:fixed`, DataBarRule | XOF formaté manuellement (pas `babel.numbers`) ; **6 partiels** Jinja au lieu de 5 canon ; PDF bien depuis snapshot scellé | 🟢 |
| O11 | **Agent** | §7 : SSE, semantic router embeddings, guardrail AVANT, circuit breaker 3/60/60, 4 handlers | agent.py (183L), semantic_router.py (138L), handlers.py (271L), circuit_breaker.py (88L) — **TOUT IMPLÉMENTÉ** | Bug `context.messages[-50]` **corrigé** (utilise `[-50:]`) ; guardrail AVANT LLM ; seuil RECO 0.85 ; CB 3/60/60 ; 4 handlers OK | 🟢 |
| O12 | **MQL** | §8 : 6 templates bind params, déterministe, mql_query_log RLS | templates.py (229L), engine.py (140L), param_extractor.py (139L) — 6 templates T1-T6, bind params, déterministe, log RLS | Route `/mql/stream` retourne JSON (pas SSE streaming) ; `ILIKE '%' || pat || '%'` dans SQL (concaténation SQL interne, pas injection) | 🟢 |
| O13 | **Langfuse** | §9 : singleton, flush fin requête, trace structure | langfuse_client.py (115L) — singleton, Null* fallback | `flush_langfuse()` **pas appelé** sur erreurs HTTP précoces (422/400/403) ; extraction SLA-A **non tracée** ; `LangfuseIntegration` (memory) **jamais utilisé** dans src/ ; structure spans ≠ canon exactement | 🟡 |
| — | **Frontend** | §3+INV-F : OpenAPI types, TanStack, Zustand, RHF+Zod, ErrorBoundary, Sentry, cmdk, ConfidenceBadge | frontend-v51/ Next.js 16 — TanStack OK, Zustand (auth), SSE agent, dashboard auto-refresh 30s | `types/api.ts` **stub vide** ; RHF+Zod **non utilisés** malgré dépendances ; cmdk+Framer **non implémentés** ; **pas d'ErrorBoundary** ; **pas de Sentry** ; sidebar fixe (pas cognitive-driven) ; `frontend/` legacy à nettoyer | 🔴 |
| — | **DB/Migrations** | §5.4-5.5 : RLS, triggers, 93+ migrations | 93 migrations + 11 patches, RLS forcé sur M16/V5.1, triggers append-only | `criterion_assessment_history` **vide** (pas d'INSERT applicatif) ; pas de trigger immutabilité `pv_snapshot` ; doublons de numéros (040/042/043/046/009) historiques | 🟡 |
| — | **Tests/CI** | §12 : coverage ≥65%, 16 tests verrouillage, invariants | **254 fichiers test**, **~2070 fonctions test**, 9 workflows CI, 16 tests V5.1 TOUS PRÉSENTS | `M-CI-INVARIANTS.done` absent (gate inactive) ; 3 tests integration sont des **proxies** ; `types/api.ts` est un stub (INV-F01 fragile en CI) | 🟡 |

---

## Synthèse par Criticité

### 🔴 CRITIQUES (2 organes — bloquent la mise en production)

**O9 — Scellement :**
1. Le seal W3 ne vérifie pas explicitement quorum + poids + flags résolus
2. Pas de trigger PostgreSQL immutabilité sur `pv_snapshot` (INV-W05 non garanti en DB)
3. Deux piles de scellement coexistent (W3 / Couche A) — risque de divergence

**Frontend :**
1. `types/api.ts` stub vide — INV-F01 en CI s'appuie sur `check_openapi_types_non_stub.py`
2. Pas d'ErrorBoundary — crash UI non géré
3. Pas de Sentry — zero observabilité erreurs production
4. cmdk, Framer Motion, RHF+Zod installés mais non utilisés (dette)
5. `frontend/` legacy coexiste sans raison

### 🟡 IMPORTANTS (7 organes — dette technique à résoudre)

| Organe | Action prioritaire |
|--------|-------------------|
| O1 Auth | Fusionner les 2 auth routers ; créer route `/auth/refresh` ; unifier RBAC V5.1 vs Couche A |
| O5 Documents | Découper `engine.py` (873L > 800) ; ajouter limite 50MB + magic bytes sur route legacy |
| O6 M16 | Alimenter `criterion_assessment_history` via INSERT ou trigger ; ajouter CHECK DB somme poids |
| O8 Délibération | Ajouter `m16_guard(block_write_if_sealed=True)` sur route comments |
| O13 Langfuse | Corriger flush sur erreurs précoces ; tracer extraction SLA-A ; nettoyer `LangfuseIntegration` inutilisée |
| DB/Migrations | Ajouter trigger immutabilité `pv_snapshot` ; créer INSERT pour `criterion_assessment_history` |
| Tests/CI | Créer `M-CI-INVARIANTS.done` ; remplacer proxies par vrais tests integration |

### 🟢 CONFORMES (6 organes)

O2 (Workspace), O3 (Cognitif), O4 (Membres), O7 (Signaux), O10 (DocGen), O11 (Agent), O12 (MQL)

---

## Phase 3 — Plan de Reconstruction Bottom-Up

```
PRIORITÉ 1 — Fondations (Couche 0-1)
├── P1.1  Trigger immutabilité pv_snapshot (DB)
├── P1.2  INSERT criterion_assessment_history (DB + service)
├── P1.3  Fusionner auth routers + créer /auth/refresh
└── P1.4  Unifier RBAC (supprimer couche_a/auth/rbac.py legacy)

PRIORITÉ 2 — Intégrité métier (Couche 2-4)
├── P2.1  Renforcer seal W3 : vérifier quorum + poids + flags
├── P2.2  Bloquer comments post-seal via m16_guard
├── P2.3  Découper engine.py (873L → 2 modules)
├── P2.4  Limite 50MB + magic bytes sur api/documents.py legacy
└── P2.5  CHECK DB somme poids critères = 100%

PRIORITÉ 3 — Observabilité (Couche 5)
├── P3.1  Fix flush_langfuse sur erreurs 400/403/422
├── P3.2  Tracer extraction SLA-A dans Langfuse
└── P3.3  Supprimer LangfuseIntegration morte

PRIORITÉ 4 — Frontend (Couche 7)
├── P4.1  Générer types/api.ts depuis OpenAPI (plus de stub)
├── P4.2  Ajouter ErrorBoundary global
├── P4.3  Intégrer Sentry
├── P4.4  Implémenter cmdk + Framer Motion OU retirer des deps
├── P4.5  Implémenter RHF+Zod sur formulaires OU retirer
├── P4.6  Sidebar cognitive-driven
└── P4.7  Supprimer frontend/ legacy

PRIORITÉ 5 — CI/Tests
├── P5.1  Créer .milestones/M-CI-INVARIANTS.done
├── P5.2  Remplacer test proxies par vrais tests integration
└── P5.3  Constantes nommées pour seuils signal_engine
```

---

## Quantification de l'Effort

| Priorité | Items | Effort estimé | Risque si non fait |
|----------|-------|---------------|-------------------|
| P1 (Fondations) | 4 | 2-3 jours | Failles sécurité + intégrité |
| P2 (Métier) | 5 | 3-4 jours | Scellement non garanti, données corrompues |
| P3 (Observabilité) | 3 | 1 jour | Traces perdues, debugging aveugle |
| P4 (Frontend) | 7 | 5-7 jours | UX dégradée, pas de monitoring erreurs |
| P5 (CI) | 3 | 1 jour | Régressions non détectées |
| **Total** | **22** | **12-16 jours** | |

---

## Verdict

Le code est **substantiel et structuré** — 22 packages `src/`, 93 migrations, 254 fichiers test, 9 workflows CI. Les organes O2, O3, O4, O7, O10, O11, O12 sont **conformes au canon**. 

Les **deux points critiques** sont :
1. **Le scellement (O9)** manque de garde-fous explicites et d'immutabilité DB
2. **Le frontend** a des dépendances fantômes et aucune observabilité

La stratégie bottom-up proposée (P1→P5) permet de reconstruire sur des fondations vérifiées. **Chaque couche est validée avec des tests AVANT de passer à la suivante.**
