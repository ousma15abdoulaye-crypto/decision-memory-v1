"""Tests M6B — canonical fail-closed assembler for M14 offers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.procurement.m14_workspace_assembler import (
    M14OfferReadinessError,
    build_m14_offers_for_workspace,
)


def _payload(**overrides):
    payload = {
        "extraction_ok": True,
        "review_required": False,
        "taxonomy_core": "offer_technical",
        "family_main": "consultance",
        "family_sub": "technical",
        "fields": [
            {
                "name": "methodology",
                "value": "Approche technique",
                "confidence": 0.91,
                "evidence": "Méthodologie proposée",
            },
            {
                "name": "currency",
                "value": "USD",
                "confidence": 0.8,
                "evidence": "Prix en USD",
            },
        ],
        "line_items": [],
    }
    payload.update(overrides)
    return payload


def _row(**overrides):
    row = {
        "id": "extraction-1",
        "bundle_id": "b1",
        "supplier_name": "A - Z SARL",
        "extracted_data_json": json.dumps(_payload()),
        "missing_fields_json": json.dumps(["total_price"]),
        "created_at": "2026-05-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def _fetchall_for(
    rows,
    *,
    dao_rows=None,
    eval_docs=None,
    assessments=None,
    context_rows=None,
    captured_sql=None,
):
    def fake_fetchall(c, sql, params):
        low = sql.lower()
        if captured_sql is not None:
            captured_sql.append(sql)
        if "from dao_criteria" in low:
            return (
                dao_rows if dao_rows is not None else [{"id": "c1", "ponderation": 100}]
            )
        if "from evaluation_documents" in low:
            return eval_docs or []
        if "from offer_extractions" in low:
            return rows
        if "from supplier_bundles" in low:
            return context_rows or [
                {
                    "bundle_id": "b1",
                    "gate_b_role": "scorable",
                    "m12_doc_kind": "offer_combined",
                }
            ]
        if "from criterion_assessments" in low:
            return assessments or []
        raise AssertionError(f"unexpected SQL: {low[:220]!r}")

    return fake_fetchall


def _assert_blocked(rows, expected_blocker: str, **kwargs) -> None:
    conn = MagicMock()
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for(rows, **kwargs),
    ):
        with pytest.raises(M14OfferReadinessError) as exc:
            build_m14_offers_for_workspace(conn, "ws-uuid")
    assert expected_blocker in ";".join(exc.value.blockers)


def test_rejects_empty_extracted_data_json() -> None:
    _assert_blocked(
        [_row(extracted_data_json={})], "extracted_data_json_absent_or_empty"
    )


def test_rejects_invalid_extracted_data_json() -> None:
    _assert_blocked(
        [_row(extracted_data_json="{not-json")], "extracted_data_json_invalid_json"
    )


def test_rejects_extraction_ok_false() -> None:
    _assert_blocked(
        [_row(extracted_data_json=json.dumps(_payload(extraction_ok=False)))],
        "extraction_ok_not_true",
    )


def test_rejects_supplier_name_absent() -> None:
    _assert_blocked([_row(supplier_name="ABSENT")], "supplier_name_absent")


def test_rejects_fields_without_value_confidence_evidence() -> None:
    _assert_blocked(
        [
            _row(
                extracted_data_json=json.dumps(
                    _payload(fields=[{"name": "methodology", "value": "x"}])
                )
            )
        ],
        "field_0_missing_confidence_evidence",
    )


def test_rejects_fields_with_blank_name() -> None:
    _assert_blocked(
        [
            _row(
                extracted_data_json=json.dumps(
                    _payload(
                        fields=[
                            {
                                "name": " ",
                                "value": "x",
                                "confidence": 0.9,
                                "evidence": "source",
                            }
                        ]
                    )
                )
            )
        ],
        "field_0_missing_name",
    )


def test_missing_bundle_id_uses_stable_blocker_prefix() -> None:
    conn = MagicMock()
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for([_row(bundle_id="", supplier_name="ABSENT")]),
    ):
        with pytest.raises(M14OfferReadinessError) as exc:
            build_m14_offers_for_workspace(conn, "ws-uuid")
    joined = ";".join(exc.value.blockers)
    assert "bundle_id_absent" in joined
    assert "extraction-1:supplier_name_absent" in joined
    assert ";:supplier_name_absent" not in joined
    assert not joined.startswith(":supplier_name_absent")


def test_maps_az_style_payload_into_enriched_offer() -> None:
    conn = MagicMock()
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for([_row()]),
    ):
        out = build_m14_offers_for_workspace(conn, "ws-uuid")

    assert len(out) == 1
    offer = out[0]
    assert offer["document_id"] == "b1"
    assert offer["supplier_name"] == "A - Z SARL"
    assert offer["process_role"] == "responds_to_bid"
    assert offer["extraction_id"] == "extraction-1"
    assert offer["extraction_ok"] is True
    assert offer["readiness_status"] == "ready"
    assert offer["readiness_blockers"] == []
    assert offer["extracted_fields"]
    assert offer["evidence_map"]["methodology"] == "Méthodologie proposée"
    assert offer["currency"] == "USD"
    assert "capability_sections_present" in offer


def test_emits_taxonomy_warning_for_atmost_style_payload() -> None:
    conn = MagicMock()
    atmost = _row(
        supplier_name="ATMOST",
        extracted_data_json=json.dumps(_payload(taxonomy_core="dao")),
    )
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for([atmost]),
    ):
        out = build_m14_offers_for_workspace(conn, "ws-uuid")
    assert out[0]["readiness_warnings"] == ["taxonomy_core_divergent"]


def test_does_not_return_identity_only_offer_in_production_path() -> None:
    conn = MagicMock()
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for([]),
    ):
        with pytest.raises(M14OfferReadinessError, match="offer_extractions_empty"):
            build_m14_offers_for_workspace(conn, "ws-uuid")


def test_existing_evaluation_documents_cannot_silently_skip_m14() -> None:
    _assert_blocked(
        [_row()],
        "evaluation_documents_existing_skip_risk",
        eval_docs=[{"id": "existing-eval"}],
    )


def test_stale_criterion_assessments_are_checked_by_sql_exists() -> None:
    captured_sql: list[str] = []
    _assert_blocked(
        [_row()],
        "criterion_assessments_stale_bundle_set",
        assessments=[{"stale": True}],
        captured_sql=captured_sql,
    )
    criterion_sql = "\n".join(
        sql for sql in captured_sql if "criterion_assessments" in sql
    ).lower()
    assert "select exists" in criterion_sql
    assert "limit 200" not in criterion_sql


def test_bundle_context_query_aggregates_document_rows_deterministically() -> None:
    captured_sql: list[str] = []
    conn = MagicMock()
    with patch(
        "src.procurement.m14_workspace_assembler.db_fetchall",
        side_effect=_fetchall_for([_row()], captured_sql=captured_sql),
    ):
        build_m14_offers_for_workspace(conn, "ws-uuid")
    context_sql = "\n".join(sql for sql in captured_sql if "supplier_bundles" in sql)
    assert "GROUP BY sb.id, sb.gate_b_role" in context_sql
    assert "FILTER" in context_sql
