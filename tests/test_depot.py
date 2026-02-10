"""Test document depot and dashboard."""
import io
import pytest

from backend.couche_a.models import Case, Lot
from backend.system.db import async_session_factory


async def _create_case_and_lot(case_id: str, lot_id: str):
    """Helper to create Case and Lot records required by foreign keys."""
    async with async_session_factory() as db:
        case = Case(id=case_id, reference=case_id, title="Test", buyer_name="Tester")
        db.add(case)
        await db.flush()
        lot = Lot(id=lot_id, case_id=case_id, number=1, description="Test lot")
        db.add(lot)
        await db.commit()


@pytest.mark.asyncio
async def test_depot_upload(client, admin_headers):
    """Upload a file via depot."""
    await _create_case_and_lot("CASE-001", "LOT-001")
    file_content = b"Sample content for testing"
    resp = await client.post(
        "/api/depot",
        data={"case_id": "CASE-001", "lot_id": "LOT-001", "channel": "upload"},
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "submission_id" in data
    assert data["status"] == "received"


@pytest.mark.asyncio
async def test_dashboard_empty(client, admin_headers):
    """Dashboard returns empty list when no submissions."""
    resp = await client.get("/api/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_dashboard_after_upload(client, admin_headers):
    """Dashboard shows submission after upload."""
    await _create_case_and_lot("CASE-002", "LOT-002")
    file_content = b"Sample content"
    await client.post(
        "/api/depot",
        data={"case_id": "CASE-002", "lot_id": "LOT-002"},
        files={"file": ("doc.txt", io.BytesIO(file_content), "text/plain")},
        headers=admin_headers,
    )
    resp = await client.get("/api/dashboard?case_id=CASE-002", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_offer_detail(client, admin_headers):
    """Get offer detail."""
    await _create_case_and_lot("CASE-003", "LOT-003")
    file_content = b"test content"
    upload_resp = await client.post(
        "/api/depot",
        data={"case_id": "CASE-003", "lot_id": "LOT-003"},
        files={"file": ("doc.txt", io.BytesIO(file_content), "text/plain")},
        headers=admin_headers,
    )
    sub_id = upload_resp.json()["submission_id"]

    resp = await client.get(f"/api/offers/{sub_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["submission"]["id"] == sub_id


@pytest.mark.asyncio
async def test_offer_not_found(client, admin_headers):
    resp = await client.get("/api/offers/nonexistent", headers=admin_headers)
    assert resp.status_code == 404
