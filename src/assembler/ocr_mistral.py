"""Client Mistral OCR 3 — moteur OCR primaire du Pass -1.

Stratégie :
  - PDF scan / image → Mistral OCR 3 (multimodal)
  - PDF natif → pdfminer/pypdf (gratuit, 0 token)
  - DOCX → python-docx (gratuit)
  - XLSX → openpyxl (gratuit)

Fallback : si Mistral timeout (> OCR_TIMEOUT_S), délègue à ocr_azure.py.

Référence : Plan V4.2.0 Phase 4 — src/assembler/ocr_mistral.py
ADR-V420-001 (pydantic-ai).
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

OCR_TIMEOUT_S = 20
MISTRAL_OCR_MODEL = "mistral-ocr-latest"


def _encode_file_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


async def ocr_with_mistral(file_path: str | Path) -> dict:
    """Extrait le texte d'un fichier via Mistral OCR 3.

    Args:
        file_path: Chemin vers le fichier (PDF scan ou image).

    Returns:
        dict avec keys: raw_text, confidence, ocr_engine, structured_json.
        En cas d'erreur : raw_text="", confidence=0.0, error=str.
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    api_key = os.environ.get("MISTRAL_API_KEY", "")

    if not api_key:
        logger.warning("[OCR-MISTRAL] MISTRAL_API_KEY absent — fallback Azure.")
        return {
            "raw_text": "",
            "confidence": 0.0,
            "ocr_engine": "mistral_ocr_3",
            "error": "MISTRAL_API_KEY manquant",
        }

    try:
        import httpx

        if ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
            media_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".tiff": "image/tiff",
                ".tif": "image/tiff",
            }
            media_type = media_map.get(ext, "image/jpeg")
            b64_data = _encode_file_b64(path)
            content = [
                {
                    "type": "image_url",
                    "image_url": f"data:{media_type};base64,{b64_data}",
                }
            ]
        else:
            b64_data = _encode_file_b64(path)
            content = [
                {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{b64_data}",
                }
            ]

        payload = {
            "model": MISTRAL_OCR_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": content
                    + [
                        {
                            "type": "text",
                            "text": (
                                "Extrais tout le texte de ce document. "
                                "Retourne le texte brut sans formatage."
                            ),
                        }
                    ],
                }
            ],
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=OCR_TIMEOUT_S) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_text = data["choices"][0]["message"]["content"] or ""
        return {
            "raw_text": raw_text,
            "confidence": 0.85,
            "ocr_engine": "mistral_ocr_3",
            "structured_json": None,
        }

    except Exception as exc:
        logger.error("[OCR-MISTRAL] Erreur sur %s : %s", path.name, exc)
        return {
            "raw_text": "",
            "confidence": 0.0,
            "ocr_engine": "mistral_ocr_3",
            "error": str(exc),
        }


async def ocr_native_pdf(file_path: str | Path) -> dict:
    """Extrait le texte d'un PDF natif via pypdf (0 coût API).

    Returns:
        dict avec raw_text, confidence=1.0, ocr_engine='none'.
    """
    path = Path(file_path)
    try:
        import pypdf  # type: ignore[import-untyped]

        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            pages = [page.extract_text() or "" for page in reader.pages]
        raw_text = "\n".join(pages)
        return {
            "raw_text": raw_text,
            "confidence": 1.0,
            "ocr_engine": "none",
            "structured_json": None,
        }
    except Exception as exc:
        logger.error("[OCR-NATIVE] Erreur pypdf sur %s : %s", path.name, exc)
        return {
            "raw_text": "",
            "confidence": 0.0,
            "ocr_engine": "none",
            "error": str(exc),
        }
