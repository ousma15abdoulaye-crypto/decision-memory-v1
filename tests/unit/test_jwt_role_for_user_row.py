"""jwt_role_for_user_row — superuser → admin JWT (bypass workspace)."""

from __future__ import annotations

from src.api.auth_helpers import jwt_role_for_user_row


def test_superuser_gets_admin_regardless_of_role_name() -> None:
    assert (
        jwt_role_for_user_row(
            {
                "is_superuser": True,
                "role_name": "supply_chain",
            }
        )
        == "admin"
    )


def test_non_superuser_maps_role_name() -> None:
    assert jwt_role_for_user_row(
        {"is_superuser": False, "role_name": "supply_chain"}
    ) == ("supply_chain")
    assert (
        jwt_role_for_user_row({"is_superuser": False, "role_name": "admin"}) == "admin"
    )


def test_unknown_role_defaults_to_viewer() -> None:
    assert jwt_role_for_user_row(
        {"is_superuser": False, "role_name": "unknown_role"}
    ) == ("viewer")
