"""UPSTREAM_CONTEXT_PACK — build without DB when SKIP_DB set."""

from __future__ import annotations

import pytest

from src.annotation.context_pack import (
    PACK_VERSION,
    UpstreamContextPack,
    build_upstream_context_pack,
)


@pytest.fixture
def skip_db(monkeypatch):
    monkeypatch.setenv("ANNOTATION_CONTEXT_PACK_SKIP_DB", "1")


def test_upstream_context_pack_model():
    p = UpstreamContextPack(document_id="d1", case_id="c1", sources_used=["none"])
    assert p.pack_version == PACK_VERSION
    assert p.document_id == "d1"


def test_build_upstream_context_pack_skips_db(skip_db, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pack = build_upstream_context_pack("doc-xyz")
    assert pack.document_id == "doc-xyz"
    assert pack.sources_used == ["none"]


def test_build_upstream_context_pack_explicit_case(skip_db):
    pack = build_upstream_context_pack("doc-1", case_id="case-42")
    assert pack.case_id == "case-42"
