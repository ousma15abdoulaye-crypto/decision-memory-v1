"""Tests correction d'horloge HTTP pour SigV4 S3/R2."""

from __future__ import annotations

import datetime

import botocore.auth as auth_mod
import pytest
from s3_clock_skew import (
    auto_botocore_clock_skew_from_http,
    botocore_clock_skew_context,
)


def _sigv4_reference_now() -> datetime.datetime:
    """Même référence temps que SigV4 dans botocore (ancien ou récent)."""
    if hasattr(auth_mod, "get_current_datetime"):
        return auth_mod.get_current_datetime()
    return auth_mod.datetime.datetime.utcnow()


class TestBotocoreClockSkewContext:
    def test_adds_skew_seconds_to_get_current_datetime(self) -> None:
        # SigV4 lit l’heure via botocore.auth (get_current_datetime ou utcnow selon version).
        t_before = _sigv4_reference_now()
        with botocore_clock_skew_context(100.0):
            t_inside = _sigv4_reference_now()
        t_after = _sigv4_reference_now()

        assert (t_inside - t_before).total_seconds() == pytest.approx(100.0, abs=2.0)
        assert abs((t_after - t_before).total_seconds()) < 2.0


class TestAutoBotocoreClockSkew:
    def test_disabled_skips_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("S3_CLOCK_SKEW_AUTO", "0")
        called: list[int] = []

        def boom() -> float:
            called.append(1)
            return 0.0

        monkeypatch.setattr("s3_clock_skew.get_http_clock_skew_seconds", boom)
        with auto_botocore_clock_skew_from_http():
            pass
        assert called == []
