"""Embedding Client — Canon V5.1.0 Section 7.7.

Client Mistral pour embeddings vectoriels (mistral-embed).
Utilisé par le semantic router pour classifier les intents.

Dégradation gracieuse : si MISTRAL_API_KEY absente ou numpy non installé,
retourne un vecteur aléatoire normalisé (pour dev/test).
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_client: Any = None
_fallback = False


def _get_client() -> Any:
    """Lazy init du client Mistral. Retourne None si API key absente."""
    global _client, _fallback

    if _client is not None:
        return _client

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.warning(
            "MISTRAL_API_KEY non définie — embedding_client en mode fallback aléatoire."
        )
        _fallback = True
        return None

    try:
        from mistralai import Mistral

        _client = Mistral(api_key=api_key)
        return _client
    except ImportError:
        logger.warning(
            "mistralai non installé — embedding_client en mode fallback aléatoire."
        )
        _fallback = True
        return None


async def get_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """Retourne le vecteur d'embedding pour un texte donné.

    En mode fallback (pas d'API key ou SDK), retourne un vecteur
    déterministe basé sur le hash du texte (reproductible pour tests).
    """
    client = _get_client()

    if client is None or _fallback:
        stable_hash = int.from_bytes(
            hashlib.sha256(text.encode("utf-8")).digest()[:4], "big"
        )
        rng = np.random.RandomState(stable_hash % (2**31))
        vec = rng.randn(dim).astype(np.float32)
        return vec / np.linalg.norm(vec)

    response = await client.embeddings.create_async(
        model="mistral-embed",
        inputs=[text],
    )
    return np.array(response.data[0].embedding, dtype=np.float32)
