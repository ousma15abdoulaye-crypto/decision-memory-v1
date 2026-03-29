"""Export Label Studio → m12-v2 (extracted_json + validation DMS)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_export_module():
    path = _ROOT / "scripts" / "export_ls_to_dms_jsonl.py"
    spec = importlib.util.spec_from_file_location("export_ls_to_dms_jsonl", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["export_ls_to_dms_jsonl"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def export_mod():
    return _load_export_module()


@pytest.fixture(scope="module")
def golden_dms_json() -> str:
    p = _ROOT / "data" / "annotations" / "fixtures" / "golden_dms_line.jsonl"
    return p.read_text(encoding="utf-8").strip()


def _minimal_legacy_ann() -> dict:
    """Annotation LS minimale pour to_dms_line_legacy (doc_type / ao_ref)."""
    return {
        "id": 1,
        "completed_by": 2,
        "result": [
            {
                "from_name": "doc_type",
                "to_name": "x",
                "type": "choices",
                "value": {"choices": ["RFQ"]},
            },
            {
                "from_name": "ao_ref",
                "to_name": "x",
                "type": "textarea",
                "value": {"text": ["AO-1"]},
            },
        ],
    }


def _ls_item(
    extracted_json: str,
    *,
    text: str = "p.1 RFQ-001 Org projet XOF 1000",
    annotation_status: str = "review_required",
) -> dict:
    return {
        "id": 42,
        "data": {"text": text},
        "annotations": [
            {
                "id": 99,
                "completed_by": 2,
                "result": [
                    {
                        "from_name": "extracted_json",
                        "to_name": "document_text",
                        "type": "textarea",
                        "value": {"text": [extracted_json]},
                    },
                    {
                        "from_name": "evidence_attestation",
                        "value": {"choices": ["confirmed_from_doc"]},
                    },
                    {
                        "from_name": "no_invented_numbers",
                        "value": {"choices": ["confirmed"]},
                    },
                    {
                        "from_name": "routing_ok",
                        "value": {"choices": ["correct"]},
                    },
                    {
                        "from_name": "financial_ok",
                        "value": {"choices": ["not_applicable"]},
                    },
                    {
                        "from_name": "annotation_notes",
                        "value": {"text": [""]},
                    },
                    {
                        "from_name": "annotation_status",
                        "value": {"choices": [annotation_status]},
                    },
                ],
            }
        ],
    }


def test_legacy_export_includes_source_text_from_data_text(export_mod) -> None:
    task = {"id": 10, "data": {"text": "legacy body from text"}}
    line = export_mod.to_dms_line_legacy(_minimal_legacy_ann(), task, 99)
    assert line["export_schema_version"] == "m12-legacy"
    assert line["source_text"] == "legacy body from text"


def test_legacy_source_text_prefers_data_text_over_content(export_mod) -> None:
    task = {
        "id": 11,
        "data": {"text": "winner", "content": "loser"},
    }
    line = export_mod.to_dms_line_legacy(_minimal_legacy_ann(), task, 1)
    assert line["source_text"] == "winner"


def test_legacy_source_text_falls_back_to_content_when_text_empty(export_mod) -> None:
    task = {"id": 12, "data": {"text": "", "content": "from content only"}}
    line = export_mod.to_dms_line_legacy(_minimal_legacy_ann(), task, 1)
    assert line["source_text"] == "from content only"


def test_legacy_source_text_uses_content_when_text_missing(export_mod) -> None:
    task = {"id": 13, "data": {"content": "html or pdf blob ref"}}
    line = export_mod.to_dms_line_legacy(_minimal_legacy_ann(), task, 1)
    assert line["source_text"] == "html or pdf blob ref"


def test_m12_v2_export_ok_with_valid_json(
    export_mod, golden_dms_json: str  # noqa: PT019
) -> None:
    item = _ls_item(golden_dms_json, annotation_status="review_required")
    line = export_mod.ls_annotation_to_m12_v2_line(
        item["annotations"][0],
        item,
        1,
        enforce_validated_qa=True,
    )
    assert line["export_schema_version"] == "m12-v2"
    assert line["export_ok"] is True
    assert line["source_text"] == "p.1 RFQ-001 Org projet XOF 1000"
    assert line["dms_annotation"] is not None
    assert line["dms_annotation"]["_meta"]["schema_version"] == "v3.0.1d"


def test_m12_v2_export_fails_on_invalid_json(export_mod) -> None:
    item = _ls_item("{not json", annotation_status="review_required")
    line = export_mod.ls_annotation_to_m12_v2_line(
        item["annotations"][0], item, 1, enforce_validated_qa=False
    )
    assert line["export_ok"] is False
    assert any("json_parse" in e for e in line["export_errors"])


def test_m12_v2_bad_evidence_reported_without_blocking_export_ok(
    export_mod, golden_dms_json: str
) -> None:
    """annotated_validated + texte sans preuves : export_ok si schéma OK ; violations en option."""
    item = _ls_item(
        golden_dms_json,
        text="totally unrelated text without markers",
        annotation_status="annotated_validated",
    )
    line = export_mod.ls_annotation_to_m12_v2_line(
        item["annotations"][0],
        item,
        1,
        enforce_validated_qa=True,
    )
    assert line["export_ok"] is True
    assert not any("validated_but_evidence" in e for e in line["export_errors"])
    assert line.get("evidence_violations")


def test_require_ls_attestations_blocks_validated_without_choices(
    export_mod, golden_dms_json: str
) -> None:
    item = _ls_item(golden_dms_json, annotation_status="annotated_validated")
    # Retirer les attestations du résultat LS
    res = item["annotations"][0]["result"]
    item["annotations"][0]["result"] = [
        r
        for r in res
        if r["from_name"] not in ("evidence_attestation", "no_invented_numbers")
    ]
    line = export_mod.ls_annotation_to_m12_v2_line(
        item["annotations"][0],
        item,
        1,
        enforce_validated_qa=False,
        require_ls_attestations=True,
    )
    assert line["export_ok"] is False
    assert any("missing_evidence_attestation" in e for e in line["export_errors"])


def test_annotation_qa_financial_when_line_items(export_mod) -> None:
    _ensure = export_mod._ensure_annotation_path  # noqa: SLF001
    _ensure()
    from annotation_qa import financial_coherence_warnings

    dms = json.loads(
        (_ROOT / "data/annotations/fixtures/golden_dms_line.jsonl").read_text(
            encoding="utf-8"
        )
    )
    dms["couche_1_routing"]["document_role"] = "offer_financial"
    dms["couche_1_routing"]["taxonomy_core"] = "offer_financial"
    dms["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "A",
            "unit_raw": "u",
            "quantity": 1.0,
            "unit_price": 100.0,
            "line_total": 100.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        }
    ]
    dms["couche_4_atomic"]["financier"]["total_price"] = {
        "value": 9999.0,
        "confidence": 1.0,
        "evidence": "p.1",
    }
    w = financial_coherence_warnings(dms, 0)
    assert w and w[0].startswith("ANOMALY_total_price_")
