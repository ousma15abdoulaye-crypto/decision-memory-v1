"""
Tests intégration /predict — Mandat 5.
Vérifie la structure Label Studio et la normalisation gates.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configurer l'environnement requis pour le backend pour chaque test.

    On utilise monkeypatch.setenv pour éviter de modifier l'état global
    du process pytest au moment de l'import du module de test.
    """
    monkeypatch.setenv("PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-sel-mandat5"))
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", os.environ.get("ALLOW_WEAK_PSEUDONYMIZATION", "1"))
    monkeypatch.setenv("MISTRAL_API_KEY", os.environ.get("MISTRAL_API_KEY", ""))


# Import backend depuis le répertoire parent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestNormalizeGates:
    """Tests _normalize_gates()."""

    def _import(self):
        from backend import _normalize_gates

        return _normalize_gates

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

    def test_applicable_gate_value_null_force_false(self):
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
        ambiguites = result["ambiguites"]
        assert gate["gate_value"] is False
        assert any("gate_negotiation_reached" in a for a in ambiguites)

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
        assert r["to_name"] == "text"
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
