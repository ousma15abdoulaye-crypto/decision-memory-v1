"""
LLM Router — DMS Couche A
ADR-M11-002 : Tier-1 upgrade mistral-large + mistral-ocr

Constantes de modèles centralisées.
NE JAMAIS hardcoder un model name en dehors de ce fichier.
Toute modification → GO CTO obligatoire.
"""

import os

from mistralai import Mistral

# ── Tier-1 — Annotation + extraction DAO ──────────────────────────────────
TIER_1_MODEL: str = os.environ.get("TIER_1_MODEL", "mistral-large-latest")

# ── Tier-1 — OCR PDF scannés et images ────────────────────────────────────
TIER_1_OCR_MODEL: str = os.environ.get("TIER_1_OCR_MODEL", "mistral-ocr-latest")

# ── Fallback OCR — Azure Form Recognizer si endpoint configuré ────────────
AZURE_OCR_ENDPOINT: str = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
AZURE_OCR_KEY: str = os.environ.get("AZURE_FORM_RECOGNIZER_KEY", "")


def get_llm_client() -> Mistral:
    """Retourne un client Mistral configuré depuis MISTRAL_API_KEY."""
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "[LLM_ROUTER] MISTRAL_API_KEY absent — "
            "impossible d'instancier le client Mistral."
        )
    return Mistral(api_key=api_key)


def azure_ocr_available() -> bool:
    """True si Azure Form Recognizer est configuré comme fallback."""
    return bool(AZURE_OCR_ENDPOINT and AZURE_OCR_KEY)
