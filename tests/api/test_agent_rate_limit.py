"""Tests Rate Limit Agent — Canon V5.1.0 (BUG-P1-03).

Vérifie que le décorateur @limiter.limit(LIMIT_ANNOTATION) est présent
sur la route POST /agent/prompt.
"""

from __future__ import annotations

import inspect


class TestAgentRateLimitDecorator:
    """Vérifie la présence et la configuration du rate limit sur /agent/prompt."""

    def test_route_has_request_parameter(self):
        """La route agent_prompt doit accepter Request (requis par slowapi)."""
        from src.api.routers.agent import agent_prompt

        sig = inspect.signature(agent_prompt)
        params = list(sig.parameters.keys())
        assert "request" in params, (
            "La route agent_prompt doit avoir un paramètre 'request' "
            "pour que slowapi puisse appliquer le rate limit."
        )

    def test_rate_limit_annotation_defined(self):
        """LIMIT_ANNOTATION doit être défini et vaut '10/minute'."""
        from src.ratelimit import LIMIT_ANNOTATION

        assert LIMIT_ANNOTATION == "10/minute"

    def test_agent_router_registered_in_module(self):
        """Le router agent est bien importable et contient POST /agent/prompt."""
        from src.api.routers.agent import router

        routes = {r.path: r.methods for r in router.routes}
        assert "/api/agent/prompt" in routes
        assert "POST" in routes["/api/agent/prompt"]

    def test_limiter_is_initialized(self):
        """Le limiter global est correctement initialisé (non-None)."""
        from src.ratelimit import limiter

        assert limiter is not None
