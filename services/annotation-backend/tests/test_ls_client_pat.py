"""Auth LS : PAT JWT (refresh + Bearer) vs legacy Token."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import ls_client as ls_client_mod  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_pat_cache() -> None:
    ls_client_mod._pat_access_cache.clear()
    yield
    ls_client_mod._pat_access_cache.clear()


def test_looks_like_jwt_pat() -> None:
    assert ls_client_mod._looks_like_ls_jwt_pat("eyJhbGciOiJIUzI1NiJ9.eyJ4IjoxfQ.fake")
    assert not ls_client_mod._looks_like_ls_jwt_pat("legacy-token-no-dots")


def test_legacy_token_header() -> None:
    h = ls_client_mod._ls_auth_headers("https://ls.test", "abc123legacy")
    assert h["Authorization"] == "Token abc123legacy"


def test_legacy_forced_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LABEL_STUDIO_LEGACY_TOKEN", "1")
    jwt_key = "eyJhbGciOiJIUzI1NiJ9.eyJ4IjoxfQ.sig"
    h = ls_client_mod._ls_auth_headers("https://ls.test", jwt_key)
    assert h["Authorization"] == f"Token {jwt_key}"


@patch.object(ls_client_mod.requests, "post")
def test_pat_uses_refresh_then_bearer(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access": "short-lived-access"}
    mock_post.return_value = mock_resp

    h = ls_client_mod._ls_auth_headers(
        "https://ls.test",
        "eyJhbGciOiJIUzI1NiJ9.eyJ4IjoxfQ.sig",
    )
    assert h["Authorization"] == "Bearer short-lived-access"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://ls.test/api/token/refresh"
    assert kwargs["json"] == {"refresh": "eyJhbGciOiJIUzI1NiJ9.eyJ4IjoxfQ.sig"}
