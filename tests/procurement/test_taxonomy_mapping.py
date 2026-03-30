"""Tests for src/procurement/taxonomy_mapping.py — bidirectional corpus mapping."""

from __future__ import annotations

from src.procurement.document_ontology import (
    DocumentKindParent,
    DocumentKindSubtype,
)
from src.procurement.taxonomy_mapping import (
    all_corpus_keys,
    corpus_to_parent_subtype,
    legacy_taxonomy_to_m12,
    parent_subtype_to_corpus,
)


class TestCorpusToM12:
    def test_known_key(self) -> None:
        parent, subtype = corpus_to_parent_subtype("offer_technical")
        assert parent == DocumentKindParent.OFFER_TECHNICAL
        assert subtype == DocumentKindSubtype.GENERIC

    def test_unknown_key_returns_unknown(self) -> None:
        parent, subtype = corpus_to_parent_subtype("nonexistent_type")
        assert parent == DocumentKindParent.UNKNOWN
        assert subtype == DocumentKindSubtype.OTHER

    def test_tdr_consultancy(self) -> None:
        parent, subtype = corpus_to_parent_subtype("tdr_consultance_audit")
        assert parent == DocumentKindParent.TDR

    def test_dao_construction(self) -> None:
        parent, subtype = corpus_to_parent_subtype("dao_construction_goods")
        assert parent == DocumentKindParent.DAO
        assert subtype == DocumentKindSubtype.CONSTRUCTION_GOODS


class TestM12ToCorpus:
    def test_roundtrip_known(self) -> None:
        key = parent_subtype_to_corpus(
            DocumentKindParent.OFFER_TECHNICAL, DocumentKindSubtype.GENERIC
        )
        assert key == "offer_technical"

    def test_unknown_roundtrip(self) -> None:
        key = parent_subtype_to_corpus(
            DocumentKindParent.UNKNOWN, DocumentKindSubtype.OTHER
        )
        assert key == "unknown"


class TestLegacyBridge:
    def test_legacy_offer_financial(self) -> None:
        assert (
            legacy_taxonomy_to_m12("offer_financial")
            == DocumentKindParent.OFFER_FINANCIAL
        )

    def test_legacy_unknown_returns_unknown(self) -> None:
        assert legacy_taxonomy_to_m12("no_such_thing") == DocumentKindParent.UNKNOWN


class TestAllCorpusKeys:
    def test_returns_frozenset(self) -> None:
        keys = all_corpus_keys()
        assert isinstance(keys, frozenset)
        assert "offer_technical" in keys
        assert "unknown" in keys
