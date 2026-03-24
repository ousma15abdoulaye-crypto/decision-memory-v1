"""
Heuristic LLM cost estimation for annotation passes (no live API calls).

See: docs/contracts/annotation/LLM_COST_MODEL_ANNOTATION.md
"""

from __future__ import annotations

import os
from typing import Any


def _fenv(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def estimate_tokens_from_chars(char_count: int, *, divisor: float = 4.0) -> int:
    """Rough prompt token estimate (documented approximation, not billing)."""
    if char_count <= 0:
        return 0
    return max(1, int(char_count / divisor))


def estimate_mistral_chat_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    USD estimate using configurable price-per-1M tokens (update from vendor list).

    Defaults are conservative placeholders — replace via env for accurate budgets.
    """
    pin = _fenv("MISTRAL_USD_PER_1M_INPUT_TOKENS", 2.0)
    pout = _fenv("MISTRAL_USD_PER_1M_OUTPUT_TOKENS", 6.0)
    return (prompt_tokens * pin + completion_tokens * pout) / 1_000_000.0


def build_cost_metadata_for_document(
    normalized_char_count: int,
    *,
    max_completion_tokens: int = 32_000,
) -> dict[str, Any]:
    """Metadata fragment for AnnotationPassOutput.metadata."""
    prompt_est = estimate_tokens_from_chars(normalized_char_count)
    completion_est = max_completion_tokens
    cost = estimate_mistral_chat_cost_usd(prompt_est, completion_est)
    return {
        "token_count_prompt_est": prompt_est,
        "token_count_completion_est": completion_est,
        "cost_estimate_usd": round(cost, 6),
        "cost_model": "mistral_heuristic_v1",
    }
