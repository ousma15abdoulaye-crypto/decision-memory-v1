"""Tests IMC parser — RÈGLE-21 : fixtures statiques."""

from pathlib import Path

import pytest

from src.couche_b.imc.parser import _parse_filename_period, parse_imc_pdf


class TestParseFilenamePeriod:
    def test_aout18(self):
        assert _parse_filename_period("AOUT18.pdf") == (2018, 8)

    def test_jan26(self):
        assert _parse_filename_period("JAN26.pdf") == (2026, 1)

    def test_dec25(self):
        assert _parse_filename_period("DEC25.pdf") == (2025, 12)

    def test_avril18(self):
        assert _parse_filename_period("AVRIL18.pdf") == (2018, 4)

    def test_av25(self):
        assert _parse_filename_period("AV25.pdf") == (2025, 4)


class TestParseImcPdf:
    @pytest.fixture
    def sample_pdf(self):
        p = Path("data/imports/imc/AOUT18.pdf")
        if not p.exists():
            pytest.skip("AOUT18.pdf absent")
        return p

    def test_parse_returns_entries(self, sample_pdf):
        entries = parse_imc_pdf(sample_pdf)
        assert len(entries) >= 5
        assert all("category_raw" in e for e in entries)
        assert all("period_year" in e for e in entries)
        assert all("period_month" in e for e in entries)
        assert all(e["period_year"] == 2018 for e in entries)
        assert all(e["period_month"] == 8 for e in entries)
