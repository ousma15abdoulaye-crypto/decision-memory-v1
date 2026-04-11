"""Embedding Client — Canon V5.1.0 Section 7.7.

Client Mistral pour embeddings vectoriels (mistral-embed).
Utilisé par le semantic router pour classifier les intents.

Dégradation gracieuse : si MISTRAL_API_KEY absente ou SDK absent,
retourne un embedding lexical déterministe (hashing trick) pour dev/CI.
"""

from __future__ import annotations

import hashlib
import logging
import re
import traceback
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

    from src.core.config import get_settings

    api_key = get_settings().MISTRAL_API_KEY
    if not api_key:
        logger.warning(
            "MISTRAL_API_KEY non définie — embedding_client en mode fallback "
            "lexical déterministe (sans API Mistral)."
        )
        _fallback = True
        return None

    try:
        from mistralai.client import Mistral

        _client = Mistral(api_key=api_key)
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "mistralai indisponible — embedding_client en mode fallback "
            "lexical déterministe (sans API Mistral). "
            "Cause : %s: %s\n%s",
            type(exc).__name__,
            exc,
            traceback.format_exc(),
        )
        _fallback = True
        return None


def _lexical_hash_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """Embedding déterministe hors API — sac de mots via hashing trick.

    Les anciens vecteurs « aléatoires par phrase » décorrélaient totalement
    les requêtes proches (« prix du ciment à Bamako » vs exemples marché),
    ce qui faisait classer RECOMMENDATION au hasard et déclenchait INV-W06.
    Ici, les tokens partagés renforcent la similarité cosinus entre questions
    de prix / zone et les INTENT_EXAMPLES MARKET_QUERY.
    """
    vec = np.zeros(dim, dtype=np.float32)
    low = text.lower()
    tokens = re.findall(r"[a-zàâäéèêëïîôùûçœæ0-9]+", low)
    if not tokens:
        digest = hashlib.sha256(low.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        vec[idx] = 1.0
    else:
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            for i in range(0, min(len(digest) - 1, 16), 2):
                idx = int.from_bytes(digest[i : i + 2], "big") % dim
                vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:
        vec[0] = 1.0
        norm = 1.0
    return vec / norm


async def get_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """Retourne le vecteur d'embedding pour un texte donné.

    En mode fallback (pas d'API key ou SDK), retourne un vecteur
    déterministe basé sur les tokens (hashing trick), pas un tirage aléatoire
    par phrase — pour que le routeur sémantique reste cohérent en dev/CI.
    """
    client = _get_client()

    if client is None or _fallback:
        return _lexical_hash_embedding(text, dim=dim)

    response = await client.embeddings.create_async(
        model="mistral-embed",
        inputs=[text],
    )
    return np.array(response.data[0].embedding, dtype=np.float32)
