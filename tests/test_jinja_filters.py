from __future__ import annotations

from src.utils.jinja_filters import confidence_badge, format_date_fr, format_score


def test_format_date_fr_iso_zulu() -> None:
    rendered = format_date_fr("2026-04-06T14:37:00Z")
    assert "6 avril 2026" in rendered
    assert "14:37 UTC" in rendered


def test_confidence_badge_green_and_muted() -> None:
    assert "badge--green" in confidence_badge(0.82)
    assert "badge--muted" in confidence_badge(None)


def test_format_score_units() -> None:
    assert format_score(10, "days") == "10 j"
    assert format_score(1000000, "XOF").endswith(" XOF")
