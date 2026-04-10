# src/couche_a/llm_router.py
"""
LLM Router — DMS Couche A
ADR-M11-002 : Tier-1 upgrade mistral-large + mistral-ocr

Constantes de modèles centralisées.
NE JAMAIS hardcoder un model name en dehors de ce fichier.
Toute modification → GO CTO obligatoire.

Mandat 4 — 2026-03-17 :
  Ajout LLMRouter + select_tier + ANNOTATION_BACKEND_URL.
  Toutes les constantes et fonctions existantes CONSERVÉES.

V5.2 : Variables d'environnement lues via get_settings() (Pydantic Settings).
"""

import logging

try:
    from mistralai import Mistral
except (ImportError, AttributeError):
    from mistralai.client import Mistral  # mistralai v2.x

from src.core.config import get_settings
from src.couche_a.extraction_models import Tier

logger = logging.getLogger(__name__)


def _tier_1_model() -> str:
    return get_settings().TIER_1_MODEL


def _tier_1_ocr_model() -> str:
    return get_settings().TIER_1_OCR_MODEL


TIER_1_MODEL: str = "mistral-large-latest"
TIER_1_OCR_MODEL: str = "mistral-ocr-latest"


def _refresh_model_constants() -> None:
    """Refresh module-level constants from Settings (called lazily)."""
    global TIER_1_MODEL, TIER_1_OCR_MODEL
    s = get_settings()
    TIER_1_MODEL = s.TIER_1_MODEL
    TIER_1_OCR_MODEL = s.TIER_1_OCR_MODEL


def azure_ocr_available() -> bool:
    """True si Azure Form Recognizer est configuré."""
    s = get_settings()
    return bool(s.AZURE_FORM_RECOGNIZER_ENDPOINT and s.AZURE_FORM_RECOGNIZER_KEY)


def get_llm_client() -> Mistral:
    """Retourne un client Mistral configuré depuis MISTRAL_API_KEY."""
    api_key = get_settings().MISTRAL_API_KEY
    if not api_key:
        raise RuntimeError(
            "[LLM_ROUTER] MISTRAL_API_KEY absent — "
            "impossible d'instancier le client Mistral."
        )
    return Mistral(api_key=api_key)


# ── LLMRouter — Mandat 4 ──────────────────────────────────────


class LLMRouter:
    """
    Routeur hiérarchique TIER 1 → TIER 4.

    TIER 1 : annotation-backend Railway — online
             MISTRAL_API_KEY présente
    TIER 4 : fallback offline — review_required traçable
             MISTRAL_API_KEY absente ou backend KO

    Principe DMS :
      Le système préfère renvoyer review_required
      plutôt qu'inventer une valeur.
    """

    def __init__(self) -> None:
        s = get_settings()
        self._backend_url = s.ANNOTATION_BACKEND_URL
        self._timeout = s.ANNOTATION_TIMEOUT

    @property
    def backend_url(self) -> str:
        return self._backend_url

    @property
    def timeout(self) -> int:
        return self._timeout

    def select_tier(self) -> Tier:
        has_api_key = bool(get_settings().MISTRAL_API_KEY.strip())
        if not has_api_key:
            logger.warning("[ROUTER] MISTRAL_API_KEY absente → TIER 4")
            return Tier.T4_OFFLINE
        logger.debug(
            "[ROUTER] TIER 1 sélectionné → %s",
            self._backend_url,
        )
        return Tier.T1

    def is_online_capable(self) -> bool:
        return bool(get_settings().MISTRAL_API_KEY.strip())


# Singleton
router = LLMRouter()
