"""Pilote terrain — matching par ids (env), sans DB pour la résolution email."""

import pytest

from src.core.config import get_settings
from src.couche_a.auth.dependencies import UserClaims
from src.couche_a.auth.pilot_access import (
    is_pilot_terrain_user_claims,
    is_pilot_terrain_user_id,
    pilot_terrain_allowed_user_ids,
)


@pytest.fixture(autouse=True)
def _pilot_env_cleanup(monkeypatch):
    yield
    for key in (
        "DMS_PILOT_TERRAIN_FULL_ACCESS",
        "DMS_PILOT_USER_IDS",
        "DMS_PILOT_USER_EMAILS",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()


def test_pilot_disabled_when_flag_off(monkeypatch):
    monkeypatch.setenv("DMS_PILOT_TERRAIN_FULL_ACCESS", "false")
    monkeypatch.setenv("DMS_PILOT_USER_IDS", "1,2,3")
    get_settings.cache_clear()
    assert not is_pilot_terrain_user_id(1)


def test_pilot_flag_on_empty_lists_denies_everyone(monkeypatch):
    monkeypatch.setenv("DMS_PILOT_TERRAIN_FULL_ACCESS", "true")
    monkeypatch.setenv("DMS_PILOT_USER_IDS", "")
    monkeypatch.setenv("DMS_PILOT_USER_EMAILS", "")
    get_settings.cache_clear()
    assert pilot_terrain_allowed_user_ids() == set()
    assert not is_pilot_terrain_user_id(99)


def test_pilot_ids_csv(monkeypatch):
    monkeypatch.setenv("DMS_PILOT_TERRAIN_FULL_ACCESS", "1")
    monkeypatch.setenv("DMS_PILOT_USER_IDS", "7; 8, 9")
    monkeypatch.setenv("DMS_PILOT_USER_EMAILS", "")
    get_settings.cache_clear()
    assert is_pilot_terrain_user_id(7)
    assert is_pilot_terrain_user_id(8)
    assert is_pilot_terrain_user_id(9)
    assert not is_pilot_terrain_user_id(10)


def test_is_pilot_terrain_user_claims(monkeypatch):
    monkeypatch.setenv("DMS_PILOT_TERRAIN_FULL_ACCESS", "true")
    monkeypatch.setenv("DMS_PILOT_USER_IDS", "42")
    get_settings.cache_clear()
    ok = UserClaims(user_id="42", role="viewer", jti="jti", tenant_id=None)
    bad = UserClaims(user_id="43", role="viewer", jti="jti", tenant_id=None)
    assert is_pilot_terrain_user_claims(ok)
    assert not is_pilot_terrain_user_claims(bad)
