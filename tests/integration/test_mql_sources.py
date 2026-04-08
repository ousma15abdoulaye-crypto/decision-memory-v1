"""INV-A04 — MQL source attribution tests (Locking test 16).

Verifies that every MQL template query produces source attribution.
"""

from __future__ import annotations

from src.mql.templates import MQL_TEMPLATES


class TestMQLSourceAttribution:
    """INV-A04 : chaque résultat MQL doit lister ses sources."""

    def test_all_templates_join_campaigns(self):
        for key, tpl in MQL_TEMPLATES.items():
            sql = tpl["sql"].lower()
            assert (
                "survey_campaigns" in sql
            ), f"{key}: doit joindre survey_campaigns pour la source attribution"

    def test_all_templates_expose_source_fields(self):
        for key, tpl in MQL_TEMPLATES.items():
            sql = tpl["sql"].lower()
            has_source_type = "source_type" in sql
            has_is_official = "is_official" in sql
            assert (
                has_source_type or has_is_official
            ), f"{key}: doit exposer source_type ou is_official"

    def test_confidence_zero_for_empty(self):
        from src.mql.engine import _compute_mql_confidence

        assert _compute_mql_confidence([], []) == 0.0

    def test_official_source_boosts_confidence(self):
        from datetime import date

        from src.mql.engine import MQLSource, _compute_mql_confidence

        rows = [{"x": 1}] * 5
        sources = [
            MQLSource("DNCC", "mercurial_officiel", "DNCC", date(2026, 1, 1), True)
        ]
        conf = _compute_mql_confidence(rows, sources)
        assert conf >= 0.5, "Source officielle doit donner un bonus"
