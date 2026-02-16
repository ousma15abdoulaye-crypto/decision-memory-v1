"""
Tests d'intégration pour les endpoints d'upload (Manuel SCI §4).
"""

import os

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


def get_token(username: str = "admin", password: str = "admin123") -> str:
    """Helper login – retourne le token JWT."""
    response = client.post(
        "/auth/token", data={"username": username, "password": password}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.json()}")
    return response.json()["access_token"]


@pytest.fixture
def test_case():
    """Crée un cas via l'API et retourne (case_id, token)."""
    token = get_token()
    response = client.post(
        "/api/cases",
        json={
            "case_type": "RFQ",
            "title": "Test Upload Endpoints",
            "lot": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"Failed to create case: {response.text}"
    return response.json()["id"], token


def test_upload_dao_success(test_case):
    """Upload DAO nominal."""
    case_id, token = test_case
    response = client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifact_id" in data
    assert data["status"] == "uploaded"


def test_upload_dao_duplicate(test_case):
    """Second upload DAO → 409."""
    case_id, token = test_case
    client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao1.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao2.pdf", b"%PDF-1.5", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


def test_upload_offer_requires_dao(test_case):
    """Upload offre sans DAO → 400."""
    case_id, token = test_case
    # Créer un cas sans DAO (l'API génère l'id, on utilise le cas retourné)
    response = client.post(
        "/api/cases",
        json={
            "case_type": "RFQ",
            "title": "No DAO",
            "lot": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    case_no_dao = response.json()["id"]
    response = client.post(
        f"/api/cases/{case_no_dao}/upload-offer",
        data={"supplier_name": "Test Supplier", "offer_type": "technique"},
        files={"file": ("offer.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "before DAO" in response.text


def test_upload_offer_success(test_case):
    """Upload offre nominal."""
    case_id, token = test_case
    client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.post(
        f"/api/cases/{case_id}/upload-offer",
        data={"supplier_name": "Supplier A", "offer_type": "technique"},
        files={"file": ("tech.pdf", b"%PDF-1.4 technical", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["supplier_name"] == "Supplier A"
    assert data["offer_type"] == "technique"


def test_upload_offer_duplicate_supplier_type(test_case):
    """Même fournisseur + même type → 409."""
    case_id, token = test_case
    client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/api/cases/{case_id}/upload-offer",
        data={"supplier_name": "Duplicate", "offer_type": "financiere"},
        files={"file": ("fin1.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.post(
        f"/api/cases/{case_id}/upload-offer",
        data={"supplier_name": "Duplicate", "offer_type": "financiere"},
        files={"file": ("fin2.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


@pytest.mark.skip(reason="Table lots not yet implemented - planned for M3A")
def test_upload_offer_with_lot_id(test_case):
    """Upload offre avec lot_id – validation du lot."""
    case_id, token = test_case
    from src.db import get_connection, db_execute

    # Créer un lot pour le case
    lot_id = "test-lot-123"
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO lots (id, case_id, lot_number, description, estimated_value, created_at)
            VALUES (:id, :cid, :num, :desc, :val, :ts)
        """,
            {
                "id": lot_id,
                "cid": case_id,
                "num": "LOT-TEST-01",
                "desc": "Test Lot",
                "val": 10000,
                "ts": "2026-02-12T00:00:00",
            },
        )

    # Upload DAO first
    client.post(
        f"/api/cases/{case_id}/upload-dao",
        files={"file": ("dao.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Upload offre avec lot_id valide
    response = client.post(
        f"/api/cases/{case_id}/upload-offer",
        data={
            "supplier_name": "Supplier With Lot",
            "offer_type": "technique",
            "lot_id": lot_id,
        },
        files={"file": ("tech.pdf", b"%PDF-1.4 technical", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lot_id"] == lot_id
    assert "is_late" in data

    # Upload offre avec lot_id invalide
    response = client.post(
        f"/api/cases/{case_id}/upload-offer",
        data={
            "supplier_name": "Supplier Bad Lot",
            "offer_type": "financiere",
            "lot_id": "nonexistent",
        },
        files={"file": ("fin.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.text.lower()

    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM lots WHERE id=:id", {"id": lot_id})
