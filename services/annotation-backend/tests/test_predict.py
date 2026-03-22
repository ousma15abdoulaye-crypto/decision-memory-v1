"""
Tests intégration /predict — Mandat 5.
Vérifie la structure Label Studio et la normalisation gates.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configurer l'environnement requis pour le backend pour chaque test.

    On utilise monkeypatch.setenv pour éviter de modifier l'état global
    du process pytest au moment de l'import du module de test.
    """
    monkeypatch.setenv(
        "PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-sel-mandat5")
    )
    monkeypatch.setenv(
        "ALLOW_WEAK_PSEUDONYMIZATION",
        os.environ.get("ALLOW_WEAK_PSEUDONYMIZATION", "1"),
    )
    monkeypatch.setenv("MISTRAL_API_KEY", os.environ.get("MISTRAL_API_KEY", ""))


# Chargement hermétique de backend.py sans modifier sys.path globalement
_BACKEND_MODULE = None
_BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend.py"


def _load_backend_module():
    """Charge le module backend depuis backend.py sans toucher à sys.path."""
    global _BACKEND_MODULE
    if _BACKEND_MODULE is not None:
        return _BACKEND_MODULE

    spec = importlib.util.spec_from_file_location("backend", _BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Impossible de charger le module backend depuis {_BACKEND_PATH}"
        )

    _repo = Path(__file__).resolve().parents[3]
    if str(_repo) not in sys.path:
        sys.path.insert(0, str(_repo))

    module = importlib.util.module_from_spec(spec)
    # Enregistrer le module pour que les imports internes fonctionnent éventuellement
    sys.modules.setdefault("backend", module)
    spec.loader.exec_module(module)
    _BACKEND_MODULE = module
    return module


@pytest.fixture(scope="module", autouse=True)
def _autoload_backend_module() -> None:
    """Charger backend une fois — variables d'env avant import (PSEUDONYM_SALT)."""
    os.environ.setdefault("PSEUDONYM_SALT", "test-sel-mandat5")
    os.environ.setdefault("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    _load_backend_module()
    yield


class TestNormalizeGates:
    """Tests _normalize_gates()."""

    def _import(self):
        backend = _load_backend_module()
        return backend._normalize_gates

    def test_not_applicable_confidence_zero_corrige(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_visit_passed",
                    "gate_state": "NOT_APPLICABLE",
                    "gate_value": None,
                    "confidence": 0.0,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        gate = result["couche_5_gates"][0]
        assert gate["confidence"] == 1.0, f"Expected 1.0, got {gate['confidence']}"

    def test_applicable_confidence_zero_corrige(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_eligibility_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": True,
                    "confidence": 0.0,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        gate = result["couche_5_gates"][0]
        assert gate["confidence"] == 0.6

    def test_applicable_gate_value_null_defaults_to_false(self):
        """APPLICABLE + gate_value null → False (schéma Pydantic ; revue humaine possible)."""
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_negotiation_reached",
                    "gate_state": "APPLICABLE",
                    "gate_value": None,
                    "confidence": 0.8,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        gate = result["couche_5_gates"][0]
        assert gate["gate_value"] is False
        assert result["ambiguites"] == []

    def test_confidence_correcte_non_touchee(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_eligibility_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": True,
                    "confidence": 0.8,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        gate = result["couche_5_gates"][0]
        assert gate["confidence"] == 0.8

    def test_not_applicable_gate_value_non_null_force_null(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_visit_passed",
                    "gate_state": "NOT_APPLICABLE",
                    "gate_value": True,
                    "confidence": 1.0,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        gate = result["couche_5_gates"][0]
        assert gate["gate_value"] is None

    def test_gate_threshold_value_missing_key_filled_with_none(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_eligibility_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": True,
                    "confidence": 0.8,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        assert "gate_threshold_value" in result["couche_5_gates"][0]
        assert result["couche_5_gates"][0]["gate_threshold_value"] is None

    def test_gate_threshold_value_string_parsed_to_float(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_capacity_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": True,
                    "gate_threshold_value": "1500000,50",
                    "confidence": 0.8,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        assert result["couche_5_gates"][0]["gate_threshold_value"] == 1500000.5

    def test_applicable_gate_value_oui_string(self):
        fn = self._import()
        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_visit_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": "OUI",
                    "confidence": 0.8,
                }
            ],
            "ambiguites": [],
        }
        result = fn(annotation)
        assert result["couche_5_gates"][0]["gate_value"] is True


class TestBuildLsResult:
    """Tests _build_ls_result()."""

    def _import(self):
        from backend import _build_ls_result

        return _build_ls_result

    def test_structure_conforme_label_studio(self):
        fn = self._import()
        annotation = {"_meta": {"review_required": False}}
        result = fn(annotation, task_id=1, has_errors=False)

        assert "id" in result
        assert "score" in result
        assert "result" in result
        assert len(result["result"]) >= 1

        r = result["result"][0]
        assert r["from_name"] == "extracted_json"
        assert r["to_name"] == "document_text"
        assert r["type"] == "textarea"
        assert isinstance(r["value"]["text"], list)
        assert len(r["value"]["text"]) == 1
        assert isinstance(r["value"]["text"][0], str)
        assert len(r["value"]["text"][0]) > 0

    def test_json_parsable_depuis_textarea(self):
        fn = self._import()
        annotation = {
            "_meta": {"review_required": False},
            "test_key": "test_value",
        }
        result = fn(annotation, task_id=2, has_errors=False)
        json_str = result["result"][0]["value"]["text"][0]
        parsed = json.loads(json_str)
        assert parsed["test_key"] == "test_value"

    def test_score_reduit_si_errors(self):
        fn = self._import()
        annotation = {"_meta": {"review_required": False}}
        result_ok = fn(annotation, task_id=1, has_errors=False)
        result_err = fn(annotation, task_id=2, has_errors=True)
        assert result_ok["score"] > result_err["score"]

    def test_toujours_non_vide_meme_si_review_required(self):
        fn = self._import()
        annotation = {"_meta": {"review_required": True}}
        result = fn(annotation, task_id=3, has_errors=True)
        json_str = result["result"][0]["value"]["text"][0]
        assert len(json_str) > 0, "textarea NE DOIT PAS être vide"

    def test_build_empty_result_non_vide(self):
        from backend import _build_empty_result

        result = _build_empty_result(99, "test_error")
        json_str = result["result"][0]["value"]["text"][0]
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert parsed["_meta"]["review_required"] is True

    def test_identifiants_export_omits_phone_email_raw_keys(self):
        """Export LS (ADR-013) : pas de clés supplier_phone_raw / supplier_email_raw dans le JSON."""
        import json

        from backend import ABSENT, _build_ls_result

        annotation = {
            "_meta": {"review_required": False},
            "identifiants": {
                "supplier_phone_raw": "+33601020304",
                "supplier_email_raw": ABSENT,
            },
        }
        result = _build_ls_result(annotation, task_id=42, has_errors=False)
        parsed = json.loads(result["result"][0]["value"]["text"][0])
        ident = parsed["identifiants"]
        assert "supplier_phone_raw" not in ident
        assert "supplier_email_raw" not in ident
        assert ident["supplier_phone"]["present"] is True
        assert ident["supplier_phone"]["redacted"] is True
        assert ident["supplier_email"]["present"] is False


def test_normalize_identifiants_fills_missing_raw_when_nested_contact_blocks():
    from backend import ABSENT, _normalize_identifiants_for_schema

    ann = {
        "identifiants": {
            "supplier_phone": {"pseudo": None, "present": False, "redacted": False},
            "supplier_email": {"pseudo": None, "present": False, "redacted": False},
        }
    }
    _normalize_identifiants_for_schema(ann)
    assert ann["identifiants"]["supplier_phone_raw"] == ""
    assert ann["identifiants"]["supplier_email_raw"] == ""
    ann2 = {"identifiants": {"supplier_name_raw": "X"}}
    _normalize_identifiants_for_schema(ann2)
    assert ann2["identifiants"]["supplier_phone_raw"] == ABSENT


def test_sync_gate_reasons_replaces_stale_supporting_doc_label():
    from backend import _sync_gate_reasons_with_document_role

    ann = {
        "couche_1_routing": {"document_role": "financial_offer"},
        "couche_5_gates": [
            {
                "gate_name": "gate_eligibility_passed",
                "gate_reason_raw": "Non applicable — document_role = supporting_doc",
            },
        ],
    }
    _sync_gate_reasons_with_document_role(ann)
    assert ann["couche_5_gates"][0]["gate_reason_raw"] == (
        "Non applicable — document_role = financial_offer"
    )


class TestNormalizeGatesJsonReel:
    """Test avec le JSON réel produit par Mistral (Mandat 5)."""

    def test_json_parfait_non_modifie(self):
        """
        Le JSON d'Entraide Africaine Guinée est parfait.
        confidence=1.0 partout.
        _normalize_gates ne doit rien changer.
        """
        from backend import _normalize_gates

        annotation = {
            "couche_5_gates": [
                {
                    "gate_name": "gate_eligibility_passed",
                    "gate_state": "APPLICABLE",
                    "gate_value": True,
                    "confidence": 1.0,
                },
                {
                    "gate_name": "gate_visit_passed",
                    "gate_state": "NOT_APPLICABLE",
                    "gate_value": None,
                    "confidence": 1.0,
                },
                {
                    "gate_name": "gate_negotiation_reached",
                    "gate_state": "APPLICABLE",
                    "gate_value": False,
                    "confidence": 1.0,
                },
            ],
            "ambiguites": [],
        }

        result = _normalize_gates(annotation)

        assert len(result["ambiguites"]) == 0
        for gate in result["couche_5_gates"]:
            assert gate["confidence"] == 1.0


class TestPredictTextGuards:
    """Garde-fous /predict — texte vide ou trop court (PDF vide côté LS)."""

    def test_empty_http_body_returns_empty_results(self) -> None:
        """Corps POST vide — pas d’exception ; 200 + results []."""
        backend = _load_backend_module()
        from starlette.testclient import TestClient

        client = TestClient(backend.app)
        r = client.post(
            "/predict",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json() == {"results": []}

    def test_invalid_json_returns_empty_results(self) -> None:
        backend = _load_backend_module()
        from starlette.testclient import TestClient

        client = TestClient(backend.app)
        r = client.post(
            "/predict",
            content=b"{not json",
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json() == {"results": []}

    def test_empty_text_no_mistral(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = _load_backend_module()
        mistral = AsyncMock(side_effect=RuntimeError("Mistral ne doit pas être appelé"))
        monkeypatch.setattr(backend, "_call_mistral", mistral)
        from starlette.testclient import TestClient

        client = TestClient(backend.app)
        r = client.post(
            "/predict",
            json={"tasks": [{"id": 1, "data": {"text": ""}}]},
        )
        assert r.status_code == 200
        assert mistral.await_count == 0
        data = r.json()
        assert data["results"][0]["id"] == 1

    def test_whitespace_only_treated_as_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = _load_backend_module()
        mistral = AsyncMock(side_effect=RuntimeError("Mistral ne doit pas être appelé"))
        monkeypatch.setattr(backend, "_call_mistral", mistral)
        from starlette.testclient import TestClient

        client = TestClient(backend.app)
        r = client.post(
            "/predict",
            json={"tasks": [{"id": 2, "data": {"text": "  \n\t  "}}]},
        )
        assert r.status_code == 200
        assert mistral.await_count == 0

    def test_text_under_200_chars_text_too_short(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = _load_backend_module()
        mistral = AsyncMock(side_effect=RuntimeError("Mistral ne doit pas être appelé"))
        monkeypatch.setattr(backend, "_call_mistral", mistral)
        from starlette.testclient import TestClient

        client = TestClient(backend.app)
        short = "a" * 199
        r = client.post(
            "/predict",
            json={"tasks": [{"id": 99, "data": {"text": short}}]},
        )
        assert r.status_code == 200
        assert mistral.await_count == 0
        payload = r.json()["results"][0]["result"][0]["value"]["text"][0]
        assert "text_too_short" in payload


class TestDeterministicRoutingArch02:
    """ARCH-02 — routeur déterministe + fallback enums."""

    def test_financial_header_overwrites_routing(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "rfq"
        ann["couche_1_routing"]["document_role"] = "source_rules"
        text = "# PROPOSITION FINANCIÈRE\n" + "x" * 500
        out = backend._apply_deterministic_routing(ann, text, 1)
        assert out["couche_1_routing"]["taxonomy_core"] == "offer_financial"
        assert out["couche_1_routing"]["document_role"] == "financial_offer"
        assert out["_meta"]["routing_source"] == "deterministic_classifier"
        assert out["_meta"]["routing_matched_rule"] == "P0_financial_title_header"

    def test_llm_invalid_enum_becomes_unknown(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "not_a_real_taxonomy"
        ann["couche_1_routing"]["document_role"] = "not_a_role"
        text = "hello " * 400
        out = backend._apply_deterministic_routing(ann, text, 2)
        assert out["couche_1_routing"]["taxonomy_core"] == "unknown"
        assert out["couche_1_routing"]["document_role"] == "unknown"
        assert out["_meta"]["routing_source"] == "llm_fallback_unresolved"

    def test_llm_valid_enum_keeps_routing(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "rfq"
        ann["couche_1_routing"]["document_role"] = "source_rules"
        text = "hello " * 400
        out = backend._apply_deterministic_routing(ann, text, 3)
        assert out["couche_1_routing"]["taxonomy_core"] == "rfq"
        assert out["couche_1_routing"]["document_role"] == "source_rules"
        assert out["_meta"]["routing_source"] == "llm_fallback_validated"


class TestFinancialReviewArch04:
    """ARCH-04 — review_required sur offre financière (prudence locale)."""

    def test_non_financial_untouched(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "rfq"
        ann["_meta"]["review_required"] = False
        out = backend._apply_financial_offer_review_rules(ann)
        assert out is ann
        assert out["_meta"].get("review_reasons") in (None, [])

    def _sample_line_item(self) -> dict:
        return {
            "item_line_no": 1,
            "item_description_raw": "x",
            "unit_raw": "u",
            "quantity": 1.0,
            "unit_price": 10.0,
            "line_total": 10.0,
            "line_total_check": "OK",
            "confidence": 1.0,
            "evidence": "p.1",
        }

    def test_invalid_financial_review_threshold_env_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = _load_backend_module()
        monkeypatch.setenv("FINANCIAL_REVIEW_THRESHOLD_XOF", "totally_bad")
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "offer_financial"
        ann["couche_1_routing"]["document_role"] = "financial_offer"
        ann["couche_4_atomic"]["financier"]["line_items"] = [self._sample_line_item()]
        ann["couche_4_atomic"]["financier"]["total_price"] = {
            "value": "11000000",
            "confidence": 1.0,
            "evidence": "p.1",
        }
        ann["_meta"] = {"review_required": False}
        out = backend._apply_financial_offer_review_rules(ann)
        reasons = out["_meta"].get("review_reasons") or []
        assert any("high_value_above" in r for r in reasons)

    def test_total_price_with_narrow_nbsp_triggers_high_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = _load_backend_module()
        monkeypatch.setenv("FINANCIAL_REVIEW_THRESHOLD_XOF", "1000000")
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "offer_financial"
        ann["couche_1_routing"]["document_role"] = "financial_offer"
        ann["couche_4_atomic"]["financier"]["line_items"] = [self._sample_line_item()]
        ann["couche_4_atomic"]["financier"]["total_price"] = {
            "value": "15\u202f000\u202f000",
            "confidence": 1.0,
            "evidence": "p.1",
        }
        ann["_meta"] = {"review_required": False}
        out = backend._apply_financial_offer_review_rules(ann)
        reasons = out["_meta"].get("review_reasons") or []
        assert any("high_value_above" in r for r in reasons)

    def test_financial_empty_line_items_triggers_review(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "offer_financial"
        ann["couche_1_routing"]["document_role"] = "financial_offer"
        ann["couche_4_atomic"]["financier"]["line_items"] = []
        ann["_meta"]["review_required"] = False
        out = backend._apply_financial_offer_review_rules(
            ann, total_price_threshold=1e12
        )
        assert out["_meta"]["review_required"] is True
        assert "line_items_empty_on_financial_offer" in out["_meta"]["review_reasons"]

    def test_financial_anomaly_line_triggers_review(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["couche_1_routing"]["taxonomy_core"] = "offer_financial"
        ann["couche_4_atomic"]["financier"]["line_items"] = [
            {
                "item_line_no": 1,
                "item_description_raw": "x",
                "unit_raw": "u",
                "quantity": 1.0,
                "unit_price": 10.0,
                "line_total": 999.0,
                "line_total_check": "ANOMALY",
                "confidence": 1.0,
                "evidence": "p.1",
            }
        ]
        ann["_meta"]["review_required"] = False
        out = backend._apply_financial_offer_review_rules(
            ann, total_price_threshold=1e12
        )
        assert out["_meta"]["review_required"] is True
        assert any(
            x.startswith("arithmetic_anomaly_item_")
            for x in out["_meta"]["review_reasons"]
        )


class TestJsonFixAnnotValidatePipeline:
    """JSON-FIX-ANNOT-01-v2 — _validate_and_correct normalise avant model_validate."""

    def test_hierarchical_item_line_no_passes_schema(self) -> None:
        backend = _load_backend_module()
        ann = copy.deepcopy(backend.FALLBACK_RESPONSE)
        ann["ambiguites"] = []
        ann["couche_4_atomic"]["financier"]["total_price"] = {
            "value": 200.0,
            "confidence": 1.0,
            "evidence": "p.1",
        }
        ann["couche_4_atomic"]["financier"]["line_items"] = [
            {
                "item_line_no": 1.1,
                "item_description_raw": "Ligne",
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
        out, errors = backend._validate_and_correct(ann, 1)
        assert errors == []
        assert out["couche_4_atomic"]["financier"]["line_items"][0]["item_line_no"] == 1
        assert (
            "parent_subtotal_no"
            not in out["couche_4_atomic"]["financier"]["line_items"][0]
        )


def test_normalize_annotation_output_importable():
    """JSON-FIX-ANNOT-01-v2 — même module que le backend (/predict)."""
    from prompts.schema_validator import normalize_annotation_output

    d = {"_meta": {"review_required": False}, "ambiguites": []}
    out = normalize_annotation_output(d)
    assert out["_meta"]["review_required"] is False
