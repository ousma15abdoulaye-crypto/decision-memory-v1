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
"""

import logging
import os

try:
    from mistralai.client import Mistral
except ImportError:
    from mistralai import Mistral  # mistralai v1.x

from src.couche_a.extraction_models import Tier

logger = logging.getLogger(__name__)

# ── Tier-1 — Annotation + extraction DAO ─────────────────────
TIER_1_MODEL: str = os.environ.get("TIER_1_MODEL", "mistral-large-latest")

# ── Tier-1 — OCR PDF scannés et images ───────────────────────
TIER_1_OCR_MODEL: str = os.environ.get("TIER_1_OCR_MODEL", "mistral-ocr-latest")

# ── Fallback OCR — Azure Form Recognizer ─────────────────────
AZURE_OCR_ENDPOINT: str = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
AZURE_OCR_KEY: str = os.environ.get("AZURE_FORM_RECOGNIZER_KEY", "")

# ── Annotation backend ────────────────────────────────────────
ANNOTATION_BACKEND_URL: str = os.environ.get(
    "ANNOTATION_BACKEND_URL",
    "http://annotation-backend:9090",
)
ANNOTATION_TIMEOUT_SECONDS: int = int(os.environ.get("ANNOTATION_TIMEOUT", "120"))
_MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")


# ── Fonctions existantes — CONSERVÉES ────────────────────────


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
    """True si Azure Form Recognizer est configuré."""
    return bool(AZURE_OCR_ENDPOINT and AZURE_OCR_KEY)


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
        self._backend_url = ANNOTATION_BACKEND_URL
        self._timeout = ANNOTATION_TIMEOUT_SECONDS

    @property
    def backend_url(self) -> str:
        return self._backend_url

    @property
    def timeout(self) -> int:
        return self._timeout

    def select_tier(self) -> Tier:
        # Relecture dynamique de MISTRAL_API_KEY pour éviter de figer l'état
        has_api_key = bool(os.environ.get("MISTRAL_API_KEY", ""))
        if not has_api_key:
            logger.warning("[ROUTER] MISTRAL_API_KEY absente → TIER 4")
            return Tier.T4_OFFLINE
        logger.debug(
            "[ROUTER] TIER 1 sélectionné → %s",
            self._backend_url,
        )
        return Tier.T1

    def is_online_capable(self) -> bool:
        # Capacité online basée sur l'état courant de l'environnement
        return bool(os.environ.get("MISTRAL_API_KEY", ""))


# Singleton
router = LLMRouter()
