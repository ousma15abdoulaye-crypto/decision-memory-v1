"""Tests headers de sécurité — SecurityHeadersMiddleware.

RÈGLE-07 : assertions explicites sur chaque header.
RÈGLE-21 : zéro appel API réel.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from src.couche_a.auth.middleware import SecurityHeadersMiddleware

# ── App de test ───────────────────────────────────────────────────────────────


def _make_app():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping():
        return JSONResponse({"ok": True})

    @app.get("/auth/token")
    def auth_token():
        return JSONResponse({"token": "test"})

    @app.get("/auth/me")
    def auth_me():
        return JSONResponse({"user": "test"})

    return app


client = TestClient(_make_app())


# ── Headers présents sur toutes les réponses ──────────────────────────────────


def test_x_content_type_options():
    """X-Content-Type-Options: nosniff présent sur toute réponse."""
    response = client.get("/ping")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_x_frame_options():
    """X-Frame-Options: DENY présent sur toute réponse."""
    response = client.get("/ping")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_x_xss_protection():
    """X-XSS-Protection présent sur toute réponse."""
    response = client.get("/ping")
    value = response.headers.get("X-XSS-Protection", "")
    assert "1" in value
    assert "mode=block" in value


def test_strict_transport_security():
    """Strict-Transport-Security présent sur toute réponse."""
    response = client.get("/ping")
    hsts = response.headers.get("Strict-Transport-Security", "")
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts


def test_content_security_policy():
    """Content-Security-Policy: default-src 'self' présent."""
    response = client.get("/ping")
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp
    assert "'self'" in csp


def test_referrer_policy():
    """Referrer-Policy présent sur toute réponse."""
    response = client.get("/ping")
    rp = response.headers.get("Referrer-Policy", "")
    assert rp == "strict-origin-when-cross-origin"


# ── Cache-Control sur routes /auth/* uniquement ───────────────────────────────


def test_cache_control_no_store_sur_auth():
    """Route /auth/* → Cache-Control: no-store."""
    response = client.get("/auth/token")
    assert response.headers.get("Cache-Control") == "no-store"


def test_cache_control_absent_hors_auth():
    """Route non-auth → Cache-Control: no-store absent."""
    response = client.get("/ping")
    assert response.headers.get("Cache-Control") != "no-store"


def test_all_security_headers_present_on_auth_route():
    """Route /auth/* → tous les 6 headers + Cache-Control présents."""
    response = client.get("/auth/me")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "mode=block" in response.headers.get("X-XSS-Protection", "")
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")
    assert "default-src" in response.headers.get("Content-Security-Policy", "")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("Cache-Control") == "no-store"
