# src/api/routes/extractions.py
"""
Endpoints M-EXTRACTION-ENGINE.
Constitution V3.3.2 §1 (Couche A) + §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.connection import get_db_cursor
from src.extraction.engine import (
    SLA_A_METHODS,
    SLA_B_METHODS,
    _get_document,
    extract_async,
    extract_sync,
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
    job_id: Optional[str] = None
    duration_ms: Optional[float] = None
    confidence: Optional[float] = None
    requires_human_review: Optional[bool] = None
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    method: str
    sla_class: str
    queued_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class ExtractionResultResponse(BaseModel):
    document_id: str
    raw_text: Optional[str] = None
    structured_data: Optional[dict] = None
    extraction_method: Optional[str] = None
    confidence_score: Optional[float] = None
    extracted_at: Optional[str] = None
    warning: Optional[str] = None


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
        doc = _get_document(document_id)
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
        cur.execute("""
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
        """, (job_id,))
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
        started_at=(
            str(job["started_at"]) if job["started_at"] else None
        ),
        completed_at=(
            str(job["completed_at"])
            if job["completed_at"] else None
        ),
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
        cur.execute("""
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
        """, (document_id,))
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
        result["structured_data"] = json.loads(
            result["structured_data"]
        )

    # §9 : signaler explicitement la confiance faible
    warning = None
    if (
        result.get("confidence_score") is not None
        and result["confidence_score"] < 0.6
    ):
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
            str(result["extracted_at"])
            if result.get("extracted_at") else None
        ),
        warning=warning,
    )
