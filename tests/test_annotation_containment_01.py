"""
M-ANNOTATION-CONTAINMENT-01 — garde-fous entrée + spot-check + zéro LLM si texte court.
Périmètre : services/annotation-backend/backend.py (via importlib) + assertions couche A.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

BACKEND_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "annotation-backend"
    / "backend.py"
)


@pytest.fixture(autouse=True)
def _containment_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """backend.py refuse de s'importer sans sel — défaut test."""
    monkeypatch.setenv("PSEUDONYM_SALT", "test-salt-containment")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")


def _load_backend():
    """Charge backend.py à chaque appel (ré-exec pour ENV à jour)."""
    name = "ab_containment_backend"
    spec = importlib.util.spec_from_file_location(name, BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"backend load fail {BACKEND_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    be_root = str(BACKEND_PATH.parent)
    spec.loader.exec_module(mod)
    # backend.py fait sys.path.insert(0, ...) à chaque import — éviter les doublons.
    while len(sys.path) > 1 and sys.path[0] == be_root and sys.path[1] == be_root:
        sys.path.pop(0)
    return mod


@pytest.fixture
def backend_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-salt-containment")
    )
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "")
    return _load_backend()


def test_predict_text_insufficient_no_llm(monkeypatch: pytest.MonkeyPatch):
    """text_len_norm < MIN → BLOCK, score 0, pas d'appel Mistral."""
    monkeypatch.setenv("PSEUDONYM_SALT", "test-salt-containment")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key-for-client-exists")
    mod = _load_backend()
    mod.client = MagicMock()
    client = TestClient(mod.app)
    body = {
        "document_id": "doc-test-1",
        "tasks": [{"id": 7, "data": {"text": "short" * 10}}],  # 50 chars
    }
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    mod.client.chat.complete.assert_not_called()
    res = r.json()["results"][0]
    assert res["score"] == 0.0
    inner = json.loads(res["result"][0]["value"]["text"][0])
    assert inner["_meta"]["review_required"] is True
    assert "text_insufficient" in inner["_meta"]["error_reason"]


def test_predict_empty_text_field_content_fallback(
    backend_module, monkeypatch: pytest.MonkeyPatch
):
    """data.text vide mais data.content assez long → utilise content."""
    monkeypatch.setenv("MISTRAL_API_KEY", "")
    mod = _load_backend()
    client = TestClient(mod.app)
    long_content = "Y" * 120
    body = {"tasks": [{"id": 2, "data": {"text": "", "content": long_content}}]}
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    # Pas de client → fallback interne sans HTTP externe réelle
    res = r.json()["results"][0]
    assert res["id"] == 2


def test_build_messages_rejects_short():
    mod = _load_backend()
    with pytest.raises(ValueError, match="INSUFFICIENT_TEXT_FOR_LLM"):
        mod._build_messages("x" * 50, document_role="")


def test_spot_check_supplier_not_in_source_flags_review():
    mod = _load_backend()
    ann = {
        "identifiants": {"supplier_name_raw": "InventedVendorXYZ"},
        "ambiguites": [],
        "_meta": {},
    }
    out = mod._spot_check_annotation_vs_source(
        ann,
        "Le soumissionnaire est Acme Corp uniquement pour ce marché.",
        99,
    )
    assert "AMBIG-SPOT-supplier_not_in_source" in out["ambiguites"]
    assert out["_meta"]["review_required"] is True


def test_spot_check_supplier_in_source_clean():
    mod = _load_backend()
    ann = {
        "identifiants": {"supplier_name_raw": "Acme Corp"},
        "ambiguites": [],
        "_meta": {},
    }
    out = mod._spot_check_annotation_vs_source(
        ann,
        "Le soumissionnaire est Acme Corp uniquement.",
        1,
    )
    assert "AMBIG-SPOT-supplier_not_in_source" not in out.get("ambiguites", [])


def test_spot_check_total_not_in_source_flags_review():
    mod = _load_backend()
    ann = {
        "identifiants": {},
        "couche_4_atomic": {
            "financier": {"total_price": {"value": "999999.00", "confidence": 0.8}}
        },
        "ambiguites": [],
        "_meta": {},
    }
    out = mod._spot_check_annotation_vs_source(
        ann,
        "Devis sans aucun montant numérique long dans le corps.",
        42,
    )
    assert "AMBIG-SPOT-total_not_in_source" in out["ambiguites"]
    assert out["_meta"]["review_required"] is True


def test_fallback_response_validates_dms_annotation():
    """M-CONTRACT-02 : squelette FALLBACK = 0 erreur Pydantic (sans assouplir le schéma)."""
    mod = _load_backend()
    sys.path.insert(0, str(BACKEND_PATH.parent))
    from prompts.schema_validator import DMSAnnotation

    DMSAnnotation.model_validate(mod.FALLBACK_RESPONSE)
    assert len(mod.FALLBACK_RESPONSE["couche_5_gates"]) == 10
    assert "AMBIG-PARSE_FAILED" in mod.FALLBACK_RESPONSE["ambiguites"]


def test_validate_and_correct_fallback_zero_schema_errors():
    """Même annotation qu’après parse Mistral → _validate_and_correct sans erreurs schéma."""
    mod = _load_backend()
    ann = copy.deepcopy(mod.FALLBACK_RESPONSE)
    _fixed, errors = mod._validate_and_correct(ann, task_id=42)
    assert errors == []


def test_predict_mock_fallback_no_validate_errors_logged(caplog, monkeypatch):
    """Cas valide + mock renvoie FALLBACK : pas de log « N erreurs schema »."""
    monkeypatch.setenv("PSEUDONYM_SALT", "test-salt-containment")
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key")
    mod = _load_backend()
    mod.client = MagicMock()
    rmock = MagicMock()
    rmock.choices = [MagicMock()]
    rmock.choices[0].message.content = json.dumps(mod.FALLBACK_RESPONSE)
    mod.client.chat.complete.return_value = rmock
    with caplog.at_level("ERROR"):
        with TestClient(mod.app) as client:
            r = client.post(
                "/predict",
                json={
                    "document_id": "contract-02",
                    "tasks": [{"id": 5, "data": {"text": "Z" * 200}}],
                },
            )
    assert r.status_code == 200
    assert "erreurs schema" not in caplog.text


def test_spot_check_invalid_meta_amb_types_non_destructive():
    """_meta / ambiguites mal typés → normalisés, pas d'exception."""
    mod = _load_backend()
    ann = {
        "identifiants": {"supplier_name_raw": "GhostCo"},
        "ambiguites": "not-a-list",
        "_meta": "broken",
    }
    out = mod._spot_check_annotation_vs_source(
        ann,
        "Le soumissionnaire GhostCo est cite ici.",
        77,
    )
    assert isinstance(out["_meta"], dict)
    assert isinstance(out["ambiguites"], list)


def test_normalize_input_text_collapses_whitespace():
    mod = _load_backend()
    assert mod._normalize_input_text("  a \n\t b  ") == "a b"
