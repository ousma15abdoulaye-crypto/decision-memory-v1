"""Client Azure Document Intelligence — fallback OCR Pass -1.

Utilisé quand Mistral OCR 3 timeout (> 20s) ou retourne une erreur.
Azure = fallback transparent, pas de HITL pour ce type d'erreur.

Référence : Plan V4.2.0 Phase 4 — src/assembler/ocr_azure.py
ADR-V420-001 (pydantic-ai).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

AZURE_OCR_TIMEOUT_S = 30
AZURE_API_VERSION = "2024-02-29-preview"


async def ocr_with_azure(file_path: str | Path) -> dict:
    """Extrait le texte via Azure Document Intelligence (Read API).

    Requiert les variables d'environnement :
      AZURE_DOC_INTEL_ENDPOINT : endpoint Azure (https://...cognitiveservices.azure.com)
      AZURE_DOC_INTEL_KEY      : clé API Azure

    Args:
        file_path: Chemin vers le fichier (PDF scan ou image).

    Returns:
        dict avec raw_text, confidence, ocr_engine='azure_doc_intel'.
        En cas d'erreur : raw_text="", confidence=0.0, error=str.
    """
    path = Path(file_path)
    endpoint = os.environ.get("AZURE_DOC_INTEL_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_DOC_INTEL_KEY", "")

    if not endpoint or not api_key:
        logger.warning(
            "[OCR-AZURE] AZURE_DOC_INTEL_ENDPOINT ou KEY absent — OCR indisponible."
        )
        return {
            "raw_text": "",
            "confidence": 0.0,
            "ocr_engine": "azure_doc_intel",
            "error": "Azure credentials manquantes",
        }

    try:
        import httpx

        analyze_url = (
            f"{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze"
            f"?api-version={AZURE_API_VERSION}"
        )

        file_bytes = path.read_bytes()
        ext = path.suffix.lower()
        content_type_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        content_type = content_type_map.get(ext, "application/octet-stream")

        async with httpx.AsyncClient(timeout=AZURE_OCR_TIMEOUT_S) as client:
            resp = await client.post(
                analyze_url,
                headers={
                    "Ocp-Apim-Subscription-Key": api_key,
                    "Content-Type": content_type,
                },
                content=file_bytes,
            )
            resp.raise_for_status()

            operation_url = resp.headers.get("Operation-Location", "")
            if not operation_url:
                return {
                    "raw_text": "",
                    "confidence": 0.0,
                    "ocr_engine": "azure_doc_intel",
                    "error": "Operation-Location header absent",
                }

            import asyncio

            for _ in range(15):
                await asyncio.sleep(2)
                result_resp = await client.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": api_key},
                )
                result_resp.raise_for_status()
                result = result_resp.json()

                status = result.get("status", "")
                if status == "succeeded":
                    content = result.get("analyzeResult", {}).get("content", "")
                    return {
                        "raw_text": content,
                        "confidence": 0.9,
                        "ocr_engine": "azure_doc_intel",
                        "structured_json": None,
                    }
                if status == "failed":
                    return {
                        "raw_text": "",
                        "confidence": 0.0,
                        "ocr_engine": "azure_doc_intel",
                        "error": f"Azure analyse échouée : {result.get('error')}",
                    }

            return {
                "raw_text": "",
                "confidence": 0.0,
                "ocr_engine": "azure_doc_intel",
                "error": "Azure timeout (30s * 15 polls)",
            }

    except Exception as exc:
        logger.error("[OCR-AZURE] Erreur sur %s : %s", path.name, exc)
        return {
            "raw_text": "",
            "confidence": 0.0,
            "ocr_engine": "azure_doc_intel",
            "error": str(exc),
        }
