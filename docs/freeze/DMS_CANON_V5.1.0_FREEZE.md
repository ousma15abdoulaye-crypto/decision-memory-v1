# DMS WORKSPACE — ARCHITECTURE CANON V5.1.0 FINAL

## Decision Memory System — Document Scellé · Prêt pour Jour 1

### Save the Children International Mali · Branche main

---

> **Ce document remplace le Canon V5.0.0 et devient la source de vérité unique.**
> Toute implémentation, toute PR, tout choix technique se réfère à ce canon.
> Les couches O0–O10 sont héritées de V5.0.0 et intégrées sans modification sauf là où un delta V5.1 est explicitement noté.
> Les couches O11–O13 sont nouvelles, complètes, codées, testées.
> La couche O14 est une spécification architecturale uniquement — pas de code livré.

---

## CLAUSE DE HIÉRARCHIE DOCUMENTAIRE

> Ce document est un **CANON** qui complète et étend la chaîne documentaire DMS.
>
> **Hiérarchie d'autorité (RÈGLE-ANCHOR-10) :**
> 1. **Plan Directeur DMS V4.1** — `docs/freeze/DMS_V4.1.0_FREEZE.md` (IMMUTABLE)
> 2. **`docs/freeze/CONTEXT_ANCHOR.md`** — condensé opposable (E-01 à E-67)
> 3. **Mandats CTO** — instructions de session écrites
> 4. **Ce Canon V5.1.0** — spécification exécutable, **ne prime jamais** sur 1–3
>
> **Ce qu'il spécifie :**
> - Les couches O11 (Agent V5), O12 (MQL V8), O13 (Langfuse Tracing) — non implémentées
>   dans le dépôt au moment du gel (confirmé par Atlas P2_L6)
> - L'extension des invariants de 18 (V4.2.0) à 28 (6W + 4S + 2D + 4C + 6F + 6A)
> - Les 16 tests de verrouillage CI (extension des 8 tests V4.3.2)
> - Le plan d'implémentation 30 jours / 4 voies parallèles
> - La couche O14 (Offline-First) comme spécification architecture uniquement
>
> **Ce qu'il ne modifie PAS :**
> - RÈGLE-01 à RÈGLE-29 (V4.1.0)
> - RÈGLE-ORG-01 à RÈGLE-ORG-11 (V4.1.0)
> - INV-R1 à INV-R9 (adaptés au workspace par V4.2.0)
> - Les SLA (UPLOAD ≤500ms, EXTRACT ≤30s, PIPELINE ≤60s, SIGNAL ≤200ms, EXPORT ≤10s)
> - La stack infrastructure core (FastAPI, PostgreSQL 16, Redis 7, ARQ, Railway, Alembic)
> - Les migrations existantes 001→086
> - Les freezes actifs : schema-freeze-v1.0, validator-freeze-v1.0
>
> **En cas de conflit :**
> - Sur les RÈGLES, INV-R, SLA, fichiers intouchables → **le canon V4.1.0 prime**
> - Sur les couches O11–O14, INV-A, plan d'implémentation → **ce document prime**
>
> **Note sur confidence :** Les valeurs `confidence` dans le contexte MQL (INV-A04,
> `_compute_mql_confidence`) sont des métriques calculées continues [0.0, 1.0] — distinctes
> de la confidence extraction pipeline {0.6, 0.8, 1.0} (Kill List CLAUDE.md). Pas de conflit.

---

## 0. Axiome Fondateur

**DMS ne décide pas. Il documente les décisions humaines avec une précision irréprochable.**

Un processus DAO/RFQ/RFP est un acte juridique, engageant des fonds publics ou bailleurs,
soumis à audit DGMP Mali, ECHO, et aux règles internes SCI International.

Le système ne produit jamais : recommandation, classement, gagnant, sélection.
Le système produit : données sourcées, documentation scellée, traçabilité complète.

DMS est l'extension cognitive de l'expert procurement. Il transforme 100 offres en données
structurées. Il organise 20 contrats en parallèle. Il compresse 1 mois de processus en
1 journée. L'agent conversationnel interroge les données de marché et les données du
workspace avec traçabilité LLM complète. Le moteur fait le travail administratif.
L'expert prend les décisions.

---

## 1. Périmètre V5.1

| Dimension | Valeur |
|---|---|
| **Territoire** | Mali — Bamako/Sévaré/Mopti, déploiement Gao |
| **Organisation** | Save the Children International Mali |
| **Processus couverts** | DAO · RFQ · RFP · Contrats Cadres |
| **Langue** | Français (interface + documents) |
| **Monnaie** | XOF (Franc CFA BCEAO) |
| **Profils réglementaires** | SCI Standard · ECHO 2026 · OCHA HRF Mali · DGMP Mali AON |
| **Bailleurs exclus** | USAID (fermé le 01/07/2025) |
| **Connectivité cible** | Bamako fibre / Sévaré-Mopti 3G+ |
| **Déploiement** | Railway (Europe West) · PostgreSQL 16 · Redis 7 |

---

## 2. Corrections Intégrées

| ID | Objet | Origine | Statut |
|---|---|---|---|
| C1–C12 | Corrections V4.3.2 (WeasyPrint, Babel, openpyxl, etc.) | V4.3.2 | ✅ |
| C13 | Dashboard multi-workspace | V5.0.0 | ✅ |
| C14 | Permissions alignées code↔canon | V5.0.0 | ✅ |
| C15 | Guard unifié (1 module) | V5.0.0 | ✅ |
| C16 | Signal engine source de vérité unique | V5.0.0 | ✅ |
| C17 | Matrice d'activation État×Permission | V5.0.0 | ✅ |
| C18 | RLS tenant_id direct sur tables M16 | V5.0.0 | ✅ |
| C19 | Pagination toutes routes GET | V5.0.0 | ✅ |
| C20 | Types frontend générés OpenAPI | V5.0.0 | ✅ |
| C21 | Agent V5 `/agent/prompt` implémenté | **V5.1.0** | ✅ |
| C22 | MQL V8 Engine 6 templates SQL implémenté | **V5.1.0** | ✅ |
| C23 | Semantic Router centroïdes d'intent | **V5.1.0** | ✅ |
| C24 | Langfuse self-hosted tracing obligatoire | **V5.1.0** | ✅ |
| C25 | Circuit breaker Mistral Small→Large | **V5.1.0** | ✅ |
| C26 | Redis context store TTL 3600s | **V5.1.0** | ✅ |

---

## 3. Stack Technique

```
┌──────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE                                                  │
│  Railway · PostgreSQL 16 · Redis 7 · GitHub Actions CI          │
├──────────────────────────────────────────────────────────────────┤
│  BACKEND                                                         │
│  FastAPI · Alembic · psycopg/asyncpg (SQL paramétré, pas ORM)  │
│  ARQ (async tasks) · slowapi (rate limiting)                     │
├──────────────────────────────────────────────────────────────────┤
│  IA / LLM                                                        │
│  Mistral Small (agent primary) · Mistral Large (fallback)        │
│  Mistral Large (extraction) · Mistral OCR (scans)               │
│  Mistral Embed v2 (semantic routing)                             │
│  Azure Form Recognizer (fallback OCR si configuré)               │
├──────────────────────────────────────────────────────────────────┤
│  OBSERVABILITÉ LLM                                               │
│  Langfuse self-hosted (traces obligatoires — INV-A01)            │
├──────────────────────────────────────────────────────────────────┤
│  GÉNÉRATION DOCUMENTAIRE                                         │
│  Jinja2 · WeasyPrint (CSS table layout) · openpyxl · Babel      │
├──────────────────────────────────────────────────────────────────┤
│  FRONTEND                                                        │
│  Next.js 15 LTS · shadcn/ui · Tailwind · TanStack Query v5     │
│  Zustand · React Hook Form + Zod · openapi-typescript            │
│  Framer Motion · cmdk · Sentry                                   │
├──────────────────────────────────────────────────────────────────┤
│  DONNÉES DE MARCHÉ                                               │
│  survey_campaigns · market_surveys · MQL Engine V8               │
│  6 templates SQL paramétrés (T1–T6) · Source attribution         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Architecture des Couches — O0 à O14

### O0 — Dashboard Multi-Workspace

`GET /api/dashboard` — vue pilotage de tous les workspaces de l'utilisateur.
Calcul `compute_cognitive_state` par workspace.
Tri par urgence (health red → amber → green, needs_action, deadline).
Stats agrégées par phase. Refresh frontend 30s.

### O1 — Authentification & Tenant Isolation

JWT HS256. Access 30min. Refresh 7j. Blacklist `token_blacklist`.
Middleware `TenantContextMiddleware` pose `SET app.current_tenant` sur chaque connexion.
`RESET` au retour pool.

### O2 — Workspace & Processus

`process_workspaces` : `draft → assembling → assembled → in_analysis →
analysis_complete → in_deliberation → sealed → closed → cancelled`.
Statut = source de vérité en base.

### O3 — Moteur Cognitif E0→E6

Projection pure via `compute_cognitive_state(CognitiveFacts)`.
Pas de colonne SQL (INV-C01).
Retourne `CognitiveStateResult` avec `state`, `label_fr`, `completeness`,
`can_advance`, `advance_blockers`, `available_actions`, `confidence_regime`.

Endpoint dédié : `GET /workspaces/{workspace_id}/cognitive-state`.

### O4 — Membres & Quorum

`workspace_memberships`. Quorum : 4 membres minimum,
1 votant par rôle critique (INV-W01).

### O5 — Documents & Extraction

Upload (PDF/DOCX/XLSX, 50MB max) → OCR (Mistral OCR) → Extraction (Mistral Large) →
Confidence scoring → HITL si < 0.5. Stockage `data/uploads/`.

**Delta V5.1** : tout appel LLM d'extraction est tracé dans Langfuse (INV-A01).
Le `trace_id` est stocké dans `extraction_jobs.langfuse_trace_id`.

### O6 — Matrice d'Évaluation M16

9 tables M16. `evaluation_domains` → `evaluation_criteria` → `criterion_assessments` →
`assessment_history`. Délibération : `deliberation_threads` → `deliberation_messages`
(append-only). Notes validées. Clarifications.
Prix : `price_line_comparisons` → `price_line_bundle_values`.

INV-W03 : somme poids = 100%. INV-W04 : éliminatoires d'abord.

### O7 — Signal Engine

Source de vérité unique `src/services/signal_engine.py`.
Seuils : `CONFIDENCE_GREEN=0.80`, `CONFIDENCE_YELLOW=0.50`,
`PRICE_DELTA_GREEN=0.15`, `PRICE_DELTA_YELLOW=0.30`.
Trois fonctions : `compute_assessment_signal`, `compute_price_signal`,
`compute_domain_signal`.

### O8 — Délibération CDE

Interface simple : clic cellule → dialog → commenter ou signaler.
Backend `add_smart_comment` crée automatiquement le thread, infère le type de message,
stocke dans `deliberation_messages` ET `assessment_comments`,
met à jour l'historique si flag.

### O9 — Scellement & Snapshot

Scellement automatique en 1 clic : vérifie quorum + poids + flags →
snapshot 7 blocs → SHA-256 → verrouille → résout threads → enqueue PDF/XLSX.
INV-W02 : irréversible. INV-W05 : trigger immutabilité. INV-W06 : champs interdits.

### O10 — Génération Documentaire

Jinja2 (5 partials) → WeasyPrint PDF (CSS table layout, pas Grid) +
openpyxl XLSX (DataBarRule, pas ColorScaleRule).
Routes `GET /workspaces/{id}/committee/pv?format=json|pdf|xlsx`.

### O11 — Agent Conversationnel V5

Couche nouvelle V5.1. Surface conversationnelle unifiée.
Point d'entrée unique `POST /agent/prompt`.
Dispatch sémantique vers MQL, workspace handler, process handler, refusal.

Spécification complète : Section 7.

### O12 — MQL Engine V8

Couche nouvelle V5.1. Moteur spécialisé requêtes marché.
6 templates SQL paramétrés. Source attribution obligatoire (INV-A04).
Route interne `POST /mql/stream`.

Spécification complète : Section 8.

### O13 — Langfuse Tracing

Couche nouvelle V5.1. Tout appel LLM est tracé avant réponse au client (INV-A01).
Self-hosted. Spans structurés. Tags guardrail.

Spécification complète : Section 9.

### O14 — Offline-First (spécification architecture uniquement)

**Ce bloc est une spécification cible. Aucun code n'est livré dans V5.1.**
L'implémentation interviendra post-adoption quand les patterns d'usage
terrain seront mesurés.

Spécification : Section 10.

---

## 5. Sécurité

### 5.1 JWT

Algorithme HS256. Access 30min. Refresh 7j.
Secret `JWT_SECRET` (env, min 32 chars).
Blacklist table `token_blacklist`.
Claims : `sub`, `tenant_id`, `role`, `permissions`, `exp`, `iat`, `jti`.

### 5.2 RBAC — 18 Permissions × 6 Rôles

Source de vérité : `src/auth/permissions.py`.

| Permission | supply_chain | finance | technical | budget_holder | observer | admin |
|---|---|---|---|---|---|---|
| workspace.manage | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| workspace.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| documents.upload | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| documents.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| documents.delete | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| evaluation.write | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| evaluation.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| committee.comment | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| committee.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| committee.seal | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| pv.export | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| pv.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| market.query | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| market.write | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| agent.query | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| audit.read | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| mql.internal | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| system.admin | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 5.3 Guard Unifié

```python
# src/auth/guard.py

async def guard(db, user: dict, workspace_id: UUID, permission: str):
    """
    3 vérifications. 1 fonction. Toutes les routes.
    1. Membership (403 si non membre)
    2. Permission RBAC (403 si rôle insuffisant)
    3. Seal protection (409 si écriture sur workspace clos)
    """
    member = await db.fetch_one(
        "SELECT role FROM workspace_memberships "
        "WHERE workspace_id = :ws AND user_id = :uid",
        {"ws": workspace_id, "uid": user["id"]}
    )
    if not member:
        raise HTTPException(403, "Vous n'êtes pas membre de ce workspace")

    role = member["role"]
    role_perms = ROLE_PERMISSIONS.get(role, [])
    if permission not in role_perms and "system.admin" not in role_perms:
        raise HTTPException(403, f"Rôle '{role}' n'a pas la permission '{permission}'")

    WRITE_PERMISSIONS = {
        "workspace.manage", "documents.upload", "documents.delete",
        "evaluation.write", "committee.comment", "committee.seal",
    }
    if permission in WRITE_PERMISSIONS:
        ws = await db.fetch_one(
            "SELECT status FROM process_workspaces WHERE id = :ws",
            {"ws": workspace_id}
        )
        if ws and ws["status"] in ("sealed", "closed", "cancelled"):
            raise HTTPException(409, "Workspace clos. Aucune modification possible.")
```

### 5.4 RLS

Toutes tables métier : `tenant_id UUID NOT NULL REFERENCES tenants(id)`,
index, `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`,
policy `USING (tenant_id = current_setting('app.current_tenant', true)::uuid)`.

Liste exhaustive : `process_workspaces`, `workspace_memberships`, `workspace_events`,
`supplier_bundles`, `bundle_documents`, `source_package_documents`,
`evaluation_criteria`, `evaluation_domains`, `criterion_assessments`,
`committee_sessions`, `deliberation_threads`, `deliberation_messages`,
`validated_analytical_notes`, `assessment_history`, `clarification_requests`,
`assessment_comments`, `price_line_comparisons`,
`price_line_bundle_values` (via sous-query), `survey_campaigns`, `market_surveys`,
`mql_query_log`, `audit_log`.

### 5.5 Audit

`audit_log` hash chain. `workspace_events` journal transitions.
`assessment_history` chaque changement avec raison.
`deliberation_messages` append-only (trigger).
`pv_snapshot` immutable (trigger).
`mql_query_log` chaque requête MQL avec `langfuse_trace_id`.

### 5.6 Rate Limiting

slowapi 100/min IP. `/auth/token` 5/min. `/auth/register` 3/h.
Middleware Redis 100/min IP, 200/min user.

---

## 6. Matrice d'Activation État × Permission

L'UI affiche `available_actions`. Le guard protège les données. Séparation nette.

| Action | E0 | E1 | E2 | E3 | E4 | E5 | E6 |
|---|---|---|---|---|---|---|---|
| workspace.manage | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| documents.upload (source) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| documents.upload (bundles) | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| evaluation.write | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| evaluation.read | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| committee.comment | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| committee.seal | ❌ | ❌ | ❌ | ❌ | ❌ | ✅* | ❌ |
| pv.export | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| market.query | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| agent.query | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

*\* `committee.seal` en E5 : uniquement si `can_advance == true`*

`agent.query` est disponible dans tous les états : l'agent peut répondre à
des questions de contexte (état du workspace, membres, processus) quel que soit
l'état. Les requêtes MQL sont internalement restreintes aux workspaces ayant
atteint E4+ par la logique du MQL Engine qui nécessite des `criterion_assessments`
existants pour contextualiser les données marché.

---

## 7. Agent Conversationnel V5 — O11

### 7.1 Architecture

```
POST /agent/prompt
      │
      ├─ Langfuse trace ouvert (INV-A01)
      │
      ├─ Semantic Router (Mistral Embed v2)
      │   │
      │   ├─ MARKET_QUERY (sim > 0.75)   → MQL Engine V8 (Section 8) → SSE
      │   ├─ WORKSPACE_STATUS (sim > 0.75) → workspace_handler()      → SSE
      │   ├─ PROCESS_INFO (sim > 0.75)     → process_handler()        → SSE
      │   ├─ OUT_OF_SCOPE (default)        → static_refusal()         → SSE
      │   └─ RECOMMENDATION (sim > 0.85)   → guardrail_block()        → JSON 422
      │         ↑ intercepté AVANT tout appel LLM
      │         tracé Langfuse tag "guardrail_inv_w06"
      │
      └─ Langfuse trace fermé
```

### 7.2 Route `/agent/prompt`

```python
# src/api/routers/agent.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
import json
import time

from src.auth.guard import guard
from src.agent.semantic_router import classify_intent, IntentClass
from src.agent.handlers import (
    mql_stream_handler,
    workspace_status_handler,
    process_info_handler,
    static_refusal_handler,
)
from src.agent.langfuse_client import get_langfuse, flush_langfuse
from src.agent.context_store import get_context, save_context
from src.agent.guardrail import check_recommendation_guardrail

router = APIRouter(prefix="/api", tags=["agent"])


class AgentPromptRequest(BaseModel):
    query: str
    workspace_id: Optional[UUID] = None
    session_id: Optional[str] = None


@router.post("/agent/prompt")
async def agent_prompt(
    payload: AgentPromptRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Point d'entrée unique de l'agent conversationnel.
    Retourne un stream SSE pour toutes les réponses sauf guardrail (JSON 422).
    """
    if payload.workspace_id:
        await guard(db, current_user, payload.workspace_id, "agent.query")

    langfuse = get_langfuse()
    trace = langfuse.trace(
        name="agent_prompt",
        user_id=str(current_user["id"]),
        metadata={
            "workspace_id": str(payload.workspace_id) if payload.workspace_id else None,
            "query_length": len(payload.query),
        },
    )

    try:
        guardrail_result = await check_recommendation_guardrail(
            payload.query, trace
        )
        if guardrail_result.blocked:
            trace.update(
                output={"blocked": True, "reason": "guardrail_inv_w06"},
                tags=["guardrail_inv_w06"],
            )
            raise HTTPException(
                422,
                {
                    "error": "guardrail_inv_w06",
                    "message": (
                        "DMS ne formule pas de recommandation. "
                        "Reformulez votre question pour demander des données factuelles."
                    ),
                    "confidence": guardrail_result.confidence,
                },
            )

        intent_span = trace.span(name="intent_classification")
        intent = await classify_intent(payload.query)
        intent_span.end(
            output={
                "intent": intent.intent_class.value,
                "confidence": intent.confidence,
            }
        )

        session_key = f"{payload.workspace_id or 'global'}:{payload.session_id or current_user['id']}"
        context = await get_context(session_key)

        if intent.intent_class == IntentClass.MARKET_QUERY:
            handler = mql_stream_handler
        elif intent.intent_class == IntentClass.WORKSPACE_STATUS:
            handler = workspace_status_handler
        elif intent.intent_class == IntentClass.PROCESS_INFO:
            handler = process_info_handler
        else:
            handler = static_refusal_handler

        async def event_generator():
            try:
                async for event in handler(
                    query=payload.query,
                    workspace_id=payload.workspace_id,
                    user=current_user,
                    db=db,
                    context=context,
                    trace=trace,
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                error_event = {
                    "type": "error",
                    "code": "handler_error",
                    "message": str(e),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                trace.update(
                    output={"error": str(e)},
                    level="ERROR",
                )
            finally:
                await save_context(session_key, context)
                trace.update(output={"completed": True})
                flush_langfuse()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        trace.update(output={"error": str(e)}, level="ERROR")
        flush_langfuse()
        raise HTTPException(500, f"Erreur agent : {str(e)}")
```

### 7.3 Semantic Router

```python
# src/agent/semantic_router.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import numpy as np
from src.agent.embedding_client import get_embedding


class IntentClass(str, Enum):
    MARKET_QUERY = "market_query"
    WORKSPACE_STATUS = "workspace_status"
    PROCESS_INFO = "process_info"
    RECOMMENDATION = "recommendation"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class IntentResult:
    intent_class: IntentClass
    confidence: float
    matched_centroid: Optional[str] = None


INTENT_EXAMPLES = {
    IntentClass.MARKET_QUERY: [
        "Quel est le prix du ciment à Mopti ?",
        "Prix médian des fournitures scolaires zone Sévaré",
        "Combien coûte le carburant à Bamako ce trimestre ?",
        "Évolution des prix du riz depuis janvier",
        "Comparaison prix entre Mopti et Gao",
        "Quels fournisseurs livrent du matériel médical ?",
        "Tendance prix du gasoil T1 2026",
        "Sources de prix disponibles pour le ciment",
    ],
    IntentClass.WORKSPACE_STATUS: [
        "Où en est le dossier RFQ-2026-041 ?",
        "Combien d'offres reçues pour ce processus ?",
        "Quels fournisseurs ont soumis ?",
        "Le quorum est-il atteint ?",
        "Quel est l'état de la matrice d'évaluation ?",
        "Combien de points signalés restent ouverts ?",
        "Qui fait partie du comité ?",
    ],
    IntentClass.PROCESS_INFO: [
        "Quels sont les seuils ECHO pour les consultations restreintes ?",
        "Quelle est la procédure DGMP pour un DAO ?",
        "Combien de membres minimum pour un comité ?",
        "Quels documents sont éliminatoires ?",
        "Quel est le délai réglementaire pour un appel d'offres ?",
    ],
    IntentClass.RECOMMENDATION: [
        "Quel fournisseur est le meilleur ?",
        "À qui devrait-on attribuer le marché ?",
        "Recommandez-moi un fournisseur",
        "Qui est le moins-disant ?",
        "Classez les fournisseurs du meilleur au pire",
        "Quel est le gagnant ?",
        "Qui devrait remporter le contrat ?",
    ],
}

_centroid_cache: dict[IntentClass, np.ndarray] = {}


async def _ensure_centroids():
    """Calcule les centroïdes si non en cache."""
    if _centroid_cache:
        return
    for intent_class, examples in INTENT_EXAMPLES.items():
        embeddings = []
        for example in examples:
            emb = await get_embedding(example)
            embeddings.append(emb)
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        _centroid_cache[intent_class] = centroid


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def classify_intent(query: str) -> IntentResult:
    """
    Classifie l'intent d'une requête par similarité cosinus
    avec les centroïdes pré-calculés.

    INV-A03 : routing sémantique, pas regex.
    """
    await _ensure_centroids()

    query_embedding = await get_embedding(query)
    query_norm = query_embedding / np.linalg.norm(query_embedding)

    best_class = IntentClass.OUT_OF_SCOPE
    best_sim = 0.0

    for intent_class, centroid in _centroid_cache.items():
        sim = _cosine_similarity(query_norm, centroid)
        if sim > best_sim:
            best_sim = sim
            best_class = intent_class

    if best_class == IntentClass.RECOMMENDATION and best_sim >= 0.85:
        return IntentResult(
            intent_class=IntentClass.RECOMMENDATION,
            confidence=best_sim,
        )

    if best_class != IntentClass.RECOMMENDATION and best_sim >= 0.75:
        return IntentResult(
            intent_class=best_class,
            confidence=best_sim,
        )

    return IntentResult(
        intent_class=IntentClass.OUT_OF_SCOPE,
        confidence=best_sim,
    )
```

### 7.4 Guardrail INV-W06

```python
# src/agent/guardrail.py

from dataclasses import dataclass
from src.agent.semantic_router import classify_intent, IntentClass


@dataclass
class GuardrailResult:
    blocked: bool
    confidence: float
    reason: str


async def check_recommendation_guardrail(query: str, trace) -> GuardrailResult:
    """
    INV-W06 appliqué à l'agent.
    Intercepte les tentatives de recommandation AVANT tout appel LLM.
    Confidence > 0.85 sur le centroïde RECOMMENDATION → bloqué.
    """
    intent = await classify_intent(query)

    if intent.intent_class == IntentClass.RECOMMENDATION and intent.confidence >= 0.85:
        span = trace.span(
            name="guardrail_inv_w06",
            input={"query": query, "confidence": intent.confidence},
            output={"blocked": True},
        )
        span.update(tags=["guardrail_inv_w06"])
        span.end()

        return GuardrailResult(
            blocked=True,
            confidence=intent.confidence,
            reason="Tentative de recommandation détectée",
        )

    return GuardrailResult(blocked=False, confidence=0.0, reason="")
```

### 7.5 Handlers

```python
# src/agent/handlers.py

from uuid import UUID
from typing import AsyncGenerator, Optional
from src.agent.llm_client import stream_mistral
from src.agent.circuit_breaker import get_model_with_breaker
from src.mql.engine import execute_mql_query
from src.agent.context_store import MQLContext


async def mql_stream_handler(
    query: str,
    workspace_id: Optional[UUID],
    user: dict,
    db,
    context: MQLContext,
    trace,
) -> AsyncGenerator[dict, None]:
    """Handler MARKET_QUERY — exécute MQL puis stream la réponse LLM."""
    yield {"type": "tool_call", "tool": "query_market", "status": "running"}

    mql_span = trace.span(name="mql_execution")
    mql_result = await execute_mql_query(
        db=db,
        tenant_id=user["tenant_id"],
        workspace_id=workspace_id,
        query=query,
        context=context,
    )
    mql_span.end(output={
        "template": mql_result.template_used,
        "rows": mql_result.row_count,
        "sources": len(mql_result.sources),
    })

    yield {
        "type": "sources",
        "sources": [
            {
                "name": s.name,
                "source_type": s.source_type,
                "publisher": s.publisher,
                "published_date": s.published_date.isoformat() if s.published_date else None,
                "is_official": s.is_official,
            }
            for s in mql_result.sources
        ],
        "has_official_source": any(s.is_official for s in mql_result.sources),
    }

    model = await get_model_with_breaker()
    llm_span = trace.span(name="llm_generation", input={"model": model})

    system_prompt = _build_mql_system_prompt(mql_result)
    messages = context.build_messages(system_prompt, query)

    async for token in stream_mistral(model, messages, llm_span):
        yield {"type": "token", "content": token}

    llm_span.end()

    await db.execute("""
        INSERT INTO mql_query_log
          (tenant_id, workspace_id, user_id, query_text,
           intent_classified, intent_confidence,
           template_used, sources_count, latency_ms,
           model_used, langfuse_trace_id)
        VALUES
          (:tid, :ws, :uid, :query,
           'market_query', :conf,
           :template, :src_count, :latency,
           :model, :trace_id)
    """, {
        "tid": user["tenant_id"],
        "ws": workspace_id,
        "uid": user["id"],
        "query": query,
        "conf": mql_result.confidence,
        "template": mql_result.template_used,
        "src_count": len(mql_result.sources),
        "latency": mql_result.latency_ms,
        "model": model,
        "trace_id": str(trace.id),
    })

    yield {"type": "done", "usage": {"model": model}}


async def workspace_status_handler(
    query: str,
    workspace_id: Optional[UUID],
    user: dict,
    db,
    context: MQLContext,
    trace,
) -> AsyncGenerator[dict, None]:
    """Handler WORKSPACE_STATUS — retourne l'état du workspace."""
    if not workspace_id:
        yield {
            "type": "token",
            "content": "Veuillez sélectionner un workspace pour consulter son état.",
        }
        yield {"type": "done", "usage": {}}
        return

    ws = await db.fetch_one(
        "SELECT * FROM process_workspaces WHERE id = :ws",
        {"ws": workspace_id}
    )
    if not ws:
        yield {"type": "token", "content": "Workspace introuvable."}
        yield {"type": "done", "usage": {}}
        return

    from src.cognitive.cognitive_state import compute_cognitive_state
    from src.api.cognitive_helpers import load_cognitive_facts

    facts = await load_cognitive_facts(db, ws)
    cog = compute_cognitive_state(facts)

    bundles = await db.fetch_all(
        "SELECT supplier_name_raw, supplier_name_resolved, status "
        "FROM supplier_bundles WHERE workspace_id = :ws",
        {"ws": workspace_id}
    )

    members = await db.fetch_all("""
        SELECT u.full_name, wm.role
        FROM workspace_memberships wm
        JOIN users u ON u.id = wm.user_id
        WHERE wm.workspace_id = :ws
    """, {"ws": workspace_id})

    open_flags = await db.fetch_val(
        "SELECT COUNT(*) FROM assessment_comments "
        "WHERE workspace_id = :ws AND is_flag = true AND resolved = false",
        {"ws": workspace_id}
    )

    model = await get_model_with_breaker()
    llm_span = trace.span(name="llm_workspace_status", input={"model": model})

    ws_context = (
        f"Workspace: {ws['reference_code']} — {ws['title']}\n"
        f"Phase: {cog.label_fr} ({cog.state.value})\n"
        f"Progression: {int(cog.completeness * 100)}%\n"
        f"Fournisseurs: {len(bundles)} offres reçues\n"
        f"Membres comité: {len(members)}\n"
        f"Points signalés ouverts: {open_flags}\n"
    )
    if cog.advance_blockers:
        ws_context += "En attente:\n"
        for b in cog.advance_blockers:
            ws_context += f"  - {b}\n"

    system = (
        "Tu es l'assistant DMS. Réponds en français, de manière concise et factuelle. "
        "Ne fais aucune recommandation. Ne classe aucun fournisseur. "
        "Voici les données du workspace :\n\n" + ws_context
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]

    async for token in stream_mistral(model, messages, llm_span):
        yield {"type": "token", "content": token}

    llm_span.end()
    yield {"type": "done", "usage": {"model": model}}


async def process_info_handler(
    query: str,
    workspace_id: Optional[UUID],
    user: dict,
    db,
    context: MQLContext,
    trace,
) -> AsyncGenerator[dict, None]:
    """Handler PROCESS_INFO — répond aux questions réglementaires."""
    model = await get_model_with_breaker()
    llm_span = trace.span(name="llm_process_info", input={"model": model})

    system = (
        "Tu es l'assistant DMS spécialisé dans les procédures de passation "
        "de marchés au Mali (DGMP, SCI, ECHO, OCHA). "
        "Réponds en français de manière précise et sourcée. "
        "Ne fais aucune recommandation d'attribution. "
        "Cite les textes réglementaires quand c'est possible."
    )
    messages = context.build_messages(system, query)

    async for token in stream_mistral(model, messages, llm_span):
        yield {"type": "token", "content": token}

    llm_span.end()
    yield {"type": "done", "usage": {"model": model}}


async def static_refusal_handler(
    query: str, workspace_id, user, db, context, trace,
) -> AsyncGenerator[dict, None]:
    """Handler OUT_OF_SCOPE — refus poli."""
    yield {
        "type": "token",
        "content": (
            "Je suis l'assistant DMS, spécialisé dans les processus "
            "de passation de marchés et les données de marché au Mali. "
            "Votre question sort de mon périmètre. "
            "Vous pouvez me poser des questions sur :\n"
            "• Les prix de marché (ciment, fournitures, carburant...)\n"
            "• L'état de vos workspaces en cours\n"
            "• Les procédures réglementaires (DGMP, ECHO, SCI)\n"
        ),
    }
    trace.update(tags=["out_of_scope"])
    yield {"type": "done", "usage": {}}


def _build_mql_system_prompt(mql_result) -> str:
    """Construit le system prompt pour le LLM après exécution MQL."""
    data_section = ""
    for row in mql_result.rows[:20]:
        data_section += f"  {row}\n"

    sources_section = ""
    for s in mql_result.sources:
        official = " (officiel)" if s.is_official else ""
        sources_section += f"  - {s.name} [{s.source_type}] par {s.publisher}{official}\n"

    return (
        "Tu es l'assistant DMS. Tu présentes des données de marché factuelles.\n"
        "RÈGLES ABSOLUES :\n"
        "- Ne recommande JAMAIS un fournisseur\n"
        "- Ne classe JAMAIS les offres\n"
        "- Ne désigne JAMAIS de gagnant\n"
        "- Présente les données avec leurs sources\n"
        "- Si les données sont insuffisantes, dis-le clairement\n\n"
        f"DONNÉES DE MARCHÉ :\n{data_section}\n"
        f"SOURCES :\n{sources_section}"
    )
```

### 7.6 LLM Client avec Streaming

```python
# src/agent/llm_client.py

from typing import AsyncGenerator
from mistralai import Mistral

_client = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        import os
        _client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return _client


async def stream_mistral(
    model: str,
    messages: list[dict],
    langfuse_span,
) -> AsyncGenerator[str, None]:
    """
    Stream les tokens depuis Mistral.
    Chaque token est yielded individuellement.
    Le span Langfuse est mis à jour avec l'usage final.
    """
    client = _get_client()

    response = await client.chat.stream_async(
        model=model,
        messages=messages,
    )

    full_content = ""
    usage = {}

    async for chunk in response:
        if chunk.data.choices:
            delta = chunk.data.choices[0].delta
            if delta.content:
                full_content += delta.content
                yield delta.content

        if chunk.data.usage:
            usage = {
                "input_tokens": chunk.data.usage.prompt_tokens,
                "output_tokens": chunk.data.usage.completion_tokens,
            }

    langfuse_span.update(
        output={"content_length": len(full_content)},
        metadata={"usage": usage},
    )
```

### 7.7 Embedding Client

```python
# src/agent/embedding_client.py

import numpy as np
from mistralai import Mistral
import os

_client = None


def _get_client() -> Mistral:
    global _client
    if not _client:
        _client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return _client


async def get_embedding(text: str) -> np.ndarray:
    """Retourne le vecteur d'embedding pour un texte donné."""
    client = _get_client()
    response = await client.embeddings.create_async(
        model="mistral-embed",
        inputs=[text],
    )
    return np.array(response.data[0].embedding, dtype=np.float32)
```

### 7.8 Context Store Redis

```python
# src/agent/context_store.py

import json
import redis.asyncio as redis
from dataclasses import dataclass, field
from typing import Optional
import os

MQL_CONTEXT_TTL = 3600  # 1h
MQL_CONTEXT_PREFIX = "mql:ctx:"

MAX_CONTEXT_TOKENS = 8000
SYSTEM_PROMPT_RESERVE = 1200
RESPONSE_RESERVE = 2000
HISTORY_BUDGET = MAX_CONTEXT_TOKENS - SYSTEM_PROMPT_RESERVE - RESPONSE_RESERVE  # 4800

_redis: Optional[redis.Redis] = None


async def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    return _redis


@dataclass
class MQLContext:
    messages: list[dict] = field(default_factory=list)
    workspace_id: Optional[str] = None

    def build_messages(self, system_prompt: str, user_query: str) -> list[dict]:
        """
        Construit la liste de messages pour le LLM.
        Applique la sliding window FIFO sur l'historique.
        Règle : un message "tool" est évicté avec son parent "assistant".
        """
        result = [{"role": "system", "content": system_prompt}]

        budget = HISTORY_BUDGET
        history_to_include = []

        for msg in reversed(self.messages):
            estimated_tokens = len(msg.get("content", "")) // 4
            if budget - estimated_tokens < 0:
                break
            history_to_include.insert(0, msg)
            budget -= estimated_tokens

        result.extend(history_to_include)
        result.append({"role": "user", "content": user_query})

        self.messages.append({"role": "user", "content": user_query})

        return result

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})


async def get_context(session_key: str) -> MQLContext:
    r = await _get_redis()
    key = MQL_CONTEXT_PREFIX + session_key
    data = await r.get(key)
    if data:
        parsed = json.loads(data)
        return MQLContext(
            messages=parsed.get("messages", []),
            workspace_id=parsed.get("workspace_id"),
        )
    return MQLContext()


async def save_context(session_key: str, context: MQLContext):
    r = await _get_redis()
    key = MQL_CONTEXT_PREFIX + session_key
    data = json.dumps({
        "messages": context.messages[-50:],
        "workspace_id": context.workspace_id,
    })
    await r.setex(key, MQL_CONTEXT_TTL, data)
```

### 7.9 Circuit Breaker

```python
# src/agent/circuit_breaker.py

import time
import asyncio
from dataclasses import dataclass, field
from enum import Enum


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


PRIMARY_MODEL = "mistral-small-latest"
FALLBACK_MODEL = "mistral-large-latest"

FAILURE_THRESHOLD = 3
FAILURE_WINDOW_SECONDS = 60
RECOVERY_TIMEOUT_SECONDS = 60


@dataclass
class CircuitBreaker:
    state: BreakerState = BreakerState.CLOSED
    failures: list[float] = field(default_factory=list)
    last_failure_time: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _clean_old_failures(self):
        now = time.time()
        self.failures = [
            t for t in self.failures
            if now - t < FAILURE_WINDOW_SECONDS
        ]

    async def record_failure(self):
        async with self._lock:
            now = time.time()
            self.failures.append(now)
            self.last_failure_time = now
            self._clean_old_failures()

            if len(self.failures) >= FAILURE_THRESHOLD:
                self.state = BreakerState.OPEN

    async def record_success(self):
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failures.clear()

    async def get_state(self) -> BreakerState:
        async with self._lock:
            if self.state == BreakerState.OPEN:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= RECOVERY_TIMEOUT_SECONDS:
                    self.state = BreakerState.HALF_OPEN
            return self.state


_breaker = CircuitBreaker()


async def get_model_with_breaker() -> str:
    """
    Retourne le modèle à utiliser selon l'état du circuit breaker.

    CLOSED    → Mistral Small (primary)
    OPEN      → Mistral Large (fallback)
    HALF_OPEN → Mistral Large + test recovery

    En double échec (fallback aussi en erreur) : lever une exception.
    L'appelant doit retourner HTTP 503 Retry-After: 30.
    """
    state = await _breaker.get_state()

    if state == BreakerState.CLOSED:
        return PRIMARY_MODEL
    else:
        return FALLBACK_MODEL
```

### 7.10 Événements SSE

| Type | Contenu | Moment |
|---|---|---|
| `token` | `{"type":"token","content":"Prix médian..."}` | Token par token |
| `tool_call` | `{"type":"tool_call","tool":"query_market","status":"running"}` | Appel MQL détecté |
| `sources` | `{"type":"sources","sources":[...],"has_official_source":true}` | Après exécution MQL |
| `done` | `{"type":"done","usage":{"model":"..."}}` | Fin du stream |
| `error` | `{"type":"error","code":"...","message":"..."}` | En cas d'erreur |

---

## 8. MQL Engine V8 — O12

### 8.1 Table `survey_campaigns`

Existe déjà en base (migration 042). Structure vérifiée :

```sql
-- survey_campaigns (existante)
-- Colonnes : id, tenant_id, name, source_type, publisher,
--            published_date, zone_coverage (TEXT[]), is_official,
--            reference_doc, doc_url, created_at
```

Types `source_type` acceptés : `mercurial_officiel`, `indice_prix_national`,
`enquete_terrain`, `devis_interne`, `cotation_externe`, `base_prix_bailleur`,
`mercurial_ong`.

### 8.2 Les 6 Templates SQL

```python
# src/mql/templates.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import date


@dataclass
class MQLParams:
    tenant_id: UUID
    article_pattern: Optional[str] = None
    zones: Optional[list[str]] = None
    vendor_pattern: Optional[str] = None
    min_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    proposed_price: Optional[float] = None
    zone: Optional[str] = None
    max_results: int = 50


MQL_TEMPLATES = {
    "T1_PRICE_MEDIAN": {
        "name": "Prix médian par article et zone",
        "sql": """
            SELECT
                ms.article_label,
                ms.zone,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                MIN(ms.unit_price) AS min_price,
                MAX(ms.unit_price) AS max_price,
                COUNT(*) AS sample_count,
                sc.name AS campaign_name,
                sc.source_type,
                sc.publisher,
                sc.published_date,
                sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.zone = ANY(:zones)
              AND ms.article_label ILIKE :article_pattern
              AND sc.published_date >= :min_date
            GROUP BY ms.article_label, ms.zone,
                     sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official
            ORDER BY sc.published_date DESC
            LIMIT :max_results
        """,
    },

    "T2_PRICE_TREND": {
        "name": "Évolution des prix sur période",
        "sql": """
            SELECT
                ms.article_label,
                DATE_TRUNC('month', sc.published_date) AS period,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                COUNT(*) AS sample_count,
                sc.source_type,
                sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.article_label ILIKE :article_pattern
              AND ms.zone = ANY(:zones)
              AND sc.published_date BETWEEN :start_date AND :end_date
            GROUP BY ms.article_label, DATE_TRUNC('month', sc.published_date),
                     sc.source_type, sc.is_official
            ORDER BY period ASC
        """,
    },

    "T3_VENDOR_HISTORY": {
        "name": "Historique prix par fournisseur",
        "sql": """
            SELECT
                ms.vendor_name, ms.article_label, ms.unit_price,
                ms.zone, sc.name AS campaign_name,
                sc.published_date, sc.source_type, sc.is_official
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.vendor_name ILIKE :vendor_pattern
              AND sc.published_date >= :min_date
            ORDER BY sc.published_date DESC
            LIMIT :max_results
        """,
    },

    "T4_ZONE_COMPARISON": {
        "name": "Comparaison inter-zones",
        "sql": """
            SELECT
                ms.zone, ms.article_label,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                COUNT(DISTINCT ms.vendor_name) AS vendor_count,
                COUNT(*) AS sample_count
            FROM market_surveys ms
            JOIN survey_campaigns sc ON ms.campaign_id = sc.id
            WHERE ms.tenant_id = :tenant_id
              AND ms.article_label ILIKE :article_pattern
              AND sc.published_date >= :min_date
            GROUP BY ms.zone, ms.article_label
            ORDER BY ms.zone
        """,
    },

    "T5_ANOMALY_DETECTION": {
        "name": "Détection d'écart de prix",
        "sql": """
            WITH stats AS (
                SELECT
                    ms.article_label, ms.zone,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median,
                    STDDEV(ms.unit_price) AS stddev
                FROM market_surveys ms
                JOIN survey_campaigns sc ON ms.campaign_id = sc.id
                WHERE ms.tenant_id = :tenant_id
                  AND sc.published_date >= :min_date
                GROUP BY ms.article_label, ms.zone
            )
            SELECT
                s.article_label, s.zone, s.median, s.stddev,
                :proposed_price AS proposed_price,
                CASE WHEN s.stddev > 0
                    THEN ROUND(((:proposed_price - s.median) / s.stddev)::numeric, 2)
                    ELSE 0
                END AS z_score,
                ROUND(((:proposed_price - s.median) / NULLIF(s.median, 0) * 100)::numeric, 1)
                    AS pct_deviation
            FROM stats s
            WHERE s.article_label ILIKE :article_pattern
              AND s.zone = ANY(:zones)
        """,
    },

    "T6_CAMPAIGN_INVENTORY": {
        "name": "Inventaire des campagnes disponibles",
        "sql": """
            SELECT
                sc.name, sc.source_type, sc.publisher,
                sc.published_date, sc.is_official, sc.zone_coverage,
                COUNT(ms.id) AS survey_count,
                COUNT(DISTINCT ms.article_label) AS article_count,
                COUNT(DISTINCT ms.vendor_name) AS vendor_count
            FROM survey_campaigns sc
            LEFT JOIN market_surveys ms ON ms.campaign_id = sc.id
            WHERE sc.tenant_id = :tenant_id
              AND (:zone IS NULL OR :zone = ANY(sc.zone_coverage))
            GROUP BY sc.id, sc.name, sc.source_type, sc.publisher,
                     sc.published_date, sc.is_official, sc.zone_coverage
            ORDER BY sc.published_date DESC
        """,
    },
}
```

### 8.3 MQL Engine

```python
# src/mql/engine.py

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID
import time

from src.mql.templates import MQL_TEMPLATES, MQLParams
from src.mql.param_extractor import extract_mql_params
from src.mql.template_selector import select_template


@dataclass
class MQLSource:
    name: str
    source_type: str
    publisher: str
    published_date: Optional[date]
    is_official: bool


@dataclass
class MQLResult:
    template_used: str
    rows: list[dict]
    row_count: int
    sources: list[MQLSource]
    confidence: float
    latency_ms: int
    params_used: dict


async def execute_mql_query(
    db,
    tenant_id: UUID,
    workspace_id: Optional[UUID],
    query: str,
    context,
) -> MQLResult:
    """
    Exécute une requête MQL complète :
    1. Extraire les paramètres de la question en langage naturel
    2. Sélectionner le template SQL approprié
    3. Exécuter la requête paramétrée (INV-A02 : zéro concaténation SQL)
    4. Collecter les sources (INV-A04)
    5. Retourner le résultat structuré
    """
    start = time.monotonic()

    params = await extract_mql_params(query, tenant_id)

    template_key = await select_template(query, params)
    template = MQL_TEMPLATES[template_key]

    bind_params = {
        "tenant_id": tenant_id,
        "article_pattern": f"%{params.article_pattern}%" if params.article_pattern else "%",
        "zones": params.zones or ["Bamako", "Mopti", "Sévaré", "Gao"],
        "vendor_pattern": f"%{params.vendor_pattern}%" if params.vendor_pattern else "%",
        "min_date": params.min_date or date(2025, 1, 1),
        "start_date": params.start_date or date(2025, 1, 1),
        "end_date": params.end_date or date.today(),
        "proposed_price": params.proposed_price or 0,
        "zone": params.zones[0] if params.zones else None,
        "max_results": params.max_results,
    }

    rows = await db.fetch_all(template["sql"], bind_params)
    rows_dict = [dict(r) for r in rows]

    sources_seen = set()
    sources = []
    for row in rows_dict:
        src_key = row.get("campaign_name") or row.get("name")
        if src_key and src_key not in sources_seen:
            sources_seen.add(src_key)
            sources.append(MQLSource(
                name=src_key,
                source_type=row.get("source_type", "unknown"),
                publisher=row.get("publisher", "unknown"),
                published_date=row.get("published_date"),
                is_official=row.get("is_official", False),
            ))

    elapsed_ms = int((time.monotonic() - start) * 1000)

    confidence = _compute_mql_confidence(rows_dict, sources)

    return MQLResult(
        template_used=template_key,
        rows=rows_dict,
        row_count=len(rows_dict),
        sources=sources,
        confidence=confidence,
        latency_ms=elapsed_ms,
        params_used={
            "article": params.article_pattern,
            "zones": params.zones,
            "vendor": params.vendor_pattern,
        },
    )


def _compute_mql_confidence(rows: list[dict], sources: list[MQLSource]) -> float:
    """Confiance basée sur le volume de données et la qualité des sources."""
    if not rows:
        return 0.0

    base = min(0.5, len(rows) / 20.0)

    official_bonus = 0.3 if any(s.is_official for s in sources) else 0.0
    multi_source_bonus = 0.2 if len(sources) >= 2 else 0.0

    return min(1.0, base + official_bonus + multi_source_bonus)
```

### 8.4 Parameter Extractor

```python
# src/mql/param_extractor.py

from src.mql.templates import MQLParams
from uuid import UUID
from datetime import date
import re


ZONE_KEYWORDS = {
    "bamako": "Bamako",
    "mopti": "Mopti",
    "sévaré": "Sévaré",
    "sevare": "Sévaré",
    "gao": "Gao",
    "ségou": "Ségou",
    "segou": "Ségou",
    "tombouctou": "Tombouctou",
    "kidal": "Kidal",
    "sikasso": "Sikasso",
    "kayes": "Kayes",
    "koulikoro": "Koulikoro",
}


async def extract_mql_params(query: str, tenant_id: UUID) -> MQLParams:
    """
    Extraction déterministe des paramètres depuis la question.
    Pas de LLM ici — règles simples et fiables.
    L'extraction LLM est réservée aux cas complexes en V5.2.
    """
    query_lower = query.lower()

    zones = []
    for keyword, zone_name in ZONE_KEYWORDS.items():
        if keyword in query_lower:
            zones.append(zone_name)

    article = _extract_article(query_lower)

    vendor = None
    vendor_keywords = ["fournisseur", "vendor", "société", "sarl", "ets"]
    for kw in vendor_keywords:
        if kw in query_lower:
            match = re.search(rf'{kw}\s+(\w+)', query_lower)
            if match:
                vendor = match.group(1)
                break

    min_date = date(2025, 1, 1)
    year_match = re.search(r'20[2-3]\d', query)
    if year_match:
        year = int(year_match.group())
        min_date = date(year, 1, 1)

    quarter_match = re.search(r'[TQ]([1-4])\s*20[2-3]\d', query, re.IGNORECASE)
    start_date = None
    end_date = None
    if quarter_match and year_match:
        q = int(quarter_match.group(1))
        y = int(year_match.group())
        start_date = date(y, (q - 1) * 3 + 1, 1)
        end_month = q * 3
        if end_month == 12:
            end_date = date(y, 12, 31)
        else:
            end_date = date(y, end_month + 1, 1)

    proposed_price = None
    price_match = re.search(r'(\d[\d\s]*(?:\.\d+)?)\s*(?:fcfa|xof|cfa|francs?)', query_lower)
    if price_match:
        proposed_price = float(price_match.group(1).replace(" ", ""))

    return MQLParams(
        tenant_id=tenant_id,
        article_pattern=article,
        zones=zones or None,
        vendor_pattern=vendor,
        min_date=min_date,
        start_date=start_date,
        end_date=end_date,
        proposed_price=proposed_price,
    )


def _extract_article(query_lower: str) -> str:
    """Extrait l'article principal de la question."""
    stop_words = {
        "quel", "quelle", "quels", "quelles", "est", "le", "la", "les",
        "de", "du", "des", "un", "une", "prix", "coût", "cout",
        "médian", "median", "moyen", "moyenne", "combien",
        "tendance", "évolution", "evolution", "comparaison",
        "fournisseur", "fournisseurs", "zone", "à", "a",
        "ce", "cette", "trimestre", "mois", "année", "annee",
    }

    words = re.findall(r'\b[a-zéèêëàâùûôîïç]+\b', query_lower)
    meaningful = [w for w in words if w not in stop_words and len(w) > 2]

    if meaningful:
        return " ".join(meaningful[:3])
    return "%"
```

### 8.5 Template Selector

```python
# src/mql/template_selector.py

from src.mql.templates import MQLParams


async def select_template(query: str, params: MQLParams) -> str:
    """
    Sélectionne le template SQL approprié basé sur les paramètres extraits.
    Logique déterministe — pas de LLM.
    """
    query_lower = query.lower()

    if any(kw in query_lower for kw in ["source", "campagne", "inventaire", "disponible"]):
        return "T6_CAMPAIGN_INVENTORY"

    if params.proposed_price is not None:
        return "T5_ANOMALY_DETECTION"

    if params.vendor_pattern:
        return "T3_VENDOR_HISTORY"

    if any(kw in query_lower for kw in ["tendance", "évolution", "evolution", "depuis", "entre"]):
        return "T2_PRICE_TREND"

    if params.zones and len(params.zones) >= 2:
        return "T4_ZONE_COMPARISON"
    if any(kw in query_lower for kw in ["comparaison", "comparer", "entre"]):
        return "T4_ZONE_COMPARISON"

    return "T1_PRICE_MEDIAN"
```

### 8.6 Route MQL interne

```python
# src/api/routers/mql.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/api", tags=["mql"])


class MQLStreamRequest(BaseModel):
    query: str
    workspace_id: Optional[UUID] = None


@router.post("/mql/stream")
async def mql_stream(
    payload: MQLStreamRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Route interne MQL. Permission mql.internal (admin uniquement).
    Utilisée pour le debug et les tests.
    L'agent utilise le MQL Engine directement, pas cette route.
    """
    role_perms = ROLE_PERMISSIONS.get(current_user.get("role", ""), [])
    if "mql.internal" not in role_perms and "system.admin" not in role_perms:
        raise HTTPException(403, "Permission mql.internal requise")

    from src.mql.engine import execute_mql_query
    result = await execute_mql_query(
        db=db,
        tenant_id=current_user["tenant_id"],
        workspace_id=payload.workspace_id,
        query=payload.query,
        context=None,
    )

    return {
        "template": result.template_used,
        "rows": result.rows,
        "row_count": result.row_count,
        "sources": [
            {"name": s.name, "source_type": s.source_type,
             "publisher": s.publisher, "is_official": s.is_official}
            for s in result.sources
        ],
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
    }
```

### 8.7 Migration mql_query_log

```python
# alembic/versions/v51_001_mql_query_log.py

def upgrade():
    op.create_table(
        'mql_query_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workspace_id', UUID(as_uuid=True),
                  sa.ForeignKey('process_workspaces.id'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('intent_classified', sa.String(50), nullable=False),
        sa.Column('intent_confidence', sa.Numeric(4, 3), nullable=False),
        sa.Column('template_used', sa.String(50), nullable=True),
        sa.Column('sources_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=False),
        sa.Column('langfuse_trace_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )
    op.create_index('idx_mql_log_tenant', 'mql_query_log', ['tenant_id'])
    op.create_index('idx_mql_log_workspace', 'mql_query_log', ['workspace_id'])
    op.create_index('idx_mql_log_created', 'mql_query_log', ['created_at'])

    op.execute("ALTER TABLE mql_query_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE mql_query_log FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY mql_log_tenant_isolation ON mql_query_log
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)

def downgrade():
    op.drop_table('mql_query_log')
```

---

## 9. Langfuse Tracing — O13

### 9.1 Client Langfuse

```python
# src/agent/langfuse_client.py

import os
from typing import Optional
from langfuse import Langfuse

_langfuse: Optional[Langfuse] = None


def get_langfuse() -> Langfuse:
    """
    Retourne le client Langfuse singleton.
    Configuration via variables d'environnement.
    INV-A01 : tout appel LLM est tracé.
    """
    global _langfuse
    if _langfuse is None:
        _langfuse = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "https://langfuse.dms.internal"),
        )
    return _langfuse


def flush_langfuse():
    """Flush les traces en attente. Appelé à la fin de chaque requête agent."""
    if _langfuse:
        _langfuse.flush()
```

### 9.2 Structure des Traces

Chaque appel à `/agent/prompt` crée une trace Langfuse avec la structure :

```
trace: agent_prompt
  ├─ span: guardrail_inv_w06 (si détecté)
  ├─ span: intent_classification
  │   output: {intent: "market_query", confidence: 0.87}
  ├─ span: mql_execution (si MARKET_QUERY)
  │   output: {template: "T1_PRICE_MEDIAN", rows: 12, sources: 3}
  └─ span: llm_generation
      input: {model: "mistral-small-latest"}
      output: {content_length: 342}
      metadata: {usage: {input_tokens: 512, output_tokens: 342}}
```

### 9.3 Variables d'environnement Langfuse

```
LANGFUSE_PUBLIC_KEY    : Clé publique Langfuse
LANGFUSE_SECRET_KEY    : Clé secrète Langfuse
LANGFUSE_HOST          : URL du serveur Langfuse self-hosted
```

### 9.4 Impact sur O5 (Extraction)

Tout appel LLM d'extraction (Mistral Large, Mistral OCR) est également tracé :

```python
from src.agent.langfuse_client import get_langfuse, flush_langfuse

langfuse = get_langfuse()
trace = langfuse.trace(
    name="document_extraction",
    metadata={"document_id": str(doc_id), "document_type": mime_type},
)
extraction_span = trace.span(name="mistral_extraction", input={"model": model})
# ... appel Mistral ...
extraction_span.end(output={"fields_extracted": len(fields), "confidence": avg_confidence})
flush_langfuse()
```

---

## 10. Offline-First — O14 (Spécification Architecture)

**Ce bloc est une spécification cible. Aucun code n'est livré dans V5.1.0.**

### 10.1 Architecture Cible

```
COUCHE 1 — Service Worker (Serwist)
  Cache statique (app shell, JS, CSS)
  Cache API dynamique (stale-while-revalidate)
  Background sync pour mutations en queue

COUCHE 2 — TanStack Query Persistence
  persistQueryClient → IndexedDB
  gcTime: 24h
  networkMode: offlineFirst

COUCHE 3 — Mutation Queue
  Mutations stockées en IndexedDB
  Sync automatique au retour réseau
  Résolution : last-write-wins + timestamp serveur

COUCHE 4 — Connectivity Monitor
  navigator.onLine + health check /health toutes les 15s
  ConnectivityBanner dans le layout
```

### 10.2 Conditions d'Implémentation

L'implémentation de O14 interviendra quand :
1. V5.1 a été utilisé pendant au moins 1 mois en production
2. Les patterns de connectivité terrain ont été mesurés (latence, taux de coupure)
3. Les cas d'usage offline prioritaires ont été identifiés par les utilisateurs

### 10.3 Impact sur le Reste de l'Architecture

O14 n'a aucun impact sur les autres couches dans V5.1. Le frontend utilise
`TanStack Query` avec `staleTime: 30000` et `retry: 3`, ce qui fournit déjà
une résilience basique aux coupures courtes (< 30s).

---

## 11. Invariants — 28

### Invariants Workspace (INV-W) — 6

```
INV-W01 : Quorum ≥ 4 membres dont ≥ 1 votant par rôle critique pour scellement.
INV-W02 : Scellement irréversible. Aucune modification après seal_hash.
INV-W03 : Somme poids critères non-éliminatoires = 100%. Éliminatoires = 0%.
INV-W04 : Critères éliminatoires évalués avant pondérés.
INV-W05 : pv_snapshot figé après seal. Trigger immutabilité PostgreSQL.
INV-W06 : winner/rank/recommendation/selected_vendor interdits partout.
```

### Invariants Sécurité (INV-S) — 4

```
INV-S01 : RLS activée et forcée sur chaque table métier. tenant_id NOT NULL + FK.
INV-S02 : Chaque route vérifie membership + permission + seal status via guard().
INV-S03 : deliberation_messages et pv_snapshot append-only (triggers DB).
INV-S04 : assessment_comments content/is_flag immutables (trigger DB).
```

### Invariants Données (INV-D) — 2

```
INV-D01 : tenant_id NOT NULL + FK sur chaque table métier.
INV-D02 : score dans [0, 1000], confidence dans [0, 1]. CHECK constraints.
```

### Invariants Cognitifs (INV-C) — 4

```
INV-C01 : L'état cognitif E0-E6 est une PROJECTION. Jamais une colonne SQL.
INV-C02 : L'UI affiche available_actions selon l'état. Le guard protège les données.
INV-C03 : CognitiveFacts chargé depuis la DB à chaque requête. Jamais caché.
INV-C04 : advance_blockers = liste de raisons lisibles en français.
```

### Invariants Frontend (INV-F) — 6

```
INV-F01 : Types API générés depuis OpenAPI. Aucun type API défini manuellement.
INV-F02 : ErrorBoundary sur chaque feature. Aucun crash React non capturé.
INV-F03 : ConfidenceBadge combine couleur + forme + texte (WCAG 2.1 AA).
INV-F04 : Sidebar affiche sections dont état ≥ minState atteint.
INV-F05 : Toute mutation utilise TanStack Query useMutation avec retry 3.
INV-F06 : Dashboard se refresh toutes les 30s. Tri par urgence automatique.
```

### Invariants Agent & MQL (INV-A) — 6

```
INV-A01 : Tout appel LLM est tracé dans Langfuse self-hosted AVANT toute
          réponse au client. Aucune réponse agent non tracée n'est valide.

INV-A02 : Les 6 templates SQL sont paramétrés (bindparams). Aucune
          concaténation de chaîne SQL. Zéro injection.

INV-A03 : Le routing est sémantique (embedding cosine similarity).
          Le routing par regex/keywords est interdit pour la classification
          d'intent. L'extraction de paramètres MQL utilise des règles
          déterministes (pas de LLM).

INV-A04 : Toute réponse MQL expose les sources au niveau campaign
          (name, source_type, publisher, published_date, is_official).
          L'affichage "source: market_surveys" seul est interdit.

INV-A05 : La tentative de recommandation (confidence > 0.85 sur centroïde
          RECOMMENDATION) est interceptée au semantic router AVANT tout
          appel LLM. Le refus est tracé Langfuse tag "guardrail_inv_w06".

INV-A06 : Le circuit breaker surveille Mistral Small. En état "open" :
          basculement sur Mistral Large. En double échec : HTTP 503
          Retry-After: 30. Le basculement est transparent.
```

**Total : 28 invariants.**

---

## 12. Tests de Verrouillage — 16 Tests

```
┌─────┬────────────────────────────────────────────┬──────────────────┐
│ #   │ Invariant testé                            │ Type             │
├─────┼────────────────────────────────────────────┼──────────────────┤
│ 1   │ INV-W06 — Zéro mot interdit en sortie     │ E2E pytest       │
│ 2   │ INV-W05 — Snapshot immutable après seal    │ DB trigger       │
│ 3   │ INV-W03 — Weight validation                │ Unit             │
│ 4   │ INV-S01 — RLS cross-tenant                 │ Integration      │
│ 5   │ INV-S02 — Guard bloque observer            │ Integration      │
│ 6   │ INV-S02 — Guard bloque écriture post-seal  │ Integration      │
│ 7   │ INV-S03 — Messages append-only             │ DB trigger       │
│ 8   │ INV-S04 — Comments content immutable       │ DB trigger       │
│ 9   │ INV-D02 — CHECK constraints score/conf     │ DB               │
│ 10  │ INV-C01 — Cognitive state = projection     │ Unit             │
│ 11  │ INV-F01 — Types frontend = OpenAPI          │ CI diff          │
│ 12  │ INV-F06 — Dashboard retourne tous les ws    │ Integration      │
│ 13  │ INV-A01 — Langfuse trace chaque appel LLM  │ Integration      │
│ 14  │ INV-A05 — Guardrail bloque recommandation   │ Unit             │
│ 15  │ INV-A06 — Circuit breaker bascule           │ Unit mock        │
│ 16  │ INV-A04 — MQL sources au niveau campaign    │ Integration      │
└─────┴────────────────────────────────────────────┴──────────────────┘
```

### Tests 13-16 (nouveaux V5.1)

```python
# tests/integration/test_langfuse_tracing.py

@pytest.mark.asyncio
async def test_agent_prompt_creates_langfuse_trace(test_client, mock_langfuse):
    """INV-A01 : tout appel agent crée une trace Langfuse."""
    response = await test_client.post(
        "/api/agent/prompt",
        json={"query": "Prix du ciment à Mopti"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert mock_langfuse.trace_called
    assert mock_langfuse.last_trace.name == "agent_prompt"


# tests/unit/test_guardrail.py

@pytest.mark.asyncio
async def test_recommendation_blocked_before_llm(mock_embeddings):
    """INV-A05 : recommandation interceptée avant appel LLM."""
    from src.agent.guardrail import check_recommendation_guardrail

    mock_trace = MockTrace()
    result = await check_recommendation_guardrail(
        "Quel fournisseur recommandez-vous ?", mock_trace
    )
    assert result.blocked is True
    assert result.confidence >= 0.85
    assert "guardrail_inv_w06" in mock_trace.tags


@pytest.mark.asyncio
async def test_legitimate_query_not_blocked(mock_embeddings):
    """Les requêtes légitimes passent le guardrail."""
    mock_trace = MockTrace()
    result = await check_recommendation_guardrail(
        "Quel est le prix médian du ciment ?", mock_trace
    )
    assert result.blocked is False


# tests/unit/test_circuit_breaker.py

@pytest.mark.asyncio
async def test_breaker_opens_after_3_failures():
    """INV-A06 : 3 erreurs en 60s → basculement Mistral Large."""
    from src.agent.circuit_breaker import (
        CircuitBreaker, get_model_with_breaker,
        PRIMARY_MODEL, FALLBACK_MODEL, _breaker, BreakerState,
    )

    _breaker.state = BreakerState.CLOSED
    _breaker.failures.clear()

    for _ in range(3):
        await _breaker.record_failure()

    model = await get_model_with_breaker()
    assert model == FALLBACK_MODEL


@pytest.mark.asyncio
async def test_breaker_recovers_after_success():
    """Le breaker revient en CLOSED après un succès en HALF_OPEN."""
    _breaker.state = BreakerState.HALF_OPEN
    await _breaker.record_success()
    assert _breaker.state == BreakerState.CLOSED


# tests/integration/test_mql_sources.py

@pytest.mark.asyncio
async def test_mql_response_includes_campaign_sources(test_client, db_pool):
    """INV-A04 : chaque réponse MQL expose les sources au niveau campaign."""
    await _seed_market_data(db_pool)

    response = await test_client.post(
        "/api/mql/stream",
        json={"query": "Prix du ciment à Mopti"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    body = response.json()
    assert "sources" in body
    assert len(body["sources"]) > 0
    for src in body["sources"]:
        assert "name" in src
        assert "source_type" in src
        assert "publisher" in src
        assert "is_official" in src
```

### GitHub Actions V5.1

```yaml
# .github/workflows/dms_invariants_v51.yml

name: DMS V5.1 — 16 Tests de Verrouillage

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  DATABASE_URL: "postgresql://postgres:test@localhost/dms_test"
  REDIS_URL: "redis://localhost:6379"
  JWT_SECRET: "test-secret-minimum-32-characters-long"
  MISTRAL_API_KEY: "test-key"
  LANGFUSE_PUBLIC_KEY: "test-pk"
  LANGFUSE_SECRET_KEY: "test-sk"
  LANGFUSE_HOST: "http://localhost:3000"
  TESTING: "true"

jobs:
  invariants:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_PASSWORD: test, POSTGRES_DB: dms_test }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: --health-cmd "redis-cli ping"

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements-test.txt
      - run: alembic upgrade head

      - name: "Test 1 — INV-W06"
        run: pytest tests/e2e/test_inv_w06_e2e.py -v
      - name: "Test 2 — INV-W05"
        run: pytest tests/db/test_snapshot_immutability.py -v
      - name: "Test 3 — INV-W03"
        run: pytest tests/unit/test_weight_validator.py -v
      - name: "Test 4 — INV-S01"
        run: pytest tests/integration/test_rls_cross_tenant.py -v
      - name: "Test 5 — INV-S02 observer"
        run: pytest tests/integration/test_guard_observer.py -v
      - name: "Test 6 — INV-S02 sealed"
        run: pytest tests/integration/test_guard_sealed.py -v
      - name: "Test 7 — INV-S03"
        run: pytest tests/db/test_messages_append_only.py -v
      - name: "Test 8 — INV-S04"
        run: pytest tests/db/test_comments_integrity.py -v
      - name: "Test 9 — INV-D02"
        run: pytest tests/db/test_check_constraints.py -v
      - name: "Test 10 — INV-C01"
        run: pytest tests/unit/test_cognitive_projection.py -v
      - name: "Test 11 — INV-F01"
        run: |
          cd frontend
          npx openapi-typescript ../docs/ANNEX_A_openapi.json --output /tmp/fresh.ts
          diff src/contracts/api-types.ts /tmp/fresh.ts
      - name: "Test 12 — INV-F06"
        run: pytest tests/integration/test_dashboard.py -v

      - name: "Test 13 — INV-A01 Langfuse"
        run: pytest tests/integration/test_langfuse_tracing.py -v
      - name: "Test 14 — INV-A05 Guardrail"
        run: pytest tests/unit/test_guardrail.py -v
      - name: "Test 15 — INV-A06 Circuit Breaker"
        run: pytest tests/unit/test_circuit_breaker.py -v
      - name: "Test 16 — INV-A04 MQL Sources"
        run: pytest tests/integration/test_mql_sources.py -v
```

---

## 13. Plan d'Implémentation — 30 Jours, 4 Voies

```
VOIE A (CORE)          S1              S2              S3
                       J1  J2  J3  J4  J5  J6  J7  J8  J9  J10  J11

  J1  Setup Railway+PG+Redis+migrations    ██
  J2  Auth JWT+RBAC+guard                      ██
  J3  RLS toutes tables                            ██
  J4  Workspaces+cognitive engine                      ██
  J5  Members+quorum                                       ██
  J6  Bundles+extraction+confidence                            ██  ██
  J7  Eval criteria+M16 tables                                         ██
  J8  Deliberation+comments+signal engine                                  ██
  J9  Seal+SHA-256+snapshot                                                    ██
  J10 Dashboard endpoint                                                           ██
  J11 Export routes PV                                                                 ██

VOIE B (FRONTEND)      S1              S2              S3              S4
                       J1  J2  J3  J4  J5  J6  J7  J8  J9  J10  J11  J12  J13

  F1  Setup Next.js+shadcn+types gen  ██
  F2  Auth+layout+tenant                  ██
  F3  Dashboard multi-workspace               ██  ██
  F4  Workspace+cognitive state                       ██
  F5  Sidebar+header                                      ██
  F6  E0-E1 Intake+upload                                     ██
  F7  E2 Bundles                                                  ██
  F8  E3-E4 ComparativeTable                                          ██  ██
  F9  HITL inline                                                             ██
  F10 E5 Comments+Flags                                                           ██
  F11 E6 Seal+exports                                                                 ██
  F12 Agent console frontend                                                              ██
  F13 Cmd+K+polish+a11y                                                                       ██

VOIE C (DOCGEN)        S2              S3
                       J5  J6  J7  J8  J9  J10

  D1  Jinja2 5 partials            ██  ██
  D2  WeasyPrint PDF                       ██
  D3  openpyxl XLSX                            ██
  D4  Weight validator+signal engine               ██
  D5  Integration docgen+routes                        ██

VOIE D (AGENT+MQL)     S2              S3              S4
                       J6  J7  J8  J9  J10  J11  J12  J13

  M1  MQL templates+engine                 ██  ██
  M2  Param extractor+template selector            ██
  M3  Semantic router+centroïdes                       ██  ██
  M4  Guardrail INV-W06                                        ██
  M5  Agent /prompt+handlers                                       ██
  M6  SSE streaming+LLM client                                        ██
  M7  Circuit breaker                                                     ██
  M8  Langfuse integration                                                    ██
  M9  Redis context store                                                         ██
  M10 mql_query_log+tests                                                            ██

INTÉGRATION                                                                      ██  ██
  I1  16 tests de verrouillage                                                   ██
  I2  CI pipeline final                                                              ██
  I3  Tag v5.1.0                                                                     ██

DÉPENDANCES CRITIQUES :
  F3  attend J4 (cognitive state)
  F7  attend J6 (extraction)
  F8  attend J7 (M16 tables)
  F10 attend J8 (comments)
  F11 attend J9 (seal)
  F12 attend M5 (agent)
  D1  attend J9 (snapshot)
  M3  attend M1 (templates)
  M5  attend M3+M4 (router+guardrail)
  M8  attend M5 (agent handlers)
  I1  attend J11+F13+M10 (tout)
```

### Estimation

| Voie | Jours | Profil |
|---|---|---|
| A (Core Backend) | 11 | Backend senior |
| B (Frontend) | 13 | Frontend senior |
| C (DocGen) | 6 | Backend |
| D (Agent+MQL) | 10 | Backend + LLM |
| Intégration | 3 | Full-stack + QA |
| **Calendrier** | **30 jours** | **2-3 développeurs** |

---

## 14. Architecture des Silences

```
❌ Recommander un fournisseur
❌ Classer les offres
❌ Calculer un score global désignant un gagnant
❌ Modifier le snapshot après scellement
❌ Générer un PDF depuis les tables courantes (non scellées)
❌ Exposer des données d'un tenant à un autre
❌ Modifier le contenu d'un commentaire après insertion
❌ Supprimer un message de délibération
❌ Utiliser USAID comme profil réglementaire
❌ Afficher un gagnant visuel par couleur dans les exports XLSX
❌ Persister l'état cognitif comme colonne SQL
❌ Bloquer l'utilisateur avec un guard quand l'UI devrait guider
❌ Retourner une réponse agent sans trace Langfuse (INV-A01)
❌ Construire une requête SQL par concaténation de chaînes (INV-A02)
❌ Router les intents agent par regex en production (INV-A03)
❌ Afficher des données marché sans attribution source campaign (INV-A04)
❌ Appeler le LLM sur une tentative de recommandation (INV-A05)
```

---

## 15. Formulation Finale Opposable

> Le DMS est un système de documentation décisionnelle assisté par IA,
> conçu comme extension cognitive de l'expert procurement.
> Il enregistre, structure, et scelle les actes d'un comité de dépouillement.
> Il transforme 100 offres en données structurées.
> Il organise 20 contrats en parallèle.
> Il compresse 1 mois de processus en 1 journée.
> Son agent conversationnel interroge les données de marché avec traçabilité
> complète et ne formule jamais de recommandation.
> Tout appel LLM est tracé dans Langfuse avant toute réponse.
> Il ne décide jamais. Il ne recommande jamais. Il ne classe jamais.
> Toute décision d'attribution appartient exclusivement au comité humain.
> Tout document généré est opposable parce qu'il est issu d'un snapshot
> cryptographiquement scellé et jamais modifié après scellement.

---

## 16. Contexte de Verrouillage Final

```
Version            : V5.1.0 FINAL
Date de gel        : 07 avril 2026
Branche            : main
Invariants actifs  : 28 (6W + 4S + 2D + 4C + 6F + 6A)
Tests verrouillage : 16 (CI obligatoires sur main)
Corrections        : C1–C26
Couches codées     : O0–O13 (14 couches)
Couche spec only   : O14 (Offline-First — post-adoption)
Plan               : 30 jours, 4 voies parallèles, 2-3 développeurs
Prochaine étape    : Jour 1 — J1 (Setup Railway) + F1 (Setup Next.js)

Ce document ne change plus. Toute évolution = Canon V5.2.0.
```

---

*DMS Canon V5.1.0 FINAL — Decision Memory System*
*Save the Children International Mali*
*Opposable, exécutable, auditable, tracé. Prêt pour Jour 1.*
