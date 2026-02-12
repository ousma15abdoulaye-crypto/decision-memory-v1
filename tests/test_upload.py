"""
Tests d'intégration pour les endpoints d'upload (Manuel SCI §4).
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Skip if DATABASE_URL not set (main.py requires it at load time)
if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set – skipping upload integration tests",
        allow_module_level=True,
    )

from main import app

client = TestClient(app)


@pytest.fixture
def test_case():
    """Crée un cas via l'API et retourne son ID."""
    response = client.post(
        "/api/cases",
        json={
            "case_type": "RFQ",
            "title": "Test Upload Endpoints",
            "lot": None,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_upload_dao_success(test_case):
    """Upload DAO nominal."""
    response = client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifact_id" in data
    assert data["status"] == "uploaded"


def test_upload_dao_duplicate(test_case):
    """Second upload DAO → 409."""
    client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": ("dao1.pdf", b"%PDF-1.4", "application/pdf")},
    )
    response = client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": ("dao2.pdf", b"%PDF-1.5", "application/pdf")},
    )
    assert response.status_code == 409


def test_upload_offer_requires_dao(test_case):
    """Upload offre sans DAO → 400."""
    # Create a NEW case (different from test_case) - no DAO uploaded
    response = client.post(
        "/api/cases",
        json={
            "case_type": "RFQ",
            "title": "No DAO",
            "lot": None,
        },
    )
    assert response.status_code == 200
    case_without_dao = response.json()["id"]
    response = client.post(
        f"/api/cases/{case_without_dao}/upload-offer",
        data={"supplier_name": "Test Supplier", "offer_type": "technique"},
        files={"file": ("offer.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400
    assert "before DAO" in response.text


def test_upload_offer_success(test_case):
    """Upload offre nominal."""
    # d'abord upload DAO
    client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4", "application/pdf")},
    )
    # upload offre technique
    response = client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Supplier A", "offer_type": "technique"},
        files={"file": ("tech.pdf", b"%PDF-1.4 technical", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["supplier_name"] == "Supplier A"
    assert data["offer_type"] == "technique"


def test_upload_offer_duplicate_supplier_type(test_case):
    """Même fournisseur + même type → 409."""
    # DAO
    client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4", "application/pdf")},
    )
    # première offre
    client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Duplicate", "offer_type": "financiere"},
        files={"file": ("fin1.pdf", b"%PDF-1.4", "application/pdf")},
    )
    # deuxième offre identique
    response = client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Duplicate", "offer_type": "financiere"},
        files={"file": ("fin2.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 409
