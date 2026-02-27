"""Tests rate limiting Redis — fallback no-op + TTL mock horloge.

RÈGLE-21 : zéro appel Redis réel dans les tests de fallback.
Fenêtre glissante mockée — zéro attente réelle 60s.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

# ── App de test minimale ──────────────────────────────────────────────────────


def _make_app(redis_url: str | None = None):
    """Crée une app FastAPI minimale avec les deux middlewares."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from src.couche_a.auth.middleware import (
        RedisRateLimitMiddleware,
        SecurityHeadersMiddleware,
    )

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RedisRateLimitMiddleware, redis_url=redis_url)

    @app.get("/ping")
    def ping():
        return JSONResponse({"ok": True})

    @app.get("/auth/token")
    def auth_token():
        return JSONResponse({"token": "test"})

    return app


# ── Fallback Redis absent ─────────────────────────────────────────────────────


def test_redis_absent_requete_passe():
    """Redis absent → requête passe sans erreur (fallback no-op — RÈGLE-04)."""
    app = _make_app(redis_url="redis://localhost:19999/0")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_redis_absent_pas_de_429():
    """Redis absent → jamais de 429, même après beaucoup de requêtes."""
    app = _make_app(redis_url="redis://localhost:19999/0")
    client = TestClient(app, raise_server_exceptions=False)

    for _ in range(5):
        response = client.get("/ping")
        assert response.status_code == 200


# ── 429 avec Redis mocké ──────────────────────────────────────────────────────


def test_101eme_requete_meme_ip_renvoie_429():
    """101ème requête même IP → 429 + header Retry-After présent."""
    mock_redis = MagicMock()
    # Pipeline mock : simule 101 requêtes comptées
    mock_pipe = MagicMock()
    mock_pipe.execute.return_value = [None, None, 101, None]
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.ping.return_value = True

    from src.couche_a.auth import middleware as mw_module

    with patch.object(
        mw_module.RedisRateLimitMiddleware,
        "_get_redis",
        return_value=mock_redis,
    ):
        app2 = _make_app()

        mw = mw_module.RedisRateLimitMiddleware(app2)
        mw._redis = mock_redis
        mw._redis_unavailable = False

        allowed, retry_after = mw._check_limit("rate:ip:1.2.3.4", 100)

    assert not allowed
    assert retry_after == 60


def test_retry_after_header_present():
    """Réponse 429 contient Retry-After."""
    from src.couche_a.auth.middleware import RedisRateLimitMiddleware

    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute.return_value = [None, None, 101, None]
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.ping.return_value = True

    mw = RedisRateLimitMiddleware(MagicMock())
    mw._redis = mock_redis
    mw._redis_unavailable = False

    allowed, retry_after = mw._check_limit("rate:ip:x.x.x.x", 100)

    assert not allowed
    assert retry_after > 0


def test_ttl_redis_mock_horloge():
    """TTL Redis testé par mock horloge — zéro attente réelle 60s."""

    from src.couche_a.auth.middleware import RedisRateLimitMiddleware

    mock_redis = MagicMock()
    mock_pipe = MagicMock()

    call_count = [0]

    def mock_execute():
        call_count[0] += 1
        if call_count[0] == 1:
            return [None, None, 50, None]
        return [None, None, 105, None]

    mock_pipe.execute.side_effect = mock_execute
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.ping.return_value = True

    mw = RedisRateLimitMiddleware(MagicMock())
    mw._redis = mock_redis
    mw._redis_unavailable = False

    with patch("src.couche_a.auth.middleware.time") as mock_time:
        mock_time.time.return_value = 1000.0

        allowed1, _ = mw._check_limit("rate:ip:test", 100)
        assert allowed1 is True

        mock_time.time.return_value = 1001.0
        allowed2, retry_after = mw._check_limit("rate:ip:test", 100)
        assert allowed2 is False
        assert retry_after == 60
