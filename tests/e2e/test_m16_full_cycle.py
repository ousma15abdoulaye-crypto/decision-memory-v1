"""E2E M16 — marqué skip si pas de fixture workspace complète."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("M16_E2E_WORKSPACE_ID"),
    reason="définir M16_E2E_WORKSPACE_ID pour exécuter le cycle E2E",
)


@pytest.mark.e2e
def test_m16_cycle_placeholder() -> None:
    """Réservé : cycle complet avec TestClient + DB réelle (workspace id env)."""
    assert os.environ.get("M16_E2E_WORKSPACE_ID")
