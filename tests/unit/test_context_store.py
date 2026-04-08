"""Tests Context Store — Canon V5.1.0 Section 7.8.

Tests MQLContext : build_messages, sliding window, budget tokens.
"""

from __future__ import annotations

from src.agent.context_store import (
    HISTORY_BUDGET,
    MQL_CONTEXT_TTL,
    MQLContext,
)


class TestMQLContextTTL:
    def test_ttl_is_3600(self):
        assert MQL_CONTEXT_TTL == 3600


class TestMQLContextBuildMessages:
    def test_empty_context(self):
        ctx = MQLContext()
        msgs = ctx.build_messages("Tu es DMS.", "Bonjour")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_history_included(self):
        ctx = MQLContext(
            messages=[
                {"role": "user", "content": "Premier msg"},
                {"role": "assistant", "content": "Réponse"},
            ]
        )
        msgs = ctx.build_messages("System", "Deuxième msg")
        assert len(msgs) == 4
        assert msgs[0]["role"] == "system"
        assert msgs[1]["content"] == "Premier msg"
        assert msgs[2]["content"] == "Réponse"
        assert msgs[3]["content"] == "Deuxième msg"

    def test_sliding_window_evicts_old(self):
        long_msg = "x" * (HISTORY_BUDGET * 4 + 100)
        ctx = MQLContext(
            messages=[
                {"role": "user", "content": long_msg},
                {"role": "assistant", "content": "ok"},
            ]
        )
        msgs = ctx.build_messages("System", "New")
        assert msgs[-1]["content"] == "New"
        assert msgs[0]["role"] == "system"
        assert len(msgs) <= 4

    def test_appends_user_message_to_history(self):
        ctx = MQLContext()
        ctx.build_messages("System", "Hello")
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["content"] == "Hello"

    def test_add_assistant_message(self):
        ctx = MQLContext()
        ctx.add_assistant_message("Réponse IA")
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "assistant"
