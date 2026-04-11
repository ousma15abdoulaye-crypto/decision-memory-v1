"""M12 correction log — append + audit (M-CTO-V53-G).

POST append-only vers ``m12_correction_log`` ; GET liste récente (audit).
Permissions : ``audit.read``, ``mql.internal`` ou ``system.admin`` (matrice V5.2).
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.auth.permissions import ROLE_PERMISSIONS
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db import get_connection
from src.procurement.m12_correction_writer import (
    M12_CORRECTION_TYPES,
    M12CorrectionEntry,
    M12CorrectionWriter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/m12", tags=["m12-corrections-v53"])


def _require_audit_access(user: UserClaims) -> None:
    role_perms = ROLE_PERMISSIONS.get(user.role or "", frozenset())
    if (
        "audit.read" not in role_perms
        and "mql.internal" not in role_perms
        and "system.admin" not in role_perms
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Permission audit.read, mql.internal ou system.admin requise.",
        )


class M12CorrectionCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., min_length=1)
    run_id: UUID
    correction_type: Literal[
        "framework",
        "family",
        "document_kind",
        "subtype",
        "validity",
        "conformity",
        "process_link",
        "other",
    ]
    field_corrected: str = Field(..., min_length=1)
    original_value: dict = Field(default_factory=dict)
    corrected_value: dict = Field(default_factory=dict)
    corrected_by: str = Field(..., min_length=1)
    correction_note: str | None = None


@router.post("/corrections", status_code=http_status.HTTP_201_CREATED)
def append_m12_correction(
    payload: M12CorrectionCreateBody,
    user: Annotated[UserClaims, Depends(get_current_user)],
):
    _require_audit_access(user)

    # Sécurité tenant : vérifier que document_id appartient au tenant utilisateur (RLS appliqué)
    with get_connection() as conn:
        conn.execute(
            "SELECT id FROM documents WHERE id = :doc_id",
            {"doc_id": payload.document_id},
        )
        doc_row = conn.fetchone()
        if doc_row is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Document {payload.document_id} introuvable ou hors périmètre tenant.",
            )

        # Document accessible : créer la correction
        entry = M12CorrectionEntry(
            document_id=payload.document_id,
            run_id=payload.run_id,
            correction_type=payload.correction_type,
            field_corrected=payload.field_corrected,
            original_value=payload.original_value,
            corrected_value=payload.corrected_value,
            corrected_by=payload.corrected_by,
            correction_note=payload.correction_note,
        )
        writer = M12CorrectionWriter()
        new_id = writer.write(conn, entry)

    logger.info(
        "m12_correction appended id=%s document_id=%s user=%s",
        new_id,
        payload.document_id,
        user.user_id,
    )
    return {"id": new_id, "document_id": payload.document_id}


@router.get("/corrections/recent")
def list_recent_m12_corrections(
    user: Annotated[UserClaims, Depends(get_current_user)],
    limit: int = 50,
):
    _require_audit_access(user)
    lim = max(1, min(limit, 500))
    logger.warning(
        "Blocked non-tenant-scoped access to recent m12 corrections user=%s limit=%s",
        user.user_id,
        lim,
    )
    raise HTTPException(
        status_code=http_status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "La consultation des corrections récentes n'est pas disponible tant qu'un "
            "filtrage tenant-safe n'est pas implémenté."
        ),
    )
