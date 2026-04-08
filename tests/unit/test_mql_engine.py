"""Tests MQL Engine V8 — Canon V5.1.0 Section 8.

Tests couvrant :
- templates.py : 6 templates, MQLParams dataclass
- param_extractor.py : extraction déterministe zones, articles, prix, dates
- template_selector.py : sélection correcte T1-T6
- engine.py : MQLResult, confidence, source attribution (INV-A04)
"""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

TENANT = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


class TestMQLTemplates:
    """Vérifie les 6 templates T1-T6 présents et bien formés."""

    def test_six_templates_exist(self):
        from src.mql.templates import MQL_TEMPLATES

        assert len(MQL_TEMPLATES) == 6
        expected = {
            "T1_PRICE_MEDIAN",
            "T2_PRICE_TREND",
            "T3_VENDOR_HISTORY",
            "T4_ZONE_COMPARISON",
            "T5_ANOMALY_DETECTION",
            "T6_CAMPAIGN_INVENTORY",
        }
        assert set(MQL_TEMPLATES.keys()) == expected

    def test_each_template_has_sql_and_name(self):
        from src.mql.templates import MQL_TEMPLATES

        for key, tpl in MQL_TEMPLATES.items():
            assert "sql" in tpl, f"{key} manque 'sql'"
            assert "name" in tpl, f"{key} manque 'name'"
            assert ":tenant_id" in tpl["sql"], f"{key} doit filtrer par tenant_id"

    def test_no_sql_concatenation(self):
        """INV-A02 : zéro concaténation SQL — uniquement des bind params."""
        from src.mql.templates import MQL_TEMPLATES

        for key, tpl in MQL_TEMPLATES.items():
            sql = tpl["sql"]
            assert "f'" not in sql, f"{key} contient f-string"
            assert '".format' not in sql, f"{key} contient .format()"
            assert "% " not in sql or "PERCENTILE" in sql, f"{key} contient %"

    def test_mql_params_default_max_results(self):
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT)
        assert p.max_results == 50


class TestParamExtractor:
    """Tests param_extractor.py — extraction déterministe."""

    def test_extract_zone_bamako(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("prix du riz à Bamako", TENANT)
        )
        assert p.zones is not None
        assert "Bamako" in p.zones

    def test_extract_multiple_zones(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("comparaison Bamako et Mopti", TENANT)
        )
        assert p.zones is not None
        assert len(p.zones) >= 2

    def test_extract_year(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("prix ciment 2026", TENANT)
        )
        assert p.min_date == date(2026, 1, 1)

    def test_extract_price_xof(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("ciment à 5000 FCFA", TENANT)
        )
        assert p.proposed_price == 5000.0

    def test_extract_vendor(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("fournisseur Alpha", TENANT)
        )
        assert p.vendor_pattern == "alpha"

    def test_extract_article_filters_stopwords(self):
        from src.mql.param_extractor import _extract_article

        result = _extract_article("quel est le prix médian du ciment")
        assert "ciment" in result
        assert "quel" not in result
        assert "prix" not in result

    def test_extract_quarter(self):
        from src.mql.param_extractor import extract_mql_params

        p = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("tendance T2 2026 riz", TENANT)
        )
        assert p.start_date == date(2026, 4, 1)
        assert p.end_date == date(2026, 7, 1)


class TestTemplateSelector:
    """Tests template_selector.py — sélection déterministe T1-T6."""

    def test_campaign_inventory(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT)
        r = asyncio.get_event_loop().run_until_complete(
            select_template("quelles sources disponibles ?", p)
        )
        assert r == "T6_CAMPAIGN_INVENTORY"

    def test_anomaly_detection_with_price(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT, proposed_price=5000.0)
        r = asyncio.get_event_loop().run_until_complete(
            select_template("ciment à 5000 FCFA", p)
        )
        assert r == "T5_ANOMALY_DETECTION"

    def test_vendor_history(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT, vendor_pattern="alpha")
        r = asyncio.get_event_loop().run_until_complete(
            select_template("historique fournisseur alpha", p)
        )
        assert r == "T3_VENDOR_HISTORY"

    def test_price_trend(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT)
        r = asyncio.get_event_loop().run_until_complete(
            select_template("tendance du prix du riz", p)
        )
        assert r == "T2_PRICE_TREND"

    def test_zone_comparison(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT, zones=["Bamako", "Mopti"])
        r = asyncio.get_event_loop().run_until_complete(
            select_template("prix du ciment", p)
        )
        assert r == "T4_ZONE_COMPARISON"

    def test_default_price_median(self):
        from src.mql.template_selector import select_template
        from src.mql.templates import MQLParams

        p = MQLParams(tenant_id=TENANT)
        r = asyncio.get_event_loop().run_until_complete(
            select_template("prix du riz Bamako", p)
        )
        assert r == "T1_PRICE_MEDIAN"


class TestMQLConfidence:
    """Tests engine._compute_mql_confidence — INV-A04."""

    def test_empty_rows_zero_confidence(self):
        from src.mql.engine import _compute_mql_confidence

        assert _compute_mql_confidence([], []) == 0.0

    def test_official_source_bonus(self):
        from src.mql.engine import MQLSource, _compute_mql_confidence

        rows = [{"x": 1}] * 10
        sources = [
            MQLSource("S1", "mercurial_officiel", "DNCC", date(2026, 1, 1), True)
        ]
        c = _compute_mql_confidence(rows, sources)
        assert c >= 0.5, "Source officielle donne un bonus"

    def test_multi_source_bonus(self):
        from src.mql.engine import MQLSource, _compute_mql_confidence

        rows = [{"x": 1}] * 20
        sources = [
            MQLSource("S1", "mercurial_officiel", "DNCC", date(2026, 1, 1), True),
            MQLSource("S2", "enquete_terrain", "ONG", date(2026, 2, 1), False),
        ]
        c = _compute_mql_confidence(rows, sources)
        assert c == 1.0, "20 rows + officiel + multi-source = confiance max"

    def test_few_rows_low_confidence(self):
        from src.mql.engine import _compute_mql_confidence

        rows = [{"x": 1}]
        c = _compute_mql_confidence(rows, [])
        assert c < 0.5, "Peu de données = faible confiance"
