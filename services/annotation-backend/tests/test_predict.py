"""
Tests intégration /predict — Mandat 5.
Vérifie la structure Label Studio et la normalisation gates.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from unittest.mock import AsyncMock


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

    module = importlib.util.module_from_spec(spec)
    # Enregistrer le module pour que les imports internes fonctionnent éventuellement
    sys.modules.setdefault("backend", module)
    spec.loader.exec_module(module)
    _BACKEND_MODULE = module
    return module


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

    def test_whitespace_only_treated_as_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
