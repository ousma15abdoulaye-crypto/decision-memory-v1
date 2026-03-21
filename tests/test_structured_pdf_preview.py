"""Aperçu structuré PDF (bridge / LS)."""

from __future__ import annotations

from src.annotation.structured_pdf_preview import structured_preview_from_pdf


def test_structured_preview_disabled_when_max_pages_zero() -> None:
    prev = structured_preview_from_pdf("/any/path.pdf", max_pages=0)
    assert prev["page_count_sampled"] == 0
    assert "structured_preview_disabled" in prev["errors"]


def test_structured_preview_nonexistent_file_has_error(tmp_path) -> None:
    missing = tmp_path / "nope.pdf"
    prev = structured_preview_from_pdf(str(missing), max_pages=2)
    assert prev["errors"]
