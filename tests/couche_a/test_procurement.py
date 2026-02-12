"""
Tests des endpoints Procurement – Catégories, Lots, Seuils, Références
"""
import os
import pytest
from httpx import AsyncClient
from main import app
from src.db import get_connection, db_execute, db_execute_one


@pytest.fixture
def test_case_id():
    """Créer un case de test et le nettoyer après."""
    case_id = "test-case-procurement"
    with get_connection() as conn:
        # Nettoyer si existe déjà
        db_execute(conn, "DELETE FROM cases WHERE id=:id", {"id": case_id})
        # Créer le case
        db_execute(conn, """
            INSERT INTO cases (id, case_type, title, created_at, status)
            VALUES (:id, 'DAO', 'Test Procurement Case', :ts, 'draft')
        """, {"id": case_id, "ts": "2026-02-12T00:00:00"})
    
    yield case_id
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM cases WHERE id=:id", {"id": case_id})


@pytest.mark.asyncio
async def test_create_category_success():
    """Test création d'une catégorie – succès."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/procurement/categories", json={
            "code": "IT-EQUIP-001",
            "name": "Équipements informatiques",
            "threshold_usd": 50000,
            "requires_technical_eval": True,
            "min_suppliers": 5
        })
    
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "IT-EQUIP-001"
    assert data["name"] == "Équipements informatiques"
    assert data["threshold_usd"] == 50000
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM procurement_categories WHERE code=:code", {"code": "IT-EQUIP-001"})


@pytest.mark.asyncio
async def test_create_category_duplicate():
    """Test création d'une catégorie – code dupliqué."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    # Créer première catégorie
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO procurement_categories (id, code, name, threshold_usd, requires_technical_eval, min_suppliers, created_at)
            VALUES (:id, :code, :name, :threshold, :req, :min, :ts)
        """, {
            "id": "test-cat-dup",
            "code": "DUP-001",
            "name": "Test Duplicate",
            "threshold": 10000,
            "req": True,
            "min": 3,
            "ts": "2026-02-12T00:00:00"
        })
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/procurement/categories", json={
            "code": "DUP-001",
            "name": "Another Category",
            "threshold_usd": 20000
        })
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM procurement_categories WHERE code=:code", {"code": "DUP-001"})


@pytest.mark.asyncio
async def test_create_lot_success(test_case_id):
    """Test création d'un lot – succès."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/api/procurement/cases/{test_case_id}/lots", json={
            "lot_number": "LOT-01",
            "description": "Lot 1 - Fournitures de bureau",
            "estimated_value": 15000.50
        })
    
    assert response.status_code == 201
    data = response.json()
    assert data["lot_number"] == "LOT-01"
    assert data["case_id"] == test_case_id
    assert data["estimated_value"] == 15000.50
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM lots WHERE case_id=:cid", {"cid": test_case_id})


@pytest.mark.asyncio
async def test_create_lot_case_not_found():
    """Test création d'un lot – case inexistant."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/procurement/cases/nonexistent-case/lots", json={
            "lot_number": "LOT-01",
            "description": "Test"
        })
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_lot_duplicate(test_case_id):
    """Test création d'un lot – lot_number dupliqué."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    # Créer premier lot
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO lots (id, case_id, lot_number, description, estimated_value, created_at)
            VALUES (:id, :cid, :num, :desc, :val, :ts)
        """, {
            "id": "test-lot-dup",
            "cid": test_case_id,
            "num": "LOT-DUP",
            "desc": "Test Duplicate Lot",
            "val": 10000,
            "ts": "2026-02-12T00:00:00"
        })
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/api/procurement/cases/{test_case_id}/lots", json={
            "lot_number": "LOT-DUP",
            "description": "Another lot"
        })
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM lots WHERE case_id=:cid", {"cid": test_case_id})


@pytest.mark.asyncio
async def test_list_thresholds():
    """Test listage des seuils de procédure."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/procurement/thresholds")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # RFQ, RFP, DAO
    assert any(t["procedure_type"] == "RFQ" for t in data)
    assert any(t["procedure_type"] == "RFP" for t in data)
    assert any(t["procedure_type"] == "DAO" for t in data)


@pytest.mark.asyncio
async def test_create_reference_success(test_case_id):
    """Test création d'une référence procurement – succès."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/api/procurement/cases/{test_case_id}/references", json={
            "ref_type": "DAO",
            "year": 2026
        })
    
    assert response.status_code == 201
    data = response.json()
    assert data["ref_type"] == "DAO"
    assert data["year"] == 2026
    assert data["ref_number"].startswith("DAO-2026-")
    assert data["case_id"] == test_case_id
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM procurement_references WHERE case_id=:cid", {"cid": test_case_id})


@pytest.mark.asyncio
async def test_create_reference_duplicate(test_case_id):
    """Test création d'une référence – déjà existante pour ce case."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    # Créer première référence
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO procurement_references (id, case_id, ref_type, ref_number, year, sequence, created_at)
            VALUES (:id, :cid, :type, :num, :year, :seq, :ts)
        """, {
            "id": "test-ref-dup",
            "cid": test_case_id,
            "type": "RFQ",
            "num": "RFQ-2026-999",
            "year": 2026,
            "seq": 999,
            "ts": "2026-02-12T00:00:00"
        })
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/api/procurement/cases/{test_case_id}/references", json={
            "ref_type": "DAO",
            "year": 2026
        })
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    
    # Cleanup
    with get_connection() as conn:
        db_execute(conn, "DELETE FROM procurement_references WHERE case_id=:cid", {"cid": test_case_id})
