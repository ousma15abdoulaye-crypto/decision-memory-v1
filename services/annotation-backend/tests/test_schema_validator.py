"""
Tests schema_validator DMS v3.0.1d — Couche 2 validation.
Vérifie : extra=forbid, gates ordre, line_total_check recalculé, confidence 0.6|0.8|1.0.
"""

from __future__ import annotations

import copy

import pytest

from prompts.schema_validator import (
    DMSAnnotation,
    GateName,
    LineCheck,
    LineItemLevel,
    normalize_annotation_output,
    normalize_boolean,
    normalize_item_line_no_strict,
    normalize_sentinel,
    resequence_line_items,
)


def _fv(v, c=1.0, e=""):
    return {"value": v, "confidence": c, "evidence": e or "p.1 — test"}


def _gate(name: str, value: bool | None, state: str, conf: float = 1.0):
    return {
        "gate_name": name,
        "gate_value": value,
        "gate_state": state,
        "gate_threshold_value": None,
        "gate_reason_raw": "",
        "gate_evidence_hint": "",
        "confidence": conf,
    }


def _minimal_valid() -> dict:
    gates = [_gate(g.value, None, "NOT_APPLICABLE") for g in GateName]
    return {
        "couche_1_routing": {
            "procurement_family_main": "goods",
            "procurement_family_sub": "food",
            "taxonomy_core": "rfq",
            "taxonomy_client_adapter": "rfq",
            "document_stage": "solicitation",
            "document_role": "source_rules",
        },
        "couche_2_core": {
            "procedure_reference": _fv("RFQ-001"),
            "issuing_entity": _fv("Org"),
            "project_name": _fv("Proj"),
            "lot_count": _fv(1),
            "lot_scope": _fv([]),
            "zone_scope": _fv([]),
            "submission_deadline": _fv(""),
            "submission_mode": _fv([]),
            "result_type": _fv(""),
            "technical_threshold": _fv(""),
            "visit_required": _fv(""),
            "sample_required": _fv(""),
            "negotiation_allowed": _fv(""),
            "regime_dominant": _fv(""),
            "modalite_paiement": _fv(""),
            "eligibility_gates": [],
            "scoring_structure": [],
            "ponderation_coherence": "",
        },
        "couche_3_policy_sci": {
            "has_sci_conditions_signed": _fv(""),
            "has_iapg_signed": _fv(""),
            "has_non_sanction": _fv(""),
            "ariba_network_required": _fv(""),
            "sci_sustainability_pct": _fv(""),
        },
        "couche_4_atomic": {
            "conformite_admin": {
                k: _fv("")
                for k in [
                    "has_nif",
                    "has_rccm",
                    "has_rib",
                    "has_id_representative",
                    "has_statutes",
                    "has_quitus_fiscal",
                    "has_certificat_non_faillite",
                ]
            },
            "capacite_services": {
                k: _fv("")
                for k in [
                    "similar_assignments_count",
                    "lead_expert_years",
                    "lead_expert_similar_projects_count",
                    "team_composition_present",
                    "methodology_present",
                    "workplan_present",
                    "qa_plan_present",
                    "ethics_plan_present",
                ]
            },
            "capacite_works": {
                k: _fv("")
                for k in [
                    "execution_delay_days",
                    "work_methodology_present",
                    "environment_plan_present",
                    "site_visit_pv_present",
                    "equipment_list_present",
                    "key_staff_present",
                    "local_labor_commitment_present",
                ]
            },
            "capacite_goods": {
                k: _fv("")
                for k in [
                    "client_references_present",
                    "warranty_present",
                    "delivery_schedule_present",
                    "warehouse_capacity_present",
                    "stock_sufficiency_present",
                    "product_specs_present",
                    "official_distribution_license_present",
                    "sample_submission_present",
                    "phytosanitary_cert_present",
                    "bank_credit_line_present",
                ]
            },
            "durabilite": {
                k: _fv("")
                for k in [
                    "local_content_present",
                    "community_employment_present",
                    "environment_commitment_present",
                    "gender_inclusion_present",
                    "sustainability_certifications",
                ]
            },
            "financier": {
                "financial_layout_mode": "lump_sum",
                "pricing_scope": "",
                "total_price": _fv(1000),
                "currency": _fv("XOF"),
                "price_basis": _fv(""),
                "price_date": _fv(""),
                "delivery_delay_days": _fv(""),
                "validity_days": _fv(""),
                "discount_terms_present": _fv(""),
                "review_required": False,
                "line_items": [],
            },
        },
        "couche_5_gates": gates,
        "identifiants": {
            "supplier_name_raw": "",
            "supplier_name_normalized": "",
            "supplier_legal_form": "",
            "supplier_identifier_raw": "",
            "has_nif": "",
            "has_rccm": "",
            "has_rib": "",
            "supplier_address_raw": "",
            "supplier_phone_raw": "",
            "supplier_email_raw": "",
            "quitus_fiscal_date": "",
            "cert_non_faillite_date": "",
            "case_id": "",
            "supplier_id": "",
            "lot_scope": [],
            "zone_scope": [],
        },
        "ambiguites": [],
        "_meta": {
            "schema_version": "v3.0.1d",
            "framework_version": "annotation-framework-v3.0.1d",
            "mistral_model_used": "mistral-small-latest",
            "review_required": False,
            "annotation_status": "pending",
            "list_null_reason": {},
            "page_range": {"start": None, "end": None},
            "parent_document_id": "",
            "parent_document_role": "",
            "supplier_inherited_from": None,
        },
    }


def test_dms_annotation_minimal_valid():
    """Structure minimale valide — validation OK."""
    d = _minimal_valid()
    v = DMSAnnotation.model_validate(d)
    assert v.couche_1_routing.procurement_family_main == "goods"
    assert len(v.couche_5_gates) == 10


def test_normalize_strip_couche_2_core_llm_extra_keys():
    """Mistral place parfois evidence/confidence sur couche_2_core — retirées avant Pydantic."""
    d = _minimal_valid()
    d["couche_2_core"]["evidence"] = "p.1"
    d["couche_2_core"]["confidence"] = 0.9
    norm = normalize_annotation_output(copy.deepcopy(d))
    assert "evidence" not in norm["couche_2_core"]
    assert "confidence" not in norm["couche_2_core"]
    DMSAnnotation.model_validate(norm)


def test_normalize_financier_total_price_scalar_to_fieldvalue():
    """Mistral renvoie parfois total_price comme nombre brut au lieu d'un FieldValue."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = 9_070_000_109.0
    norm = normalize_annotation_output(copy.deepcopy(d))
    tp = norm["couche_4_atomic"]["financier"]["total_price"]
    assert isinstance(tp, dict)
    assert tp["value"] == 9_070_000_109.0
    assert tp["confidence"] == 0.8
    assert tp["evidence"] == "ABSENT"
    DMSAnnotation.model_validate(norm)


def test_dms_annotation_gates_order_rejected():
    """Gates dans le mauvais ordre → ValidationError."""
    d = _minimal_valid()
    d["couche_5_gates"] = [
        _gate("gate_capacity_passed", None, "NOT_APPLICABLE"),
        _gate("gate_eligibility_passed", None, "NOT_APPLICABLE"),
    ] + [_gate(g.value, None, "NOT_APPLICABLE") for g in list(GateName)[2:]]
    with pytest.raises(ValueError, match="couche_5_gates incorrect"):
        DMSAnnotation.model_validate(d)


def test_dms_annotation_line_total_check_recalculated():
    """line_total_check recalculé par backend — ANOMALY si écart > 1%."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Test",
            "unit_raw": "unité",
            "quantity": 10.0,
            "unit_price": 100.0,
            "line_total": 900.0,  # 10*100=1000, écart 10% > 1%
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert (
        v.couche_4_atomic.financier.line_items[0].line_total_check == LineCheck.ANOMALY
    )
    assert any("AMBIG-3_item_1" in a for a in v.ambiguites)


def test_line_item_item_line_no_hierarchical_decimal_ok():
    """Budget récap + détail : entrée 1.1 → normalize → resequence → int 1 ; parent_subtotal_no exclu V1."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(1000.0)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1.1,
            "item_description_raw": "Sous-ligne",
            "unit_raw": "u",
            "quantity": 2.0,
            "unit_price": 100.0,
            "line_total": 200.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
            "parent_subtotal_no": 1,
        }
    ]
    norm = normalize_annotation_output(copy.deepcopy(d))
    v = DMSAnnotation.model_validate(norm)
    assert v.couche_4_atomic.financier.line_items[0].item_line_no == 1
    assert isinstance(v.couche_4_atomic.financier.line_items[0].item_line_no, int)
    assert (
        "parent_subtotal_no"
        not in norm["couche_4_atomic"]["financier"]["line_items"][0]
    )


def test_line_item_item_line_no_float_from_json_coerced():
    """Mistral / JSON numérique : item_line_no 1.0 → int 1."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(1000.0)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1.0,
            "item_description_raw": "Ligne",
            "unit_raw": "u",
            "quantity": 10.0,
            "unit_price": 100.0,
            "line_total": 1000.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert v.couche_4_atomic.financier.line_items[0].item_line_no == 1
    assert isinstance(v.couche_4_atomic.financier.line_items[0].item_line_no, int)


def test_item_line_no_hierarchical_resequenced():
    """Entrée Mistral hiérarchique → entiers séquentiels."""
    items = [
        {
            "item_line_no": 1,
            "item_description_raw": "Honoraires",
            "level": "subtotal",
        },
        {
            "item_line_no": 1.1,
            "item_description_raw": "Consultant principal",
            "level": "detail",
        },
        {
            "item_line_no": 1.2,
            "item_description_raw": "Consultant associé",
            "level": "detail",
        },
        {
            "item_line_no": 2,
            "item_description_raw": "Logistique",
            "level": "subtotal",
        },
        {
            "item_line_no": 2.1,
            "item_description_raw": "Transport",
            "level": "detail",
        },
    ]
    result = resequence_line_items(items)
    assert [r["item_line_no"] for r in result] == [1, 2, 3, 4, 5]
    assert all(isinstance(r["item_line_no"], int) for r in result)


def test_item_line_no_int_and_string_normalized():
    """Entiers, floats entiers, strings → int séquentiel."""
    items = [
        {"item_line_no": 1, "item_description_raw": "A", "level": "detail"},
        {"item_line_no": 2.0, "item_description_raw": "B", "level": "detail"},
        {"item_line_no": "3", "item_description_raw": "C", "level": "detail"},
        {"item_line_no": "4.0", "item_description_raw": "D", "level": "detail"},
    ]
    result = resequence_line_items(items)
    assert [r["item_line_no"] for r in result] == [1, 2, 3, 4]
    assert all(isinstance(r["item_line_no"], int) for r in result)


def test_boolean_string_normalized():
    """'true'/'false' strings → True/False natifs."""
    assert normalize_boolean("true", "has_rib") is True
    assert normalize_boolean("false", "has_rib") is False
    assert normalize_boolean("True", "has_nif") is True
    assert normalize_boolean("FALSE", "has_rccm") is False
    assert normalize_boolean(True, "has_rib") is True
    assert normalize_boolean(False, "has_rib") is False
    assert normalize_boolean("OUI", "has_nif") is True
    assert normalize_boolean("NON", "has_rccm") is False
    assert normalize_boolean("requis", "has_rib") is True


def test_empty_string_to_sentinel():
    """'' sur champs ciblés → 'ABSENT', pas chaîne vide."""
    assert normalize_sentinel("", "procedure_reference") == "ABSENT"
    assert normalize_sentinel("", "has_nif") == "ABSENT"
    assert normalize_sentinel("", "supplier_address_raw") == "ABSENT"
    assert normalize_sentinel("Bamako", "supplier_address_raw") == "Bamako"
    assert normalize_sentinel("ABSENT", "has_nif") == "ABSENT"
    assert normalize_sentinel("NOT_APPLICABLE", "has_nif") == "NOT_APPLICABLE"


def test_financial_offer_az_hierarchical_passes():
    """JSON type A-Z : après normalisation — types propres, AMBIG-6 fantôme retiré, review aligné."""
    raw_json = _minimal_valid()
    raw_json["couche_1_routing"]["document_role"] = "financial_offer"
    raw_json["couche_4_atomic"]["conformite_admin"]["has_rib"] = {
        "value": "true",
        "confidence": 1.0,
        "evidence": "p.1",
    }
    raw_json["couche_4_atomic"]["conformite_admin"]["has_nif"] = {
        "value": "",
        "confidence": 0.6,
        "evidence": "ABSENT",
    }
    raw_json["couche_4_atomic"]["financier"]["total_price"] = _fv("29194950")
    raw_json["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Honoraires",
            "unit_raw": "forfait",
            "level": "subtotal",
            "parent_subtotal_no": None,
            "quantity": 1.0,
            "unit_price": 18_050_000.0,
            "line_total": 18_050_000.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        },
        {
            "item_line_no": 1.1,
            "item_description_raw": "Consultant principal",
            "unit_raw": "hj",
            "level": "detail",
            "parent_subtotal_no": 1,
            "quantity": 45.0,
            "unit_price": 110_000.0,
            "line_total": 4_950_000.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        },
        {
            "item_line_no": 1.2,
            "item_description_raw": "Consultant statisticien",
            "unit_raw": "hj",
            "level": "detail",
            "parent_subtotal_no": 1,
            "quantity": 30.0,
            "unit_price": 100_000.0,
            "line_total": 3_000_000.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        },
    ]
    raw_json["_meta"]["review_required"] = True
    raw_json["couche_4_atomic"]["financier"]["review_required"] = False
    raw_json["ambiguites"] = ["AMBIG-6_schema_validation_errors"]

    result = normalize_annotation_output(copy.deepcopy(raw_json))

    items = result["couche_4_atomic"]["financier"]["line_items"]
    assert [i["item_line_no"] for i in items] == [1, 2, 3]
    assert all(isinstance(i["item_line_no"], int) for i in items)
    assert all("parent_subtotal_no" not in i for i in items)
    assert items[0]["level"] == "subtotal"
    assert items[1]["level"] == "detail"
    assert result["couche_4_atomic"]["conformite_admin"]["has_rib"]["value"] is True
    assert result["couche_4_atomic"]["conformite_admin"]["has_nif"]["value"] == "ABSENT"
    assert "AMBIG-6_schema_validation_errors" not in result["ambiguites"]
    assert result["_meta"]["review_required"] is True
    assert result["couche_4_atomic"]["financier"]["review_required"] is True

    DMSAnnotation.model_validate(result)


def test_flat_json_backward_compatible():
    """JSON ancien format sans level : level par défaut = detail."""
    raw_json = _minimal_valid()
    raw_json["couche_4_atomic"]["financier"]["total_price"] = _fv("5000000")
    raw_json["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Article A",
            "unit_raw": "u",
            "quantity": 10.0,
            "unit_price": 250_000.0,
            "line_total": 2_500_000.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        },
        {
            "item_line_no": 2,
            "item_description_raw": "Article B",
            "unit_raw": "u",
            "quantity": 5.0,
            "unit_price": 500_000.0,
            "line_total": 2_500_000.0,
            "line_total_check": "OK",
            "confidence": 0.8,
            "evidence": "p.1",
        },
    ]
    raw_json["_meta"]["review_required"] = False
    raw_json["ambiguites"] = []

    result = normalize_annotation_output(copy.deepcopy(raw_json))
    items = result["couche_4_atomic"]["financier"]["line_items"]
    assert [i["item_line_no"] for i in items] == [1, 2]
    assert all(i["level"] == "detail" for i in items)
    assert all("parent_subtotal_no" not in i for i in items)
    DMSAnnotation.model_validate(result)


def test_routing_and_gates_unchanged_after_normalization():
    """La normalisation ne modifie ni couche_1_routing ni couche_5_gates."""
    raw_json = _minimal_valid()
    raw_json["couche_1_routing"] = {
        "procurement_family_main": "services",
        "procurement_family_sub": "consulting",
        "taxonomy_core": "rfq",
        "taxonomy_client_adapter": "rfq",
        "document_stage": "solicitation",
        "document_role": "financial_offer",
    }
    raw_json["couche_5_gates"] = [
        {
            "gate_name": g.value,
            "gate_value": None,
            "gate_state": "NOT_APPLICABLE",
            "gate_threshold_value": None,
            "gate_reason_raw": "",
            "gate_evidence_hint": "",
            "confidence": 1.0,
        }
        for g in GateName
    ]
    raw_json["couche_5_gates"][6] = {
        "gate_name": "gate_commercial_eligible",
        "gate_value": True,
        "gate_state": "APPLICABLE",
        "gate_threshold_value": None,
        "gate_reason_raw": "",
        "gate_evidence_hint": "",
        "confidence": 1.0,
    }

    original_routing = copy.deepcopy(raw_json["couche_1_routing"])
    original_gates = copy.deepcopy(raw_json["couche_5_gates"])

    result = normalize_annotation_output(copy.deepcopy(raw_json))
    assert result["couche_1_routing"] == original_routing
    assert result["couche_5_gates"] == original_gates


def test_item_line_no_invalid_rejected():
    """null, '', 'abc' → ValueError."""
    with pytest.raises(ValueError):
        normalize_item_line_no_strict(None)
    with pytest.raises(ValueError):
        normalize_item_line_no_strict("")
    with pytest.raises(ValueError):
        normalize_item_line_no_strict("abc")


def test_dms_annotation_line_total_check_ok_exact():
    """qty × unit_price == line_total → OK."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Ligne",
            "unit_raw": "u",
            "quantity": 10.0,
            "unit_price": 100.0,
            "line_total": 1000.0,
            "line_total_check": "ANOMALY",
            "confidence": 1.0,
            "evidence": "p.1 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert v.couche_4_atomic.financier.line_items[0].line_total_check == LineCheck.OK


def test_dms_annotation_line_total_check_within_relative_tolerance():
    """Écart relatif ≤ 1 % vs max(line_total,1) → OK."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Ligne",
            "unit_raw": "u",
            "quantity": 10.0,
            "unit_price": 100.0,
            "line_total": 1005.0,
            "line_total_check": "ANOMALY",
            "confidence": 1.0,
            "evidence": "p.1 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert v.couche_4_atomic.financier.line_items[0].line_total_check == LineCheck.OK


def test_dms_annotation_line_total_check_non_verifiable_zero_quantity():
    """quantity 0.0 → NON_VERIFIABLE (branche falsy, pas de contrôle math)."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Ligne",
            "unit_raw": "u",
            "quantity": 0.0,
            "unit_price": 100.0,
            "line_total": 0.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert (
        v.couche_4_atomic.financier.line_items[0].line_total_check
        == LineCheck.NON_VERIFIABLE
    )


def test_dms_annotation_gate_confidence_rejected():
    """Gate confidence 0.9 → ValidationError (E-17)."""
    d = _minimal_valid()
    d["couche_5_gates"][0]["confidence"] = 0.9
    with pytest.raises(ValueError, match="confidence=0.9 interdit"):
        DMSAnnotation.model_validate(d)


def test_dms_annotation_unit_raw_empty_rejected():
    """LineItem unit_raw vide → ValidationError (ADR-015)."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Test",
            "unit_raw": "",
            "quantity": 1.0,
            "unit_price": 100.0,
            "line_total": 100.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        }
    ]
    with pytest.raises(ValueError, match="unit_raw vide"):
        DMSAnnotation.model_validate(d)


def test_arch03_detail_level_arithmetic_ok():
    """Ligne detail : quantity × unit_price = line_total → OK."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(4_950_000)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Honoraire consultant",
            "unit_raw": "homme-jour",
            "quantity": 45.0,
            "unit_price": 110_000.0,
            "line_total": 4_950_000.0,
            "line_total_check": "OK",
            "level": "detail",
            "confidence": 1.0,
            "evidence": "p.3 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert v.couche_4_atomic.financier.line_items[0].line_total_check == LineCheck.OK


def test_arch03_subtotal_level_not_arithmetic_checked():
    """Ligne subtotal : pas de contrôle qty×unit_price → SUBTOTAL_NOT_CHECKED_HERE."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(18_050_000)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Sous-total honoraires",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 18_050_000.0,
            "line_total": 18_050_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.2 — test",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    li = v.couche_4_atomic.financier.line_items[0]
    assert li.level == LineItemLevel.SUBTOTAL
    assert li.line_total_check == LineCheck.SUBTOTAL_NOT_CHECKED_HERE
    assert not any("ANOMALY_" in a for a in v.ambiguites)


def test_arch03_recap_plus_detail_no_double_count_false_positive():
    """
    4 subtotaux (récap) + ligne détail : somme des subtotaux = total_price.
    Les détails ne sont pas additionnés au total quand des subtotaux existent.
    """
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(29_194_950)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Honoraires et perdiem",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 18_050_000.0,
            "line_total": 18_050_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.2",
        },
        {
            "item_line_no": 2,
            "item_description_raw": "Logistique",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 7_365_000.0,
            "line_total": 7_365_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.2",
        },
        {
            "item_line_no": 3,
            "item_description_raw": "Frais administratifs",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 1_870_000.0,
            "line_total": 1_870_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.2",
        },
        {
            "item_line_no": 4,
            "item_description_raw": "Frais de gestion (7%)",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 1_909_950.0,
            "line_total": 1_909_950.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.2",
        },
        {
            "item_line_no": 5,
            "item_description_raw": "Ligne budget détaillé (exemple)",
            "unit_raw": "homme-jour",
            "quantity": 10.0,
            "unit_price": 20_000.0,
            "line_total": 200_000.0,
            "line_total_check": "OK",
            "level": "detail",
            "confidence": 1.0,
            "evidence": "p.3",
        },
    ]
    v = DMSAnnotation.model_validate(d)
    assert not any("ANOMALY_subtotals_sum_" in a for a in v.ambiguites)
    assert not any("ANOMALY_details_sum_" in a for a in v.ambiguites)


def test_total_price_field_parses_ocr_unicode_spaces():
    """total_price aligné annotation_qa : espaces Unicode (\u2009, \u202f, etc.) retirés."""
    d = _minimal_valid()
    raw = "29\u2009194\u202f950"
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(raw)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Forfait",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 29_194_950.0,
            "line_total": 29_194_950.0,
            "line_total_check": "OK",
            "level": "detail",
            "confidence": 1.0,
            "evidence": "p.1",
        }
    ]
    v = DMSAnnotation.model_validate(d)
    assert not any("ANOMALY_details_sum_" in a for a in v.ambiguites)


def test_arch03_subtotals_sum_mismatch_vs_total_price_anomaly():
    """Subtotaux déclarés ne correspondent pas à total_price → ANOMALY."""
    d = _minimal_valid()
    d["couche_4_atomic"]["financier"]["total_price"] = _fv(29_194_950)
    d["couche_4_atomic"]["financier"]["line_items"] = [
        {
            "item_line_no": 1,
            "item_description_raw": "Bloc A",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 10_000_000.0,
            "line_total": 10_000_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.1",
        },
        {
            "item_line_no": 2,
            "item_description_raw": "Bloc B",
            "unit_raw": "forfait",
            "quantity": 1.0,
            "unit_price": 5_000_000.0,
            "line_total": 5_000_000.0,
            "line_total_check": "OK",
            "level": "subtotal",
            "confidence": 1.0,
            "evidence": "p.1",
        },
    ]
    v = DMSAnnotation.model_validate(d)
    assert any("ANOMALY_subtotals_sum_" in a for a in v.ambiguites)
