"""Tests for src/procurement/document_ontology.py — enum coverage and mappings."""

from __future__ import annotations

import pytest

from src.procurement.document_ontology import (
    DOCUMENT_KIND_TO_LAYER,
    DOCUMENT_KIND_TO_PROCESS_ROLE,
    DOCUMENT_KIND_TO_STAGE,
    OFFER_KINDS,
    SOURCE_RULES_KINDS,
    DocumentKindParent,
    DocumentKindSubtype,
    DocumentLayer,
    DocumentStage,
    LinkNature,
    ProcedureType,
    ProcessRole,
    ProcurementFamily,
    ProcurementFramework,
)


class TestEnumsExist:
    def test_procurement_framework_values(self) -> None:
        assert len(ProcurementFramework) >= 10
        assert ProcurementFramework.SCI == "sci"
        assert ProcurementFramework.UNKNOWN == "unknown"

    def test_procurement_family_values(self) -> None:
        assert ProcurementFamily.GOODS == "goods"
        assert ProcurementFamily.CONSULTANCY == "consultancy"

    def test_document_kind_parent_coverage(self) -> None:
        assert len(DocumentKindParent) >= 19
        assert DocumentKindParent.TDR == "tdr"
        assert DocumentKindParent.EVALUATION_DOC == "evaluation_doc"

    def test_document_kind_subtype_values(self) -> None:
        assert DocumentKindSubtype.GENERIC == "generic"
        assert DocumentKindSubtype.CONSTRUCTION_WORKS == "construction_works"


class TestMappingsCoverage:
    def test_every_parent_has_layer(self) -> None:
        for kind in DocumentKindParent:
            assert kind in DOCUMENT_KIND_TO_LAYER, f"{kind} missing layer mapping"

    def test_every_parent_has_stage(self) -> None:
        for kind in DocumentKindParent:
            assert kind in DOCUMENT_KIND_TO_STAGE, f"{kind} missing stage mapping"

    def test_every_parent_has_process_role(self) -> None:
        for kind in DocumentKindParent:
            assert kind in DOCUMENT_KIND_TO_PROCESS_ROLE, f"{kind} missing role mapping"


class TestFrozenSets:
    def test_source_rules_kinds(self) -> None:
        assert DocumentKindParent.TDR in SOURCE_RULES_KINDS
        assert DocumentKindParent.DAO in SOURCE_RULES_KINDS
        assert DocumentKindParent.OFFER_TECHNICAL not in SOURCE_RULES_KINDS

    def test_offer_kinds(self) -> None:
        assert DocumentKindParent.OFFER_TECHNICAL in OFFER_KINDS
        assert DocumentKindParent.EVALUATION_DOC not in OFFER_KINDS


class TestEnumUniqueness:
    @pytest.mark.parametrize(
        "enum_cls",
        [
            ProcurementFramework,
            ProcurementFamily,
            DocumentKindParent,
            DocumentKindSubtype,
            DocumentLayer,
            DocumentStage,
            ProcedureType,
            LinkNature,
            ProcessRole,
        ],
    )
    def test_values_unique(self, enum_cls: type) -> None:
        values = [m.value for m in enum_cls]
        assert len(values) == len(
            set(values)
        ), f"Duplicate values in {enum_cls.__name__}"
