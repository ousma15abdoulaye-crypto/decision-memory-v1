"""Output Filter INV-W06 — Canon V5.1.0.

Filtre post-LLM appliqué aux tokens streamés avant diffusion client.
Détecte et remplace les segments interdits par le Canon (winner, rank,
recommendation, best_offer, etc.) dans le flux SSE.

INV-W06 : Le système ne produit jamais de recommandation, classement,
gagnant ou sélection. Ce filtre complète le guardrail d'entrée
(guardrail.py) pour couvrir les glissements implicites du LLM.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

logger = logging.getLogger(__name__)

# Patterns interdits — Canon INV-W06 / RÈGLE-09 V4.1.0
_FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwinner\b", re.IGNORECASE),
    re.compile(r"\branking?s?\b", re.IGNORECASE),
    re.compile(r"\bclassement\b", re.IGNORECASE),
    re.compile(r"\brecommandation\b", re.IGNORECASE),
    re.compile(r"\bje\s+recommande\b", re.IGNORECASE),
    re.compile(r"\bje\s+conseille\b", re.IGNORECASE),
    re.compile(r"\bbest[_\s]offer\b", re.IGNORECASE),
    re.compile(r"\bgagnant\b", re.IGNORECASE),
    re.compile(
        r"\bmeilleur(?:e)?\s+(?:offre|fournisseur|choix|candidat)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bdevrait(?:[\s-]on)?\s+(?:choisir|attribuer|sélectionner|retenir)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\battribuer\s+le\s+marché\s+à\b", re.IGNORECASE),
    re.compile(r"\bsélectionner\s+ce\s+fournisseur\b", re.IGNORECASE),
]

_REPLACEMENT = "[CONTENU FILTRÉ — INV-W06]"

# Taille seuil d'accumulation avant flush (caractères).
# Assez grand pour capturer des patterns multi-tokens, assez petit pour la latence.
_FLUSH_CHARS = 120

# Overlap conservé après chaque flush pour éviter de couper un pattern en bord de fenêtre.
# Doit être >= longueur du pattern le plus long (~50 chars).
_OVERLAP_CHARS = 60


def _apply_patterns(text: str) -> tuple[str, bool]:
    """Applique tous les patterns interdits sur un bloc de texte.

    Returns:
        (filtered_text, was_filtered)
    """
    result = text
    triggered = False
    for pat in _FORBIDDEN_PATTERNS:
        replaced = pat.sub(_REPLACEMENT, result)
        if replaced != result:
            triggered = True
            result = replaced
    return result, triggered


async def filter_token_stream(
    stream: AsyncGenerator[dict[str, Any], None],
    trace: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Filtre INV-W06 sur le flux d'événements SSE d'un handler.

    Accumule les tokens dans un buffer, applique les patterns interdits
    par fenêtre glissante, puis yield les événements filtrés.

    Les événements non-token (sources, tool_call, done, error) sont
    passés directement après flush du buffer courant.
    """
    buffer = ""
    filter_triggered = False

    async for event in stream:
        if event.get("type") != "token":
            # Flush le buffer avant tout événement non-token
            if buffer:
                filtered, triggered = _apply_patterns(buffer)
                if triggered:
                    filter_triggered = True
                    logger.warning(
                        "[output_filter] INV-W06 : contenu filtré dans le flux LLM."
                    )
                if filtered.strip():
                    yield {"type": "token", "content": filtered}
                buffer = ""
            yield event
            continue

        content = event.get("content", "")
        if not content:
            yield event
            continue

        buffer += content

        # Flush dès que le buffer dépasse le seuil.
        # CRITIQUE : scanner le buffer COMPLET (overlap inclus) pour capturer les patterns
        # qui straddlent la frontière flush_part/overlap. Scanner seulement flush_part
        # manquerait un pattern dont le début est avant la frontière et la fin après.
        if len(buffer) >= _FLUSH_CHARS:
            full_filtered, triggered = _apply_patterns(buffer)
            if triggered:
                filter_triggered = True
                logger.warning(
                    "[output_filter] INV-W06 : contenu filtré dans le flux LLM."
                )
            if len(full_filtered) > _OVERLAP_CHARS:
                flush_out = full_filtered[:-_OVERLAP_CHARS]
                buffer = full_filtered[-_OVERLAP_CHARS:]
                if flush_out.strip():
                    yield {"type": "token", "content": flush_out}
            else:
                # Après filtrage, pas assez de contenu pour splitter — accumuler
                buffer = full_filtered

    # Flush final du buffer restant
    if buffer:
        filtered, triggered = _apply_patterns(buffer)
        if triggered:
            filter_triggered = True
            logger.warning(
                "[output_filter] INV-W06 : contenu filtré dans le flux LLM (flush final)."
            )
        if filtered.strip():
            yield {"type": "token", "content": filtered}

    if filter_triggered:
        try:
            trace.update(tags=["output_filter_inv_w06"])
        except Exception:
            pass
