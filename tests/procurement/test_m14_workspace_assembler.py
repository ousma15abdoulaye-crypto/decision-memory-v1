"""Tests M-CTO-V53-D — assembleur offers[] pour M14."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.procurement.m14_workspace_assembler import build_m14_offers_for_workspace


def test_prefers_offer_extractions() -> None:
    conn = MagicMock()
    calls = {"n": 0}

    def fake_fetchall(c, sql, params):
        calls["n"] += 1
        if "offer_extractions" in sql:
            return [
                {
                    "bundle_id": "b1",
                    "supplier_name": "ACME",
                    "extracted_data_json": {},
                }
            ]
        return []

    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=fake_fetchall,
    ):
        out = build_m14_offers_for_workspace(conn, "ws-uuid")

    assert len(out) == 1
    assert out[0]["document_id"] == "b1"
    assert out[0]["supplier_name"] == "ACME"
    assert calls["n"] == 1


def test_fallback_supplier_bundles() -> None:
    conn = MagicMock()

    def fake_fetchall(c, sql, params):
        if "offer_extractions" in sql:
            return []
        return [
            {"bundle_id": "u1", "supplier_name": "Vendor Raw"},
        ]

    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=fake_fetchall,
    ):
        out = build_m14_offers_for_workspace(conn, "ws-uuid")

    assert len(out) == 1
    assert out[0]["document_id"] == "u1"
    assert out[0]["supplier_name"] == "Vendor Raw"
