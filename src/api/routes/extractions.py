# src/api/routes/extractions.py
"""
Endpoints M-EXTRACTION-ENGINE + M-EXTRACTION-CORRECTIONS.
Constitution V3.3.2 §1 (Couche A) + §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes). ADR-0007 (corrections append-only).
"""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth import get_current_user
from src.db.connection import get_db_cursor
from src.extraction.engine import (
    SLA_A_METHODS,
    SLA_B_METHODS,
    extract_async,
    extract_sync,
    get_document,
)

router = APIRouter(
    prefix="/api/extractions",
    tags=["extractions"],
)


# ── Schemas Pydantic ─────────────────────────────────────────────


class ExtractionResponse(BaseModel):
    document_id: str
    status: str
    method: str
    sla_class: str
    job_id: str | None = None
    duration_ms: float | None = None
    confidence: float | None = None
    requires_human_review: bool | None = None
    message: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    method: str
    sla_class: str
    queued_at: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class ExtractionResultResponse(BaseModel):
    document_id: str
    raw_text: str | None = None
    structured_data: dict | None = None
    extraction_method: str | None = None
    confidence_score: float | None = None
    extracted_at: str | None = None
    warning: str | None = None


class EffectiveDataResponse(BaseModel):
    document_id: str
    extraction_id: str
    structured_data: dict
    confidence_score: float | None
    content_hash: str


class CorrectionCreate(BaseModel):
    structured_data: dict
    confidence_override: float | None = None
    correction_reason: str | None = None
    expected_content_hash: str | None = None


class CorrectionResponse(BaseModel):
    id: str
    extraction_id: str
    document_id: str
    corrected_by: str
    corrected_at: str


def _content_hash(data: dict) -> str:
    """SHA256 sur JSON sérialisé (ADR-0007)."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ── Endpoints ────────────────────────────────────────────────────


@router.post(
    "/documents/{document_id}/extract",
    response_model=ExtractionResponse,
    status_code=202,
    summary="Lancer l'extraction d'un document",
    description=(
        "SLA-A (natif) → synchrone, résultat immédiat. "
        "SLA-B (OCR) → asynchrone, job_id retourné. "
        "§9 : erreur explicite si document inconnu ou déjà extrait."
    ),
)
def trigger_extraction(document_id: str) -> ExtractionResponse:
    """
    Lance l'extraction d'un document.
    Détecte automatiquement SLA-A ou SLA-B selon la méthode.
    """
    # §9 : document inconnu → 404 explicite
    try:
        doc = get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # §9 : déjà extrait → 409 explicite
    if doc.get("extraction_status") == "done":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Document '{document_id}' déjà extrait. "
                f"Consulter GET /api/extractions/documents/"
                f"{document_id}"
            ),
        )

    method = doc.get("extraction_method") or "native_pdf"

    # SLA-A : synchrone
    if method in SLA_A_METHODS:
        try:
            result = extract_sync(document_id)
            return ExtractionResponse(**result)
        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=str(exc),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Extraction échouée : {exc}",
            )

    # SLA-B : asynchrone
    if method in SLA_B_METHODS:
        result = extract_async(document_id, method)
        return ExtractionResponse(**result)

    # Méthode inconnue → §9 explicite
    raise HTTPException(
        status_code=422,
        detail=(
            f"Méthode d'extraction inconnue : '{method}'. "
            f"SLA-A : {SLA_A_METHODS}. "
            f"SLA-B : {SLA_B_METHODS}."
        ),
    )


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Statut d'un job d'extraction OCR (SLA-B)",
)
def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Retourne le statut courant d'un job d'extraction asynchrone.
    §9 : 404 explicite si job inconnu.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                document_id,
                status,
                method,
                sla_class,
                queued_at,
                started_at,
                completed_at,
                duration_ms,
                error_message
            FROM extraction_jobs
            WHERE id = %s
        """,
            (job_id,),
        )
        job = cur.fetchone()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' introuvable.",
        )

    return JobStatusResponse(
        job_id=str(job["id"]),
        document_id=str(job["document_id"]),
        status=job["status"],
        method=job["method"],
        sla_class=job["sla_class"],
        queued_at=str(job["queued_at"]),
        started_at=(str(job["started_at"]) if job["started_at"] else None),
        completed_at=(str(job["completed_at"]) if job["completed_at"] else None),
        duration_ms=job["duration_ms"],
        error_message=job["error_message"],
    )


@router.get(
    "/documents/{document_id}",
    response_model=ExtractionResultResponse,
    summary="Résultat d'extraction d'un document",
)
def get_extraction_result(
    document_id: str,
) -> ExtractionResultResponse:
    """
    Retourne le résultat d'extraction le plus récent.
    §9 : 404 si aucune extraction.
         _warning si confidence faible (< 0.6).
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                document_id,
                raw_text,
                structured_data,
                extraction_method,
                confidence_score,
                extracted_at
            FROM extractions
            WHERE document_id = %s
            ORDER BY extracted_at DESC
            LIMIT 1
        """,
            (document_id,),
        )
        extraction = cur.fetchone()

    if extraction is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucune extraction pour le document "
                f"'{document_id}'. "
                f"Lancer POST /api/extractions/documents/"
                f"{document_id}/extract d'abord."
            ),
        )

    result = dict(extraction)

    # structured_data : désérialiser si string JSON
    if isinstance(result.get("structured_data"), str):
        result["structured_data"] = json.loads(result["structured_data"])

    # §9 : signaler explicitement la confiance faible
    warning = None
    if result.get("confidence_score") is not None and result["confidence_score"] < 0.6:
        warning = (
            "Confiance faible — revue humaine requise. "
            f"Score : {result['confidence_score']:.2f}"
        )

    return ExtractionResultResponse(
        document_id=str(result["document_id"]),
        raw_text=result.get("raw_text"),
        structured_data=result.get("structured_data"),
        extraction_method=result.get("extraction_method"),
        confidence_score=result.get("confidence_score"),
        extracted_at=(
            str(result["extracted_at"]) if result.get("extracted_at") else None
        ),
        warning=warning,
    )


# ── M-EXTRACTION-CORRECTIONS (ADR-0007) ────────────────────────────


@router.get(
    "/documents/{document_id}/effective",
    response_model=EffectiveDataResponse,
    summary="Données effectives (extraction + corrections)",
)
def get_effective_data(document_id: str) -> EffectiveDataResponse:
    """
    Retourne structured_data_effective + content_hash.
    Vue : structured_data_effective (dernière correction ou original).
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                extraction_id,
                document_id,
                structured_data,
                confidence_score
            FROM structured_data_effective
            WHERE document_id = %s
            LIMIT 1
        """,
            (document_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune extraction pour le document '{document_id}'.",
        )

    structured_data = row["structured_data"]
    if isinstance(structured_data, str):
        structured_data = json.loads(structured_data)
    elif structured_data is None:
        structured_data = {}

    content_hash = _content_hash(structured_data)

    return EffectiveDataResponse(
        document_id=str(row["document_id"]),
        extraction_id=str(row["extraction_id"]),
        structured_data=structured_data,
        confidence_score=row["confidence_score"],
        content_hash=content_hash,
    )


@router.post(
    "/documents/{document_id}/corrections",
    response_model=CorrectionResponse,
    status_code=201,
    summary="Créer une correction humaine",
)
async def post_correction(
    document_id: str,
    body: CorrectionCreate,
    current_user: dict = Depends(get_current_user),
) -> CorrectionResponse:
    """
    Enregistre une correction append-only.
    Si expected_content_hash fourni et ≠ hash effectif courant → 409 Conflict.
    """
    corrected_by = str(current_user.get("id", current_user.get("username", "unknown")))

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT extraction_id, structured_data
            FROM structured_data_effective
            WHERE document_id = %s
            LIMIT 1
        """,
            (document_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune extraction pour le document '{document_id}'.",
        )

    extraction_id = str(row["extraction_id"])
    current_structured = row["structured_data"]
    if isinstance(current_structured, str):
        current_structured = json.loads(current_structured)
    current_hash = _content_hash(current_structured or {})

    if body.expected_content_hash and body.expected_content_hash != current_hash:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Conflit : état effectif modifié. "
                f"expected_hash={body.expected_content_hash[:16]}... "
                f"current_hash={current_hash[:16]}..."
            ),
        )

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_corrections
                (extraction_id, document_id, structured_data,
                 confidence_override, correction_reason, corrected_by)
            VALUES (%s, %s, %s::jsonb, %s, %s, %s)
            RETURNING id, extraction_id, document_id, corrected_by, corrected_at
        """,
            (
                extraction_id,
                document_id,
                json.dumps(body.structured_data),
                body.confidence_override,
                body.correction_reason,
                corrected_by,
            ),
        )
        r = cur.fetchone()

    return CorrectionResponse(
        id=str(r["id"]),
        extraction_id=str(r["extraction_id"]),
        document_id=str(r["document_id"]),
        corrected_by=str(r["corrected_by"]),
        corrected_at=str(r["corrected_at"]),
    )


@router.get(
    "/documents/{document_id}/corrections/history",
    summary="Historique des corrections",
)
def get_corrections_history(document_id: str) -> list[dict]:
    """Historique des corrections pour le document (extraction_corrections_history)."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, extraction_id, document_id,
                   structured_data, confidence_override, correction_reason,
                   corrected_by, corrected_at
            FROM extraction_corrections
            WHERE document_id = %s
            ORDER BY corrected_at DESC
        """,
            (document_id,),
        )
        rows = cur.fetchall()

    result = []
    for r in rows:
        sd = r.get("structured_data")
        if isinstance(sd, str):
            try:
                sd = json.loads(sd)
            except json.JSONDecodeError:
                sd = {}
        result.append(
            {
                "id": str(r["id"]),
                "extraction_id": str(r["extraction_id"]),
                "document_id": str(r["document_id"]),
                "structured_data": sd,
                "confidence_override": r.get("confidence_override"),
                "correction_reason": r.get("correction_reason"),
                "corrected_by": str(r["corrected_by"]),
                "corrected_at": str(r["corrected_at"]),
            }
        )
    return result
