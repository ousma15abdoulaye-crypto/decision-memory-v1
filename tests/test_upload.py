"""
Tests d'intégration pour les endpoints d'upload.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

# Import only when DATABASE_URL is set (main.py requires it at load time)
if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set – skipping upload integration tests",
        allow_module_level=True,
    )

from main import app
from src.db import db_execute, db_execute_one, get_connection

client = TestClient(app)


@pytest.fixture
def test_case():
    """Crée un cas de test et retourne son ID."""
    case_id = "9999"
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO cases (id, case_type, title, lot, created_at, status)
            VALUES (:id, 'test', 'Cas de test upload', NULL, :ts, 'open')
            ON CONFLICT(id) DO NOTHING
            """,
            {"id": case_id, "ts": now},
        )
    yield case_id
    # Nettoyage après tests
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM artifacts WHERE case_id=:cid", {"cid": case_id})
        db_execute(conn, "DELETE FROM cases WHERE id=:id", {"id": case_id})


@pytest.fixture
def sample_pdf():
    """Génère un faux fichier PDF pour les tests."""
    content = b"%PDF-1.4 fake content"
    return ("test.pdf", content, "application/pdf")


def test_upload_dao_ok(test_case, sample_pdf):
    """Test nominal : upload DAO réussi."""
    filename, content, mime = sample_pdf
    response = client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifact_id" in data
    assert data["status"] == "uploaded"

    # Vérifier en base
    art = db_execute_one(
        "SELECT * FROM artifacts WHERE case_id=:cid AND kind='dao'",
        {"cid": test_case},
    )
    assert art is not None
    assert art["filename"] == filename


def test_upload_dao_duplicate(test_case, sample_pdf):
    """Test : second upload DAO → 409 Conflict."""
    filename, content, mime = sample_pdf
    # Premier upload OK
    client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": (filename, content, mime)},
    )
    # Deuxième upload → 409
    response = client.post(
        f"/api/cases/{test_case}/upload-dao",
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 409
    assert "already uploaded" in response.text


def test_upload_offer_ok(test_case, sample_pdf):
    """Test nominal : upload offre technique."""
    filename, content, mime = sample_pdf
    response = client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Fournisseur Test", "offer_type": "technique"},
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["supplier_name"] == "Fournisseur Test"
    assert data["offer_type"] == "technique"

    # Vérifier métadonnées en base
    art = db_execute_one(
        "SELECT meta_json FROM artifacts WHERE case_id=:cid AND kind='offer'",
        {"cid": test_case},
    )
    assert art is not None
    meta = json.loads(art["meta_json"])
    assert meta["supplier_name"] == "Fournisseur Test"
    assert meta["offer_type"] == "technique"


def test_upload_offer_duplicate_supplier_type(test_case, sample_pdf):
    """Test : même fournisseur + même type → 409."""
    filename, content, mime = sample_pdf
    # Premier upload
    client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Doublon Test", "offer_type": "financiere"},
        files={"file": (filename, content, mime)},
    )
    # Deuxième upload identique → 409
    response = client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Doublon Test", "offer_type": "financiere"},
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 409
    assert "déjà uploadée" in response.text


def test_upload_offer_invalid_type(test_case, sample_pdf):
    """Test : type offre non autorisé → 422 (validation FastAPI)."""
    filename, content, mime = sample_pdf
    response = client.post(
        f"/api/cases/{test_case}/upload-offer",
        data={"supplier_name": "Test", "offer_type": "invalide"},
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 422  # Validation error
