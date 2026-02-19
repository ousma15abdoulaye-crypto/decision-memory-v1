# src/extraction/engine.py
"""
ExtractionEngine — M-EXTRACTION-ENGINE
Constitution V3.3.2 §1 (Couche A) + §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
ADR-0003 §2.2 (ordre exécution).

SLA-A : native_pdf / excel_parser / docx_parser
        → synchrone < 60s
SLA-B : tesseract / azure
        → asynchrone via extraction_jobs
"""

import time

from src.db.connection import get_db_cursor

# ── Constantes ───────────────────────────────────────────────────

SLA_A_METHODS = {"native_pdf", "excel_parser", "docx_parser"}
SLA_B_METHODS = {"tesseract", "azure"}
SLA_A_TIMEOUT_S = 60.0
INSUFFICIENT_TEXT_THRESHOLD = 100

STRUCTURED_DATA_EMPTY: dict = {
    "doc_kind": None,
    "language_detected": None,
    "detected_tables": [],
    "detected_sections": [],
    "candidate_criteria": [],
    "candidate_line_items": [],
    "currency_detected": None,
    "dates_detected": [],
    "supplier_candidates": [],
    "_low_confidence": False,
    "_requires_human_review": False,
    "_extraction_duration_ms": None,
    "_sla_class": None,
}


# ── Détection méthode ────────────────────────────────────────────


def detect_method(mime_type: str, file_content: bytes) -> str:
    """
    Détecte la méthode d'extraction selon magic bytes réels.
    Jamais selon Content-Type déclaré (ADR-0002).
    """
    # PDF natif
    if file_content[:4] == b"%PDF":
        # Heuristique : présence de marqueur texte BT
        if b"BT" in file_content[:4096]:
            return "native_pdf"
        return "tesseract"

    # XLSX (ZIP Office)
    if file_content[:4] == b"PK\x03\x04":
        if b"xl/" in file_content[:512]:
            return "excel_parser"
        if b"word/" in file_content[:512]:
            return "docx_parser"
        return "tesseract"

    # Fallback OCR
    return "tesseract"


# ── Helpers privés ───────────────────────────────────────────────


def _get_document(document_id: str) -> dict:
    """
    Charge un document depuis la DB.
    §9 : raise ValueError si introuvable.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, case_id, mime_type, storage_uri,
                   extraction_status, extraction_method
            FROM documents
            WHERE id = %s
        """,
            (document_id,),
        )
        doc = cur.fetchone()

    if doc is None:
        raise ValueError(
            f"Document '{document_id}' introuvable. "
            f"Vérifier l'id ou lancer POST /api/cases/{{id}}"
            f"/documents d'abord."
        )
    return dict(doc)


def _update_document_status(document_id: str, status: str) -> None:
    """Met à jour extraction_status sur documents."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET extraction_status = %s
            WHERE id = %s
        """,
            (status, document_id),
        )


def _compute_confidence(
    raw_text: str,
    structured: dict,  # noqa: ARG001
) -> float:
    """
    Heuristique de confiance.
    §9 : incertitude mesurée, jamais masquée.
    """
    text = raw_text.strip() if raw_text else ""
    if len(text) < INSUFFICIENT_TEXT_THRESHOLD:
        return 0.3
    if len(text) < 500:
        return 0.6
    return 0.85


def _store_extraction(
    document_id: str,
    raw_text: str,
    structured_data: dict,
    method: str,
    confidence: float,
) -> None:
    """Persiste le résultat d'extraction en DB."""
    import json
    import uuid

    extraction_id = f"ext-{uuid.uuid4().hex[:12]}"
    # Récupérer case_id depuis le document
    doc = _get_document(document_id)
    case_id = doc.get("case_id")

    with get_db_cursor() as cur:
        structured_json = json.dumps(structured_data)
        cur.execute(
            """
            INSERT INTO extractions
                (id, case_id, document_id, raw_text, structured_data,
                 extraction_method, confidence_score, extracted_at,
                 data_json, extraction_type, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, NOW(),
                    %s, %s, NOW()::TEXT)
        """,
            (
                extraction_id,
                case_id,
                document_id,
                raw_text,
                structured_json,
                method,
                confidence,
                structured_json,  # data_json pour compatibilité
                method,  # extraction_type pour compatibilité
            ),
        )


def _store_error(
    document_id: str,
    job_id: str | None,
    error_code: str,
    error_detail: str,
) -> None:
    """
    §9 : enregistre l'erreur explicitement.
    Jamais silencieux.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_errors
                (document_id, job_id, error_code, error_detail)
            VALUES (%s, %s, %s, %s)
        """,
            (document_id, job_id, error_code, error_detail),
        )


# ── Parseurs ─────────────────────────────────────────────────────


def _extract_native_pdf(storage_uri: str) -> tuple[str, dict]:
    """Extraction PDF natif via pdfplumber."""
    import pdfplumber  # type: ignore

    raw_text = ""
    with pdfplumber.open(storage_uri) as pdf:
        for page in pdf.pages:
            raw_text += (page.extract_text() or "") + "\n"

    return raw_text, dict(STRUCTURED_DATA_EMPTY)


def _extract_excel(storage_uri: str) -> tuple[str, dict]:
    """Extraction XLSX via openpyxl."""
    import openpyxl  # type: ignore

    wb = openpyxl.load_workbook(storage_uri, data_only=True)
    raw_text = ""
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            row_text = " ".join(str(c) for c in row if c is not None)
            if row_text.strip():
                raw_text += row_text + "\n"

    return raw_text, dict(STRUCTURED_DATA_EMPTY)


def _extract_docx(storage_uri: str) -> tuple[str, dict]:
    """Extraction DOCX via python-docx."""
    from docx import Document  # type: ignore

    doc = Document(storage_uri)
    raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return raw_text, dict(STRUCTURED_DATA_EMPTY)


def _dispatch_extraction(
    doc: dict,
    method: str,
) -> tuple[str, dict]:
    """Routing vers le parseur selon la méthode."""
    if method == "native_pdf":
        return _extract_native_pdf(doc["storage_uri"])
    if method == "excel_parser":
        return _extract_excel(doc["storage_uri"])
    if method == "docx_parser":
        return _extract_docx(doc["storage_uri"])
    raise ValueError(
        f"Méthode inconnue pour dispatch : '{method}'. " f"SLA-A : {SLA_A_METHODS}"
    )


# ── Fonctions publiques ──────────────────────────────────────────


def extract_sync(document_id: str) -> dict:
    """
    SLA-A : extraction synchrone < 60s.
    Méthodes : native_pdf, excel_parser, docx_parser.
    §9 : échec explicite si timeout ou erreur.
    """
    start_ms = time.monotonic() * 1000

    doc = _get_document(document_id)
    method = doc.get("extraction_method") or "native_pdf"

    if method not in SLA_A_METHODS:
        raise ValueError(
            f"extract_sync appelé avec méthode SLA-B '{method}'. "
            f"Utiliser extract_async pour {SLA_B_METHODS}."
        )

    _update_document_status(document_id, "processing")

    try:
        raw_text, structured_data = _dispatch_extraction(doc, method)
        duration_ms = (time.monotonic() * 1000) - start_ms

        # §9 : SLA-A violation → échec explicite
        if duration_ms > SLA_A_TIMEOUT_S * 1000:
            _store_error(
                document_id,
                None,
                "TIMEOUT_SLA_A",
                f"SLA-A violé : {duration_ms:.0f}ms > 60000ms",
            )
            _update_document_status(document_id, "failed")
            raise TimeoutError(
                f"SLA-A violé : {duration_ms:.0f}ms. " f"Document {document_id}."
            )

        confidence = _compute_confidence(raw_text, structured_data)

        # §9 : incertitude signalée, jamais masquée
        if confidence < 0.6:
            structured_data["_low_confidence"] = True
            structured_data["_requires_human_review"] = True

        structured_data["_extraction_duration_ms"] = duration_ms
        structured_data["_sla_class"] = "A"

        _store_extraction(
            document_id,
            raw_text,
            structured_data,
            method,
            confidence,
        )
        _update_document_status(document_id, "done")

        return {
            "document_id": document_id,
            "status": "done",
            "method": method,
            "sla_class": "A",
            "duration_ms": duration_ms,
            "confidence": confidence,
            "requires_human_review": structured_data["_requires_human_review"],
        }

    except TimeoutError:
        raise
    except Exception as exc:
        # §9 : échec explicite, jamais silencieux
        _update_document_status(document_id, "failed")
        _store_error(
            document_id,
            None,
            "PARSE_ERROR",
            str(exc),
        )
        raise


def extract_async(document_id: str, method: str) -> dict:
    """
    SLA-B : mise en queue OCR asynchrone.
    Retourne immédiatement avec job_id + status pending.
    """
    if method not in SLA_B_METHODS:
        raise ValueError(
            f"extract_async appelé avec méthode SLA-A '{method}'. "
            f"Utiliser extract_sync pour {SLA_A_METHODS}."
        )

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_jobs
                (document_id, method, sla_class, status)
            VALUES (%s, %s, 'B', 'pending')
            RETURNING id
        """,
            (document_id, method),
        )
        job = cur.fetchone()

    return {
        "document_id": document_id,
        "job_id": str(job["id"]),
        "status": "pending",
        "method": method,
        "sla_class": "B",
        "message": (
            "Extraction OCR mise en queue. "
            "Consulter GET /api/extractions/jobs/"
            f"{job['id']}/status"
        ),
    }
