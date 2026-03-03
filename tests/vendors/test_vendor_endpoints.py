"""
Tests endpoints GET /vendors — M4.
Prouve que les routes sont opérationnelles et correctement filtrées.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.vendors.repository import insert_vendor

client = TestClient(app)

# Données de test insérées / nettoyées par fixture
_TEST_VENDORS = [
    {
        "name_raw": "Test Vendor BKO Alpha",
        "name_normalized": "test vendor bko alpha",
        "zone_raw": "BAMAKO",
        "zone_normalized": "bamako",
        "region_code": "BKO",
        "category_raw": "IT",
        "email": "alpha@test.ml",
        "phone": "20000001",
        "email_verified": True,
        "source": "TEST_M4",
    },
    {
        "name_raw": "Test Vendor MPT Beta",
        "name_normalized": "test vendor mpt beta",
        "zone_raw": "MOPTI",
        "zone_normalized": "mopti",
        "region_code": "MPT",
        "category_raw": "Transport",
        "email": None,
        "phone": "20000002",
        "email_verified": False,
        "source": "TEST_M4",
    },
]


@pytest.fixture(scope="module")
def seeded_vendors(db_conn_vendors):
    """Insère les vendors de test et retourne leurs IDs."""
    ids = []
    for v in _TEST_VENDORS:
        vid = insert_vendor(**v)
        if vid:
            ids.append(vid)
    yield ids
    # Nettoyage
    with db_conn_vendors.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'TEST_M4'")


def test_list_vendors_200(seeded_vendors):
    """GET /vendors doit retourner 200 avec une liste non vide."""
    resp = client.get("/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= len(seeded_vendors)


def test_list_vendors_filter_bko(seeded_vendors):
    """GET /vendors?region=BKO doit retourner uniquement des vendors BKO."""
    resp = client.get("/vendors?region=BKO")
    assert resp.status_code == 200
    data = resp.json()
    for v in data:
        assert v["region_code"] == "BKO", f"Vendor hors BKO : {v['vendor_id']}"


def test_get_vendor_valid_id_200(seeded_vendors):
    """GET /vendors/{id_valide} doit retourner 200 et les données correctes."""
    assert seeded_vendors, "Aucun vendor inséré"
    vid = seeded_vendors[0]
    resp = client.get(f"/vendors/{vid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendor_id"] == vid


def test_get_vendor_unknown_id_404():
    """GET /vendors/{id_inexistant} doit retourner 404."""
    resp = client.get("/vendors/DMS-VND-XXX-9999-Z")
    assert resp.status_code == 404


def test_list_vendors_pagination(seeded_vendors):
    """GET /vendors?limit=1 doit retourner au plus 1 élément."""
    resp = client.get("/vendors?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) <= 1
