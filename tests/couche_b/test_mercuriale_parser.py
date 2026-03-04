"""
Tests ingest_parser + importer mock — RÈGLE-21 : zéro appel API
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.couche_b.mercuriale.importer import import_mercuriale
from src.couche_b.mercuriale.ingest_parser import (
    _clean_price,
    _extract_zone_from_header,
    parse_markdown_to_lines,
)
from src.couche_b.mercuriale.models import MercurialLineCreate

MARKDOWN_SAMPLE = """
Prix TTC, Kayes, 2024

**1. Fournitures de bureau**

| 1.3 | Abonnement au journal ESSOR | Abonnement annuel | 70 000 | 77 500 | 85 000 |
| 1.15 | Agrafe 23/10 | Paquet 10 | 5 000 | 5 500 | 6 000 |
| 1.16 | Agrafe 23/16 | Paquet 10 | 7 500 | 7 875 | 8 250 |
"""


class TestCleanPrice:
    def test_prix_avec_espaces(self):
        assert float(_clean_price("77 500")) == 77500.0

    def test_prix_sans_espace(self):
        assert float(_clean_price("18500")) == 18500.0

    def test_zero_refuse(self):
        assert _clean_price("0") is None

    def test_na_refuse(self):
        assert _clean_price("N/A") is None

    def test_vide_refuse(self):
        assert _clean_price("") is None

    def test_negatif_refuse(self):
        assert _clean_price("-500") is None


class TestZoneExtraction:
    def test_kayes_2024(self):
        assert _extract_zone_from_header("Prix TTC, Kayes, 2024") == "Kayes"

    def test_mopti_2023(self):
        assert _extract_zone_from_header("Prix TTC, Mopti, 2023") == "Mopti"

    def test_absent(self):
        assert _extract_zone_from_header("Codes | DESIGNATIONS | Unité") is None


class TestParseMarkdown:
    def test_lignes_extraites(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        assert len(lines) >= 2, f"Attendu ≥ 2 · obtenu {len(lines)}"

    def test_zone_detectee(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        assert lines[0]["zone_raw"] == "Kayes"

    def test_prix_corrects_essor(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        essor = next(row for row in lines if "ESSOR" in row["item_canonical"])
        assert float(essor["price_min"]) == 70000.0
        assert float(essor["price_avg"]) == 77500.0
        assert float(essor["price_max"]) == 85000.0

    def test_group_label_detecte(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        assert lines[0]["group_label"] is not None
        assert "Fournitures" in lines[0]["group_label"]

    def test_annee_correcte(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        assert all(row["year"] == 2024 for row in lines)

    def test_confidence_dans_bornes(self):
        lines = parse_markdown_to_lines(MARKDOWN_SAMPLE, 2024)
        for line in lines:
            assert 0.0 <= line["confidence"] <= 1.0

    def test_markdown_vide_retourne_liste_vide(self):
        assert parse_markdown_to_lines("", 2024) == []

    def test_zone_default_si_non_detectee(self):
        md = "| 1.1 | Riz | Sac | 17000 | 18500 | 20000 |"
        lines = parse_markdown_to_lines(md, 2024, default_zone_raw="Bamako")
        assert lines[0]["zone_raw"] == "Bamako"


class TestModeleUnitPrice:
    def test_unit_price_egal_price_avg(self):
        """unit_price doit être automatiquement égal à price_avg."""
        line = MercurialLineCreate(
            source_id=uuid.uuid4(),
            item_canonical="Riz blanc 25kg",
            price_min=Decimal("17000"),
            price_avg=Decimal("18500"),
            price_max=Decimal("20000"),
            year=2024,
        )
        assert line.unit_price == Decimal("18500")

    def test_price_order_violation_flag(self):
        """Si price_min > price_avg → review_required + metadata flag."""
        line = MercurialLineCreate(
            source_id=uuid.uuid4(),
            item_canonical="Article test",
            price_min=Decimal("20000"),
            price_avg=Decimal("15000"),
            price_max=Decimal("25000"),
            year=2024,
        )
        assert line.review_required is True
        assert line.extraction_metadata.get("price_order_violation") is True

    def test_low_confidence_flag(self):
        """Confidence < 0.80 → review_required."""
        line = MercurialLineCreate(
            source_id=uuid.uuid4(),
            item_canonical="Article confiance faible",
            price_min=Decimal("5000"),
            price_avg=Decimal("5500"),
            price_max=Decimal("6000"),
            year=2024,
            confidence=0.65,
        )
        assert line.review_required is True


class TestImporterMock:
    """RÈGLE-21 : zéro appel LlamaCloud réel · mock obligatoire."""

    MOCK_MARKDOWN = (
        "Prix TTC, Kayes, 2024\n"
        "**1. Fournitures**\n"
        "| 1.3 | Riz blanc 25kg | Sac | 17 000 | 18 500 | 20 000 |\n"
        "| 1.15 | Agrafe 23/10 | Paquet 10 | 5 000 | 5 500 | 6 000 |\n"
    )

    def test_dry_run_sans_appel_api(self, tmp_path, monkeypatch):
        """Dry-run complet · zéro appel réseau · rapport valide."""
        monkeypatch.setenv("LLAMADMS", "test_key_mock")
        fake_pdf = tmp_path / "mercuriale_2024.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch(
            "src.couche_b.mercuriale.importer._extract_markdown_llamacloud",
            return_value=(self.MOCK_MARKDOWN, 0.90),
        ):
            report = import_mercuriale(
                filepath=fake_pdf,
                year=2024,
                dry_run=True,
            )

        assert report.dry_run is True
        assert report.inserted >= 1
        assert report.already_imported is False
        assert len(report.errors) == 0
        assert report.coverage_pct > 0

    def test_cle_absente_leve_erreur(self, tmp_path, monkeypatch):
        """Sans clé API → RuntimeError immédiat."""
        monkeypatch.delenv("LLAMADMS", raising=False)
        monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake")

        with pytest.raises(RuntimeError, match="Clé API absente"):
            import_mercuriale(filepath=fake_pdf, year=2024)

    def test_extraction_echouee_retourne_erreur(self, tmp_path, monkeypatch):
        """Extraction retourne une exception → erreur dans rapport."""
        monkeypatch.setenv("LLAMADMS", "test_key")
        fake_pdf = tmp_path / "vide.pdf"
        fake_pdf.write_bytes(b"fake")

        with patch(
            "src.couche_b.mercuriale.importer._extract_markdown_llamacloud",
            side_effect=ValueError("LlamaCloud : markdown_full vide"),
        ):
            report = import_mercuriale(
                filepath=fake_pdf,
                year=2024,
                dry_run=True,
            )

        assert len(report.errors) > 0
        assert report.inserted == 0
