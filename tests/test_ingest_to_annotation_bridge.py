"""Tests bridge M-INGEST-TO-ANNOTATION-BRIDGE-00 (script autonome, sans API cloud)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BRIDGE_PATH = ROOT / "scripts" / "ingest_to_annotation_bridge.py"
_spec = importlib.util.spec_from_file_location(
    "ingest_to_annotation_bridge", _BRIDGE_PATH
)
assert _spec and _spec.loader
_bridge = importlib.util.module_from_spec(_spec)
sys.modules["ingest_to_annotation_bridge"] = _bridge
_spec.loader.exec_module(_bridge)


def _load_bridge_module():
    return _bridge


def test_classify_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    mod = _load_bridge_module()
    f = tmp_path / "x.txt"
    f.write_text("hello", encoding="utf-8")
    assert mod.classify_pdf(f, "hello") == "rejected"


def test_classify_pdf_native_when_long_text(tmp_path: Path) -> None:
    mod = _load_bridge_module()
    f = tmp_path / "n.pdf"
    f.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    text = "word " * 30  # > 100 chars
    assert mod.classify_pdf(f, text) == "native_pdf"


def test_classify_to_document_role_from_filename() -> None:
    mod = _load_bridge_module()
    assert (
        mod._classify_to_document_role("native_pdf", "/x/PROPOSITION FINANCIERE A-Z.pdf")
        == "financial_offer"
    )
    assert (
        mod._classify_to_document_role("native_pdf", r"C:\d\OFFRE TECHNIQUE SARL.pdf")
        == "offer_technical"
    )
    assert mod._classify_to_document_role("native_pdf", "/d/doc.pdf") == "supporting_doc"


@pytest.fixture
def bridge_mod():
    return _load_bridge_module()


def test_run_ingest_writes_ls_tasks_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bridge_mod
) -> None:
    src = tmp_path / "process_a"
    src.mkdir()
    pdf = src / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    monkeypatch.setattr(
        bridge_mod,
        "extract_pdf_text_local_only",
        lambda _p: "x" * 120,
    )

    def _no_mistral(*_a, **_k):
        raise AssertionError("mistral should not run")

    def _no_llama(*_a, **_k):
        raise AssertionError("llamaparse should not run")

    monkeypatch.setattr(bridge_mod, "_extract_mistral_ocr", _no_mistral)
    monkeypatch.setattr(bridge_mod, "_extract_llamaparse", _no_llama)

    out = tmp_path / "out"
    report = bridge_mod.run_ingest(
        source_roots=[str(src)],
        output_root=str(out),
        default_document_role="dao",
        run_id="test-run-1",
        include_manifest_tasks=True,
    )
    assert report["tasks_emitted"] == 1
    assert report["tasks_skipped"] == 0

    ls_tasks = json.loads((out / "ls_tasks.json").read_text(encoding="utf-8"))
    assert len(ls_tasks) == 1
    row = ls_tasks[0]["data"]
    assert row["text"] == "x" * 120
    assert row["filename"] == "doc.pdf"
    assert row["document_role"] == "dao"
    assert row["process_name"] == "process_a"
    assert row["ingest_run_id"] == "test-run-1"
    assert "source" in row and "doc.pdf" in row["source"]

    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "test-run-1"
    assert len(manifest["tasks"]) == 1
    assert manifest["tasks"][0]["document_role"] == "dao"


def test_run_ingest_manifest_omits_tasks_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bridge_mod
) -> None:
    src = tmp_path / "p"
    src.mkdir()
    pdf = src / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    monkeypatch.setattr(
        bridge_mod,
        "extract_pdf_text_local_only",
        lambda _p: "z" * 120,
    )
    monkeypatch.setattr(bridge_mod, "_extract_mistral_ocr", lambda *_a, **_k: ("", ""))
    monkeypatch.setattr(bridge_mod, "_extract_llamaparse", lambda *_a, **_k: ("", ""))
    out = tmp_path / "out2"
    bridge_mod.run_ingest(
        source_roots=[str(src)],
        output_root=str(out),
        default_document_role="supporting_doc",
        run_id="no-tasks-manifest",
    )
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert "tasks" not in manifest


def test_run_ingest_rejects_empty_source_roots(tmp_path: Path, bridge_mod) -> None:
    with pytest.raises(ValueError, match="source_roots ne peut pas être vide"):
        bridge_mod.run_ingest(
            source_roots=[],
            output_root=str(tmp_path / "out"),
            default_document_role="dao",
            run_id="empty-roots",
        )
