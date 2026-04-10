"""Agent Handlers — Canon V5.1.0 Section 7.5.

4 handlers couvrant les IntentClass :
- MARKET_QUERY  -> mql_stream_handler (exécute MQL puis LLM en SSE)
- WORKSPACE_STATUS -> workspace_status_handler
- PROCESS_INFO  -> process_info_handler
- OUT_OF_SCOPE  -> static_refusal_handler
- RECOMMENDATION -> bloqué par guardrail (jamais atteint ici)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from src.agent.circuit_breaker import get_model_with_breaker
from src.agent.context_store import MQLContext
from src.agent.llm_client import stream_mistral
from src.mql.engine import execute_mql_query


async def mql_stream_handler(
    query: str,
    workspace_id: UUID | None,
    user: dict[str, Any],
    db: Any,
    context: MQLContext,
    trace: Any,
    intent_confidence: float = 0.0,
) -> AsyncGenerator[dict[str, Any], None]:
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
    mql_span.end(
        output={
            "template": mql_result.template_used,
            "rows": mql_result.row_count,
            "sources": len(mql_result.sources),
        }
    )

    if not mql_result.sources:
        yield {"type": "sources", "sources": [], "has_official_source": False}
        yield {
            "type": "token",
            "content": (
                "Aucune donnée de marché disponible pour cette requête. "
                "Vérifiez que des campagnes actives existent pour la zone "
                "et l'article demandés."
            ),
        }
        yield {"type": "done", "usage": {}}
        return

    yield {
        "type": "sources",
        "sources": [
            {
                "name": s.name,
                "source_type": s.source_type,
                "publisher": s.publisher,
                "published_date": (
                    s.published_date.isoformat() if s.published_date else None
                ),
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

    await db.execute(
        """
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
    """,
        {
            "tid": user["tenant_id"],
            "ws": workspace_id,
            "uid": user["id"],
            "query": query,
            "conf": intent_confidence,
            "template": mql_result.template_used,
            "src_count": len(mql_result.sources),
            "latency": mql_result.latency_ms,
            "model": model,
            "trace_id": str(trace.id),
        },
    )

    yield {"type": "done", "usage": {"model": model}}


async def workspace_status_handler(
    query: str,
    workspace_id: UUID | None,
    user: dict[str, Any],
    db: Any,
    context: MQLContext,
    trace: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Handler WORKSPACE_STATUS — retourne l'état du workspace."""
    if not workspace_id:
        yield {
            "type": "token",
            "content": "Veuillez sélectionner un workspace pour consulter son état.",
        }
        yield {"type": "done", "usage": {}}
        return

    ws = await db.fetch_one(
        "SELECT * FROM process_workspaces WHERE id = :ws", {"ws": workspace_id}
    )
    if not ws:
        yield {"type": "token", "content": "Workspace introuvable."}
        yield {"type": "done", "usage": {}}
        return

    from src.api.cognitive_helpers import async_load_cognitive_facts
    from src.cognitive.cognitive_state import compute_cognitive_state_result

    facts = await async_load_cognitive_facts(db, ws)
    cog = compute_cognitive_state_result(facts)

    bundles = await db.fetch_all(
        "SELECT supplier_name_raw, supplier_name_resolved, status "
        "FROM supplier_bundles WHERE workspace_id = :ws",
        {"ws": workspace_id},
    )

    members = await db.fetch_all(
        """
        SELECT u.full_name, wm.role
        FROM workspace_memberships wm
        JOIN users u ON u.id = wm.user_id
        WHERE wm.workspace_id = :ws
    """,
        {"ws": workspace_id},
    )

    open_flags = await db.fetch_val(
        "SELECT COUNT(*) FROM assessment_comments "
        "WHERE workspace_id = :ws AND is_flag = true AND resolved = false",
        {"ws": workspace_id},
    )

    model = await get_model_with_breaker()
    llm_span = trace.span(name="llm_workspace_status", input={"model": model})

    ws_context = (
        f"Workspace: {ws['reference_code']} — {ws['title']}\n"
        f"Phase: {cog.label_fr} ({cog.state})\n"
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
    workspace_id: UUID | None,
    user: dict[str, Any],
    db: Any,
    context: MQLContext,
    trace: Any,
) -> AsyncGenerator[dict[str, Any], None]:
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
    query: str,
    workspace_id: UUID | None,
    user: dict[str, Any],
    db: Any,
    context: MQLContext,
    trace: Any,
) -> AsyncGenerator[dict[str, Any], None]:
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


def _build_mql_system_prompt(mql_result: Any) -> str:
    """Construit le system prompt pour le LLM après exécution MQL."""
    data_section = ""
    for row in mql_result.rows[:20]:
        data_section += f"  {row}\n"

    sources_section = ""
    for s in mql_result.sources:
        official = " (officiel)" if s.is_official else ""
        sources_section += (
            f"  - {s.name} [{s.source_type}] par {s.publisher}{official}\n"
        )

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
