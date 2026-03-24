"""LLM cost model heuristics (no API)."""

from __future__ import annotations

from src.annotation.llm_cost_model import (
    build_cost_metadata_for_document,
    estimate_mistral_chat_cost_usd,
    estimate_tokens_from_chars,
)


def test_estimate_tokens_from_chars():
    assert estimate_tokens_from_chars(0) == 0
    assert estimate_tokens_from_chars(400) == 100


def test_estimate_mistral_chat_cost_usd_non_negative():
    c = estimate_mistral_chat_cost_usd(1_000_000, 1_000_000)
    assert c >= 0


def test_build_cost_metadata_for_document():
    meta = build_cost_metadata_for_document(8000, max_completion_tokens=1000)
    assert "token_count_prompt_est" in meta
    assert "cost_estimate_usd" in meta
    assert meta["cost_model"] == "mistral_heuristic_v1"
