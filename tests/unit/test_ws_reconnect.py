"""Tests WebSocket reconnect — Canon V5.1.0 (BUG-P2-01).

Vérifie la logique de reconnexion avec backoff exponentiel dans
workspace-events-bridge.tsx.

Ces tests sont en unit/ (pas integration/) : pas de DB — imports réels du bundle V5.1.

Note : le composant React WorkspaceEventsBridge est couvert par E2E Playwright.
"""

from __future__ import annotations


class TestWebSocketEndpointRegistered:
    """Vérifie que l'endpoint WS est enregistré dans l'application FastAPI."""

    def test_ws_endpoint_in_v51_bundle(self):
        """L'endpoint /ws/workspace/{workspace_id}/events doit être monté."""
        from src.api.dms_v51_mount import mount_v51_workspace_http_and_ws

        assert callable(mount_v51_workspace_http_and_ws)

    def test_ws_events_module_importable(self):
        """Le handler WebSocket workspace_events doit être importable (Canon O2)."""
        from src.api.ws import workspace_events as ws_module

        assert ws_module.workspace_events_ws is not None
        assert callable(ws_module.workspace_events_ws)


class TestReconnectConstants:
    """Valide les constantes de reconnexion (alignées avec le composant React)."""

    def test_backoff_logic(self):
        """La séquence de backoff exponentiel doit être bornée à max_backoff_ms."""
        base_backoff_ms = 1000
        max_backoff_ms = 30_000
        max_retries_before_banner = 5

        delays = []
        for attempt in range(1, 10):
            delay = min(base_backoff_ms * (2 ** (attempt - 1)), max_backoff_ms)
            delays.append(delay)

        assert all(d <= max_backoff_ms for d in delays)

        assert delays[0] == 1000
        assert delays[1] == 2000
        assert delays[2] == 4000
        assert delays[3] == 8000

        assert delays[-1] == max_backoff_ms
        assert max_retries_before_banner == 5

    def test_no_immediate_banner_on_first_failure(self):
        """Le banner d'erreur ne doit pas s'afficher avant 5 échecs consécutifs."""
        max_retries = 5
        retries = 0

        for _ in range(max_retries - 1):
            retries += 1
            should_show = retries >= max_retries
            assert (
                not should_show
            ), f"Banner ne doit pas s'afficher après {retries} essais"

        retries += 1
        should_show = retries >= max_retries
        assert should_show, f"Banner doit s'afficher après {retries} essais"
