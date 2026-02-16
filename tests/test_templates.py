"""
Tests unitaires pour les générateurs de templates.
"""

import pytest
from datetime import datetime
from src.templates.cba_template import generate_cba_excel
from src.templates.pv_template import generate_pv_ouverture, generate_pv_analyse


@pytest.fixture
def case_data_fixture():
    """Données de test conformes au Manuel SCI."""
    return {
        "case_reference": "RFQ-2026-001",
        "market_title": "Fournitures de bureau",
        "dao_ref": "RFQ-2026-001",
        "opening_date": datetime(2026, 2, 11, 10, 30),
        "deadline": datetime(2026, 2, 10, 12, 0),
        "location": "Bamako, Mali",
        "lot": "Lot unique",
        "invited_suppliers": ["Fournisseur A", "Fournisseur B", "Fournisseur C"],
        "suppliers": [
            {
                "supplier_name": "Fournisseur A",
                "timestamp": datetime(2026, 2, 10, 9, 15),
                "mode_depot": "Email",
                "docs_count": 5,
                "has_sample": True,
                "extracted_data": {
                    "technique": {"capacite_technique": 45, "durabilite": 8},
                    "financiere": {
                        "montant_ht": 12500000,
                        "tva": 18,
                        "delai_jours": 45,
                    },
                },
            },
            {
                "supplier_name": "Fournisseur B",
                "timestamp": datetime(2026, 2, 10, 10, 45),
                "mode_depot": "Mali Tender",
                "docs_count": 4,
                "has_sample": False,
                "extracted_data": {
                    "technique": {"capacite_technique": 40, "durabilite": 7},
                    "financiere": {
                        "montant_ht": 13150000,
                        "tva": 18,
                        "delai_jours": 50,
                    },
                },
            },
            {
                "supplier_name": "Fournisseur C",
                "timestamp": datetime(2026, 2, 9, 14, 20),
                "mode_depot": "Physique",
                "docs_count": 5,
                "has_sample": True,
                "extracted_data": {
                    "technique": {"capacite_technique": 48, "durabilite": 9},
                    "financiere": {
                        "montant_ht": 11800000,
                        "tva": 18,
                        "delai_jours": 40,
                    },
                },
            },
        ],
        "technical_criteria": [
            {"name": "Capacité technique", "weight": 50},
            {"name": "Durabilité", "weight": 10},
        ],
    }


@pytest.fixture
def cba_summary_fixture():
    """Résumé CBA pour PV Analyse."""
    return {
        "classement": [
            {
                "supplier_name": "Fournisseur C",
                "technical_score": 96,
                "sustainability_score": 9,
                "commercial_score": 38,
                "final_score": 87.2,
                "rank": 1,
            },
            {
                "supplier_name": "Fournisseur A",
                "technical_score": 90,
                "sustainability_score": 8,
                "commercial_score": 34,
                "final_score": 82.0,
                "rank": 2,
            },
            {
                "supplier_name": "Fournisseur B",
                "technical_score": 80,
                "sustainability_score": 7,
                "commercial_score": 32,
                "final_score": 75.5,
                "rank": 3,
            },
        ]
    }


def test_generate_cba_creates_file(case_data_fixture, tmp_path):
    """Vérifie que le fichier Excel est généré sans erreur."""
    output = generate_cba_excel(case_data_fixture, tmp_path)
    assert output.exists()
    assert output.suffix == ".xlsx"
    assert "CBA" in output.name


def test_generate_cba_has_5_sheets(case_data_fixture, tmp_path):
    """Vérifie la présence des 5 onglets requis."""
    output = generate_cba_excel(case_data_fixture, tmp_path)
    import openpyxl

    wb = openpyxl.load_workbook(output)
    expected_sheets = [
        "Info Générales",
        "Registre Dépôt",
        "Analyse Technique",
        "Analyse Financière",
        "Synthèse",
    ]
    assert set(wb.sheetnames) == set(expected_sheets)


def test_generate_pv_ouverture_creates_file(case_data_fixture, tmp_path):
    """Vérifie que le PV Ouverture Word est généré."""
    output = generate_pv_ouverture(case_data_fixture, tmp_path)
    assert output.exists()
    assert output.suffix == ".docx"
    assert "Ouverture" in output.name


def test_generate_pv_analyse_creates_file(
    case_data_fixture, cba_summary_fixture, tmp_path
):
    """Vérifie que le PV Analyse Word est généré."""
    output = generate_pv_analyse(case_data_fixture, cba_summary_fixture, tmp_path)
    assert output.exists()
    assert output.suffix == ".docx"
    assert "Analyse" in output.name
