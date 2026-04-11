"""Agent Conversationnel — Canon V5.1.0 Section 7.2.

POST /agent/prompt — point d'entrée unique.
- Semantic Router -> 4 handlers SSE
- Guardrail pré-LLM INV-W06 -> 422 si ``AGENT_INV_W06_PRE_LLM_BLOCK=true`` (défaut : off)
- Langfuse tracing (INV-A01) sur chaque prompt
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

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
logger = logging.getLogger(__name__)


class AgentPromptRequest(BaseModel):
    """Corps POST /api/agent/prompt.

    Clé canonique : ``query``. Alias acceptés pour clients mal branchés :
    ``message``, ``prompt`` (même sémantique). ``workspaceId`` / ``sessionId`` en camelCase.
    """

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("query", "message", "prompt"),
        description="Question utilisateur (texte non vide)",
    )
    workspace_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("workspace_id", "workspaceId"),
    )
    session_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("session_id", "sessionId"),
    )


@router.post("/agent/prompt")
@limiter.limit(LIMIT_ANNOTATION)
async def agent_prompt(
    request: Request,
    current_user: UserClaims = Depends(get_current_user),
) -> Any:
    """Point d'entrée unique de l'agent conversationnel.

    Retourne un stream SSE. JSON 422 guardrail uniquement si
    ``AGENT_INV_W06_PRE_LLM_BLOCK`` est activé et qu'une recommandation est détectée.

    Le corps JSON est lu manuellement depuis ``request`` afin de pouvoir logger
    le payload brut *avant* la validation Pydantic — ce qui permet de diagnostiquer
    les 422 « Field required » sans perdre le corps de la requête.
    """
    # --- 1. Log raw request body before Pydantic validation ---
    try:
        raw_body = await request.body()
        raw_text = raw_body.decode("utf-8", errors="replace")
        logger.debug(
            "[agent_prompt] raw request body (%d bytes): %s",
            len(raw_body),
            raw_text,
        )
    except Exception as read_exc:
        logger.warning("[agent_prompt] could not read raw request body: %s", read_exc)
        raw_body = b""
        raw_text = ""

    # --- 2. Parse and validate with Pydantic, logging any validation errors ---
    try:
        body_data = json.loads(raw_body) if raw_body else {}
        payload = AgentPromptRequest.model_validate(body_data)
        logger.debug(
            "[agent_prompt] parsed payload — query=%r workspace_id=%s session_id=%s",
            payload.query,
            payload.workspace_id,
            payload.session_id,
        )
    except json.JSONDecodeError as json_exc:
        logger.error(
            "[agent_prompt] JSON decode error — body=%r error=%s",
            raw_text,
            json_exc,
        )
        raise HTTPException(422, f"Corps JSON invalide : {json_exc}") from json_exc
    except ValidationError as val_exc:
        logger.error(
            "[agent_prompt] Pydantic validation error — body=%r errors=%s",
            raw_text,
            val_exc.errors(),
        )
        raise HTTPException(
            422,
            {
                "detail": val_exc.errors(),
                "body": raw_text,
            },
        ) from val_exc

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
                    {
                        "id": int(current_user.user_id),
                        "role": current_user.role,
                    },
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
