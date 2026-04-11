"""
Offer and DAO extraction pipeline — orchestrates text extraction, ML, and persistence.
"""

import asyncio
import concurrent.futures
import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.couche_a.extraction_models import (
    TDRExtractionResult,
    Tier,
    make_fallback_result,
)
from src.db import db_execute, get_connection

from .backend_client import _get_router, call_annotation_backend
from .criterion import (
    _OFFER_TYPE_TO_ROLE,
    extract_dao_criteria_structured,
    extract_dao_criteria_typed,
)
from .persistence import persist_tdr_result_to_db
from .text_extraction import ExtractionInsufficientTextError, extract_text_any

logger = logging.getLogger(__name__)


def extract_dao_content(case_id: str, artifact_id: str, filepath: str):
    """Extraction DAO avec typage des critères (M3A)."""
    try:
        try:
            text_content = extract_text_any(filepath)
        except ExtractionInsufficientTextError as exc:
            logger.error(
                "[EXTRACTION] DAO texte insuffisant — case=%s artifact=%s — %s",
                case_id,
                artifact_id,
                exc,
            )
            return

        raw_criteria = extract_dao_criteria_structured(text_content)
        raw_dicts = [asdict(c) for c in raw_criteria]
        typed_criteria = extract_dao_criteria_typed(case_id, raw_dicts)

        with get_connection() as conn:
            for crit in typed_criteria:
                db_execute(
                    conn,
                    """
                    INSERT INTO dao_criteria
                    (id, case_id, categorie, critere_nom, description,
                     criterion_category, is_eliminatory, ponderation,
                     type_reponse, seuil_elimination, ordre_affichage, created_at)
                    VALUES (:id, :cid, :cat, :nom, :desc,
                            :criterion_category, :is_eliminatory, :ponderation,
                            :type_reponse, :seuil, :ordre, :ts)
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "cid": case_id,
                        "cat": crit["categorie"],
                        "nom": crit["critere_nom"],
                        "desc": crit["description"],
                        "criterion_category": crit["criterion_category"],
                        "is_eliminatory": crit["is_eliminatory"],
                        "ponderation": crit["ponderation"],
                        "type_reponse": crit["type_reponse"],
                        "seuil": crit["seuil_elimination"],
                        "ordre": crit["ordre_affichage"],
                        "ts": datetime.now(UTC).isoformat(),
                    },
                )

        logger.info(
            f"[EXTRACTION] Case {case_id} – {len(typed_criteria)} critères typés et validés"
        )

    except Exception as e:
        logger.error(
            f"[EXTRACTION] Échec pour case {case_id}, artifact {artifact_id}: {e}"
        )
        raise


def extract_offer_content(
    case_id: str,
    artifact_id: str,
    filepath: str,
    offer_type: str,
) -> TDRExtractionResult:
    """
    Point d'entrée pipeline — appelé par routers.py via
    background_tasks.add_task() ou par _extract_and_persist_offer.

    Retourne toujours un ``TDRExtractionResult`` (succès ou fallback traçable).
    """
    logger.info(
        "[EXTRACT] Début — case=%s artifact=%s type=%s",
        case_id,
        artifact_id,
        offer_type,
    )

    try:
        text = extract_text_any(filepath)
        logger.info("[EXTRACT] Texte extrait : %d chars", len(text))
    except ExtractionInsufficientTextError as exc:
        logger.error(
            "[EXTRACT] Texte insuffisant ou illisible — case=%s artifact=%s — %s",
            case_id,
            artifact_id,
            exc,
        )
        return make_fallback_result(
            document_id=artifact_id,
            document_role=str(offer_type),
            error_reason="insufficient_extracted_text",
        )
    except Exception as exc:
        logger.error("[EXTRACT] Lecture fichier KO : %s", exc)
        return make_fallback_result(
            document_id=artifact_id,
            document_role=str(offer_type),
            error_reason=f"file_read_{type(exc).__name__}",
        )

    if not text or not text.strip():
        suffix = filepath.lower() if filepath else ""
        if suffix.endswith(".pdf"):
            probable_cause = "PDF_SCAN_SANS_OCR_ou_PDF_VIDE"
        elif suffix.endswith(".docx"):
            probable_cause = "DOCX_VIDE_ou_ERREUR_LECTURE"
        elif suffix.endswith(".doc"):
            probable_cause = "DOC_LEGACY_NON_SUPPORT_ou_VIDE"
        else:
            probable_cause = "FICHIER_ILLISIBLE_ou_FORMAT_INCONNU"
        logger.warning(
            "[EXTRACT] text_len=0 — document_id=%s — cause_probable=%s "
            "— filepath=%s — pipeline continue avec empty_result",
            artifact_id,
            probable_cause,
            Path(filepath).name if filepath else "unknown",
        )
        return make_fallback_result(
            document_id=artifact_id,
            document_role=str(offer_type),
            error_reason="empty_text_after_extraction",
        )

    document_role = _OFFER_TYPE_TO_ROLE.get(str(offer_type).lower(), "supporting_doc")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                extract_offer_content_async(
                    document_id=artifact_id,
                    text=text,
                    document_role=document_role,
                ),
            )
            result = future.result(timeout=_get_router().timeout + 15)
        logger.info(
            "[EXTRACT] Terminé — case=%s ok=%s latency=%.0fms",
            case_id,
            result.extraction_ok,
            result.latency_ms,
        )
        return result

    except concurrent.futures.TimeoutError:
        logger.error("[EXTRACT] Timeout dispatch — case=%s", case_id)
        return make_fallback_result(
            document_id=artifact_id,
            document_role=document_role,
            error_reason="dispatch_timeout",
        )
    except Exception as exc:
        logger.error(
            "[EXTRACT] Dispatch KO — %s — case=%s",
            type(exc).__name__,
            case_id,
            exc_info=True,
        )
        return make_fallback_result(
            document_id=artifact_id,
            document_role=document_role,
            error_reason=f"dispatch_{type(exc).__name__}",
        )


def _annotation_failure_is_retriable(result: TDRExtractionResult) -> bool:
    """True si l'échec vient du réseau / timeout / 5xx — candidat à un retry HTTP."""
    if result.extraction_ok:
        return False
    er = (result.error_reason or "").strip()
    if er == "backend_timeout":
        return True
    if er.startswith("connection_"):
        return True
    if er.startswith("http_") and er in (
        "http_502",
        "http_503",
        "http_504",
        "http_429",
    ):
        return True
    return False


async def extract_offer_content_async(
    document_id: str,
    text: str,
    document_role: str = "financial_offer",
) -> TDRExtractionResult:
    """Extraction documentaire réelle — async. Fallback traçable si backend KO."""
    tier = _get_router().select_tier()

    if tier == Tier.T4_OFFLINE:
        logger.warning("[EXTRACT] TIER 4 offline — doc=%s", document_id)
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason="tier4_offline_no_api_key",
            tier=Tier.T4_OFFLINE,
        )

    delay_sec = 1.0
    last: TDRExtractionResult | None = None
    for attempt in range(3):
        last = await call_annotation_backend(
            document_id=document_id,
            text=text,
            document_role=document_role,
        )
        if last.extraction_ok or not _annotation_failure_is_retriable(last):
            return last
        if attempt < 2:
            await asyncio.sleep(delay_sec)
            delay_sec *= 2.0

    return make_fallback_result(
        document_id=document_id,
        document_role=document_role,
        error_reason="annotation_backend_max_retries_exceeded",
        tier=tier,
    )


def extract_and_persist_offer(
    case_id: str,
    artifact_id: str,
    file_path: str,
    offer_type: str,
) -> None:
    """
    Wrapper canonique : extraction + persistance DB (M-FIX-PERSISTENCE-BRIDGE).
    À utiliser depuis ``background_tasks`` à la place de ``extract_offer_content`` seul.
    """
    try:
        result = extract_offer_content(case_id, artifact_id, file_path, offer_type)
        persist_tdr_result_to_db(result, case_id, artifact_id)
    except Exception as exc:
        logger.error(
            "[BRIDGE] Échec persistance — artifact=%s — %s",
            artifact_id,
            exc,
            exc_info=True,
        )
