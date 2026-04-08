"""Service commentaires CDE — O8 (Canon V5.1.0).

`add_smart_comment` : point d'entrée unique pour le dialog
"clic cellule → commenter ou signaler" (INV-S04).

Règles :
- Crée ou réutilise le thread de délibération associé à la cellule.
- Infère le `comment_type` : '?' → question, is_flag → flag, sinon comment.
- Stocke dans `deliberation_messages` ET `assessment_comments`.
- Si is_flag → insère dans `assessment_history` (raison = "flag_raised").
- content et is_flag sont immutables après insertion (trigger DB INV-S04).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.db import db_execute_one, db_fetchall

logger = logging.getLogger(__name__)

# ── Types internes ────────────────────────────────────────────────

_COMMENT_TYPES = frozenset({"comment", "flag", "question"})


def _infer_comment_type(content: str, *, is_flag: bool) -> str:
    """Infère le type depuis le contenu textuel et is_flag.

    Règle :
    - is_flag → 'flag'
    - contenu se terminant par '?' → 'question'
    - sinon → 'comment'
    """
    if is_flag:
        return "flag"
    stripped = content.strip()
    if stripped.endswith("?") or re.search(r"\?[\s]*$", stripped):
        return "question"
    return "comment"


# ── Lecture ──────────────────────────────────────────────────────


def get_comment(conn: Any, workspace_id: str, comment_id: str) -> dict[str, Any] | None:
    return db_execute_one(
        conn,
        """
        SELECT id::text AS id,
               workspace_id::text AS workspace_id,
               tenant_id::text AS tenant_id,
               criterion_assessment_id::text AS criterion_assessment_id,
               author_user_id,
               content,
               comment_type,
               is_flag,
               resolved,
               resolved_by,
               resolved_at,
               created_at
        FROM assessment_comments
        WHERE id = CAST(:cid AS uuid)
          AND workspace_id = CAST(:wid AS uuid)
        """,
        {"cid": comment_id, "wid": workspace_id},
    )


def list_comments(
    conn: Any,
    workspace_id: str,
    *,
    criterion_assessment_id: str | None = None,
    unresolved_flags_only: bool = False,
) -> list[dict[str, Any]]:
    """Liste les commentaires d'un workspace ou d'une cellule."""
    conditions = ["workspace_id = CAST(:wid AS uuid)"]
    params: dict[str, Any] = {"wid": workspace_id}

    if criterion_assessment_id:
        conditions.append("criterion_assessment_id = CAST(:caid AS uuid)")
        params["caid"] = criterion_assessment_id

    if unresolved_flags_only:
        conditions.append("is_flag = TRUE AND resolved = FALSE")

    where = " AND ".join(conditions)
    return db_fetchall(
        conn,
        f"""
        SELECT id::text AS id,
               workspace_id::text AS workspace_id,
               criterion_assessment_id::text AS criterion_assessment_id,
               author_user_id,
               content,
               comment_type,
               is_flag,
               resolved,
               created_at
        FROM assessment_comments
        WHERE {where}
        ORDER BY created_at
        """,
        params,
    )


def resolve_comment(
    conn: Any,
    workspace_id: str,
    comment_id: str,
    *,
    resolved_by: int,
) -> None:
    """Résout un commentaire/flag. content et is_flag ne changent pas (INV-S04)."""
    db_execute_one(
        conn,
        """
        UPDATE assessment_comments
        SET resolved = TRUE,
            resolved_by = :uid,
            resolved_at = NOW()
        WHERE id = CAST(:cid AS uuid)
          AND workspace_id = CAST(:wid AS uuid)
        """,
        {"cid": comment_id, "wid": workspace_id, "uid": resolved_by},
    )


# ── Écriture — point d'entrée principal ──────────────────────────


def add_smart_comment(
    conn: Any,
    *,
    workspace_id: str,
    tenant_id: str,
    author_user_id: int,
    content: str,
    is_flag: bool = False,
    criterion_assessment_id: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """CDE — clic cellule → commenter ou signaler (Canon O8).

    1. Trouve ou crée le thread de délibération associé à la cellule.
    2. Infère le `comment_type` depuis `content` et `is_flag`.
    3. Insère dans `deliberation_messages`.
    4. Insère dans `assessment_comments` (content + is_flag immutables — INV-S04).
    5. Si is_flag → insère dans `assessment_history` (raison = "flag_raised").

    Retourne un dict avec `comment_id`, `message_id`, `thread_id`, `comment_type`.
    """
    if not content or not content.strip():
        raise ValueError("content ne peut pas être vide.")

    comment_type = _infer_comment_type(content, is_flag=is_flag)

    # 1. Trouver ou créer le thread
    resolved_thread_id = _resolve_or_create_thread(
        conn,
        workspace_id=workspace_id,
        tenant_id=tenant_id,
        criterion_assessment_id=criterion_assessment_id,
        thread_id=thread_id,
    )

    # 2. Insérer dans deliberation_messages (append-only — INV-S03)
    msg_row = db_execute_one(
        conn,
        """
        INSERT INTO deliberation_messages (
            thread_id, workspace_id, tenant_id, author_user_id, body
        )
        VALUES (
            CAST(:tid AS uuid),
            CAST(:wid AS uuid),
            CAST(:tenant AS uuid),
            :uid,
            :body
        )
        RETURNING id::text AS id
        """,
        {
            "tid": resolved_thread_id,
            "wid": workspace_id,
            "tenant": tenant_id,
            "uid": author_user_id,
            "body": content,
        },
    )
    if not msg_row or not msg_row.get("id"):
        raise RuntimeError("insert deliberation_messages failed")
    message_id = str(msg_row["id"])

    # 3. Insérer dans assessment_comments (INV-S04 : content + is_flag immutables)
    cmt_params: dict[str, Any] = {
        "wid": workspace_id,
        "tenant": tenant_id,
        "uid": author_user_id,
        "content": content,
        "ctype": comment_type,
        "is_flag": is_flag,
    }
    if criterion_assessment_id:
        cmt_row = db_execute_one(
            conn,
            """
            INSERT INTO assessment_comments (
                workspace_id, tenant_id, criterion_assessment_id,
                author_user_id, content, comment_type, is_flag
            )
            VALUES (
                CAST(:wid AS uuid), CAST(:tenant AS uuid),
                CAST(:caid AS uuid),
                :uid, :content, :ctype, :is_flag
            )
            RETURNING id::text AS id
            """,
            {**cmt_params, "caid": criterion_assessment_id},
        )
    else:
        cmt_row = db_execute_one(
            conn,
            """
            INSERT INTO assessment_comments (
                workspace_id, tenant_id,
                author_user_id, content, comment_type, is_flag
            )
            VALUES (
                CAST(:wid AS uuid), CAST(:tenant AS uuid),
                :uid, :content, :ctype, :is_flag
            )
            RETURNING id::text AS id
            """,
            cmt_params,
        )
    if not cmt_row or not cmt_row.get("id"):
        raise RuntimeError("insert assessment_comments failed")
    comment_id = str(cmt_row["id"])

    # 4. Si flag → insère dans assessment_history
    if is_flag and criterion_assessment_id:
        _record_flag_in_history(
            conn,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            criterion_assessment_id=criterion_assessment_id,
            author_user_id=author_user_id,
            comment_id=comment_id,
        )

    return {
        "comment_id": comment_id,
        "message_id": message_id,
        "thread_id": resolved_thread_id,
        "comment_type": comment_type,
        "is_flag": is_flag,
    }


# ── Helpers privés ───────────────────────────────────────────────


def _resolve_or_create_thread(
    conn: Any,
    *,
    workspace_id: str,
    tenant_id: str,
    criterion_assessment_id: str | None,
    thread_id: str | None,
) -> str:
    """Retourne l'ID de thread existant ou en crée un nouveau."""
    if thread_id:
        return thread_id

    if criterion_assessment_id:
        existing = db_execute_one(
            conn,
            """
            SELECT id::text AS id
            FROM deliberation_threads
            WHERE workspace_id = CAST(:wid AS uuid)
              AND title = :title
            ORDER BY created_at
            LIMIT 1
            """,
            {
                "wid": workspace_id,
                "title": f"assessment:{criterion_assessment_id}",
            },
        )
        if existing and existing.get("id"):
            return str(existing["id"])

    title = (
        f"assessment:{criterion_assessment_id}"
        if criterion_assessment_id
        else f"workspace:{workspace_id}"
    )
    new_thread = db_execute_one(
        conn,
        """
        INSERT INTO deliberation_threads (workspace_id, tenant_id, title)
        VALUES (CAST(:wid AS uuid), CAST(:tenant AS uuid), :title)
        RETURNING id::text AS id
        """,
        {"wid": workspace_id, "tenant": tenant_id, "title": title},
    )
    if not new_thread or not new_thread.get("id"):
        raise RuntimeError("insert deliberation_threads failed")
    return str(new_thread["id"])


def _record_flag_in_history(
    conn: Any,
    *,
    workspace_id: str,
    tenant_id: str,
    criterion_assessment_id: str,
    author_user_id: int,
    comment_id: str,
) -> None:
    """Insère dans assessment_history quand un flag est levé."""
    try:
        db_execute_one(
            conn,
            """
            INSERT INTO assessment_history (
                criterion_assessment_id, workspace_id, tenant_id,
                changed_by, change_reason, change_metadata
            )
            VALUES (
                CAST(:caid AS uuid),
                CAST(:wid AS uuid),
                CAST(:tenant AS uuid),
                :uid,
                'flag_raised',
                :meta::jsonb
            )
            """,
            {
                "caid": criterion_assessment_id,
                "wid": workspace_id,
                "tenant": tenant_id,
                "uid": author_user_id,
                "meta": f'{{"comment_id": "{comment_id}"}}',
            },
        )
    except Exception as exc:
        logger.warning(
            "[comments_service] Échec insert assessment_history (non bloquant) : %s",
            exc,
        )
