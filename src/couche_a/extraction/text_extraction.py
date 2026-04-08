"""
Text extraction from files (PDF, DOCX, plain text).

M-ANNOTATION-CONTAINMENT-01 : minimum character threshold for ML pipelines.
"""

import logging
import os
from pathlib import Path

from src.core.api_keys import APIKeyMissingError

logger = logging.getLogger(__name__)

MIN_EXTRACTED_TEXT_CHARS_FOR_ML = 100


class ExtractionInsufficientTextError(ValueError):
    """Texte extrait trop court ou vide pour tout flux annotation / ML (containment)."""


def extract_text_any(filepath: str) -> str:
    """
    Extraction texte — PDF natif uniquement en beta.
    OCR (Mistral / Tesseract) = M10A — hors scope ici.

    M-ANNOTATION-CONTAINMENT-01 : journalisation de chaque voie ; si le texte final
    reste sous ``MIN_EXTRACTED_TEXT_CHARS_FOR_ML``, lève ``ExtractionInsufficientTextError``
    (jamais de chaîne courte renvoyée silencieusement pour les flux couche A).

    Cas gérés :
      PDF + LLAMADMS ou LLAMA_CLOUD_API_KEY → LlamaParse en priorité 1 (si ≥100 car. utiles)
      PDF   → sinon pypdf puis pdfminer (voir ``_extract_pdf_text``)
      DOCX  → python-docx
      .doc  → non supporté (binaire) → erreur explicite (insuffisant)
      Autre → path.read_text()
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    text = ""
    method = "unknown"

    if ext == ".pdf":
        text = _extract_pdf_text(filepath)
        method = "pdf_pypdf_or_pdfminer"
        logger.info(
            "[EXTRACT] pdf done filepath=%s text_len=%d method=%s",
            path.name,
            len(text or ""),
            method,
        )
    elif ext == ".docx":
        text = _extract_docx_text(filepath)
        method = "docx_python_docx"
        logger.info(
            "[EXTRACT] docx done filepath=%s text_len=%d method=%s",
            path.name,
            len(text or ""),
            method,
        )
    elif ext == ".doc":
        logger.error(
            "[EXTRACT] format .doc (Word 97-2003 binaire) non supporté — "
            "convertir en .docx ou PDF — filepath=%s",
            path.name,
        )
        method = "doc_legacy_unsupported"
        logger.info(
            "[EXTRACT] ocr phase=not_available scope=M10A filepath=%s text_len=0",
            path.name,
        )
        raise ExtractionInsufficientTextError(
            f"Format .doc non supporté — fichier={path.name} ; OCR M10A requis pour texte exploitable."
        )
    else:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            method = "plain_read_text"
            logger.info(
                "[EXTRACT] read_text done filepath=%s text_len=%d method=%s",
                path.name,
                len(text or ""),
                method,
            )
        except Exception as e:
            logger.error(
                "[EXTRACT] read_text échec — filepath=%s error=%s",
                path.name,
                str(e),
            )
            raise ExtractionInsufficientTextError(
                f"Lecture fichier impossible — {path.name}: {e}"
            ) from e

    stripped_len = len((text or "").strip())
    logger.info(
        "[EXTRACT] extract_text_any summary filepath=%s ext=%s method=%s text_len=%d min_required=%d",
        path.name,
        ext,
        method,
        stripped_len,
        MIN_EXTRACTED_TEXT_CHARS_FOR_ML,
    )
    if stripped_len < MIN_EXTRACTED_TEXT_CHARS_FOR_ML:
        logger.error(
            "[EXTRACT] INSUFFICIENT_TEXT filepath=%s method=%s text_len=%d min_required=%d",
            path.name,
            method,
            stripped_len,
            MIN_EXTRACTED_TEXT_CHARS_FOR_ML,
        )
        raise ExtractionInsufficientTextError(
            f"Texte extrait insuffisant pour ML — fichier={path.name} text_len={stripped_len} "
            f"min_required={MIN_EXTRACTED_TEXT_CHARS_FOR_ML} method={method}"
        )
    return text


def _extract_docx_text(filepath: str) -> str:
    """Extraction DOCX via python-docx."""
    from docx import Document as DocxDocument

    doc = DocxDocument(str(filepath))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _try_llamaparse_pdf_first(filepath: str) -> str | None:
    """LlamaParse si clé présente et texte suffisant ; sinon None (fallback pypdf/pdfminer)."""
    path = Path(filepath).resolve()
    try:
        from src.core.api_keys import get_llama_cloud_api_key

        get_llama_cloud_api_key()
    except APIKeyMissingError:
        logger.debug(
            "[EXTRACT] llamaparse skip — pas de LLAMADMS ni LLAMA_CLOUD_API_KEY — filepath=%s",
            path.name,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[EXTRACT] llamaparse skip — %s — filepath=%s", exc, path.name)
        return None

    prev = os.environ.get("STORAGE_BASE_PATH")
    raw_out = ""
    try:
        os.environ["STORAGE_BASE_PATH"] = str(path.parent)
        from src.extraction.engine import _extract_llamaparse

        raw_out, _ = _extract_llamaparse(str(path))
    except Exception as exc:
        logger.info(
            "[EXTRACT] llamaparse échec — filepath=%s error=%s — fallback pypdf",
            path.name,
            exc,
        )
        return None
    finally:
        if prev is None:
            os.environ.pop("STORAGE_BASE_PATH", None)
        else:
            os.environ["STORAGE_BASE_PATH"] = prev

    if raw_out and len(raw_out.strip()) >= 100:
        return raw_out
    return None


def _extract_pdf_text(filepath: str, *, skip_llamaparse: bool = False) -> str:
    """
    Étape 0 : LlamaParse (clé nuage) si texte riche — sautée si skip_llamaparse=True.
    Étape 1 : pypdf (toutes les pages).
    Étape 2 : si pypdf échoue ou texte < 100 caractères, tentative pdfminer.six.
    """
    path = Path(filepath)

    if not skip_llamaparse:
        lp = _try_llamaparse_pdf_first(str(path))
        if lp is not None:
            logger.info(
                "[EXTRACT] llamaparse OK — filepath=%s text_len=%d",
                path.name,
                len(lp),
            )
            return lp

    import pypdf

    text_pypdf = ""

    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = []
        for i, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            pages_text.append(raw)
            logger.debug(
                "[EXTRACT] pypdf page=%d chars=%d filepath=%s",
                i,
                len(raw),
                path.name,
            )
        text_pypdf = "\n".join(pages_text)

    except Exception as e:
        logger.error(
            "[EXTRACT] pypdf échec — filepath=%s error=%s — tentative pdfminer",
            path.name,
            str(e),
        )

    pypdf_len = len(text_pypdf.strip())
    logger.info(
        "[EXTRACT] pdf step=pypdf filepath=%s text_len=%d",
        path.name,
        pypdf_len,
    )

    if pypdf_len >= MIN_EXTRACTED_TEXT_CHARS_FOR_ML:
        logger.info(
            "[EXTRACT] pypdf OK — filepath=%s text_len=%d method=pypdf",
            path.name,
            len(text_pypdf),
        )
        return text_pypdf

    text_pdfminer = ""
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        text_pdfminer = pdfminer_extract(str(path)) or ""
        pm_len = len(text_pdfminer.strip())
        logger.info(
            "[EXTRACT] pdf step=pdfminer filepath=%s text_len=%d (pypdf était %d)",
            path.name,
            pm_len,
            pypdf_len,
        )

        if pm_len > pypdf_len:
            logger.info(
                "[EXTRACT] pdfminer fallback OK — filepath=%s text_len=%d method=pdfminer",
                path.name,
                len(text_pdfminer),
            )
            return text_pdfminer

    except Exception as e:
        logger.error(
            "[EXTRACT] pdfminer échec — filepath=%s error=%s",
            path.name,
            str(e),
        )

    logger.info(
        "[EXTRACT] ocr phase=not_available scope=M10A filepath=%s pypdf_len=%d pdfminer_len=%d",
        path.name,
        pypdf_len,
        len(text_pdfminer.strip()),
    )
    if pypdf_len == 0:
        logger.warning(
            "[EXTRACT] text_len=0 — filepath=%s — PDF_SCAN_SANS_OCR ou PDF_CORROMPU — OCR requis (M10A)",
            path.name,
        )
    else:
        logger.warning(
            "[EXTRACT] text_len=%d tres court — filepath=%s — sous seuil ML",
            pypdf_len,
            path.name,
        )

    return text_pypdf


def extract_pdf_text_local_only(filepath: str) -> str:
    """
    PDF : pypdf puis pdfminer uniquement — pas LlamaParse, pas seuil ML, pas d'exception
    sur texte court. Pour heuristiques (ex. bridge ingest : classification native vs scan).
    """
    return _extract_pdf_text(filepath, skip_llamaparse=True)
