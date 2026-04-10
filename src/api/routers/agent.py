"""Agent Conversationnel — Canon V5.1.0 Section 7.2.

POST /agent/prompt — point d'entrée unique.
- Semantic Router -> 4 handlers SSE
- Guardrail INV-W06 -> 422 si RECOMMENDATION détectée
- Langfuse tracing (INV-A01) sur chaque prompt
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.context_store import get_context, save_context
from src.agent.guardrail import check_recommendation_guardrail
from src.agent.handlers import (
    mql_stream_handler,
    process_info_handler,
    static_refusal_handler,
    workspace_status_handler,
)
from src.agent.langfuse_client import flush_langfuse, get_langfuse
from src.agent.output_filter import filter_token_stream
from src.agent.semantic_router import IntentClass, classify_intent
from src.auth.guard import guard
from src.auth.permissions import ROLE_PERMISSIONS
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db.async_pool import AsyncpgAdapter, acquire_with_rls
from src.ratelimit import LIMIT_ANNOTATION, limiter

router = APIRouter(prefix="/api", tags=["agent-v51"])


class AgentPromptRequest(BaseModel):
    query: str
    workspace_id: UUID | None = None
    session_id: str | None = None


@router.post("/agent/prompt")
@limiter.limit(LIMIT_ANNOTATION)
async def agent_prompt(
    request: Request,
    payload: AgentPromptRequest,
    current_user: UserClaims = Depends(get_current_user),
) -> Any:
    """Point d'entrée unique de l'agent conversationnel.

    Retourne un stream SSE pour toutes les réponses sauf guardrail (JSON 422).
    """
    langfuse = get_langfuse()
    trace = langfuse.trace(
        name="agent_prompt",
        user_id=str(current_user.user_id),
        metadata={
            "workspace_id": (
                str(payload.workspace_id) if payload.workspace_id else None
            ),
            "query_length": len(payload.query),
        },
    )

    try:
        guardrail_result = await check_recommendation_guardrail(payload.query, trace)
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

        if not current_user.tenant_id:
            raise HTTPException(400, "tenant_id manquant dans le JWT.")

        async with acquire_with_rls(
            str(current_user.tenant_id),
            is_admin=(current_user.role == "admin"),
        ) as raw_conn:
            conn = AsyncpgAdapter(raw_conn)
            if payload.workspace_id:
                # guard() attend AsyncpgAdapter (pas la connexion brute)
                # et un dict {"id": int} (pas UserClaims).
                await guard(
                    conn,
                    {"id": int(current_user.user_id)},
                    payload.workspace_id,
                    "agent.query",
                )
            else:
                role_perms = ROLE_PERMISSIONS.get(current_user.role or "", frozenset())
                if "agent.query" not in role_perms and "system.admin" not in role_perms:
                    raise HTTPException(403, "Permission agent.query requise.")

            intent_span = trace.span(name="intent_classification")
            intent = await classify_intent(payload.query)
            intent_span.end(
                output={
                    "intent": intent.intent_class.value,
                    "confidence": intent.confidence,
                }
            )

            session_key = (
                f"{payload.workspace_id or 'global'}"
                f":{payload.session_id or current_user.user_id}"
            )
            context = await get_context(session_key)

            user_dict: dict[str, Any] = {
                "id": current_user.user_id,
                "tenant_id": current_user.tenant_id,
                "role": current_user.role,
            }

            if intent.intent_class == IntentClass.MARKET_QUERY:
                handler = mql_stream_handler
            elif intent.intent_class == IntentClass.WORKSPACE_STATUS:
                handler = workspace_status_handler
            elif intent.intent_class == IntentClass.PROCESS_INFO:
                handler = process_info_handler
            else:
                handler = static_refusal_handler

            async def event_generator():  # type: ignore[return]
                assistant_content = ""
                try:
                    handler_kwargs: dict[str, Any] = {
                        "query": payload.query,
                        "workspace_id": payload.workspace_id,
                        "user": user_dict,
                        "db": conn,
                        "context": context,
                        "trace": trace,
                    }
                    if intent.intent_class == IntentClass.MARKET_QUERY:
                        handler_kwargs["intent_confidence"] = intent.confidence
                    raw_stream = handler(**handler_kwargs)
                    async for event in filter_token_stream(raw_stream, trace):
                        if event.get("type") == "token" and event.get("content"):
                            assistant_content += event["content"]
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
                    if assistant_content:
                        context.add_assistant_message(assistant_content)
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
