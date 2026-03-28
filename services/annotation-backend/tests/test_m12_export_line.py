"""
Tests m12_export_line — causes racines corpus inexploitable.

Couverture :
  1. _normalize_identifiants_for_ls_reimport : supplier_phone_raw / email_raw
     manquants (ADR-013) → ajoutés avant DMSAnnotation.model_validate.
  2. raw_json_text conservé dans la ligne même si schéma échoue.
  3. ls_annotation_to_m12_v2_line end-to-end avec JSON LS réaliste.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(_BACKEND_DIR), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PSEUDONYM_SALT", os.environ.get("PSEUDONYM_SALT", "test-sel-m12-export")
    )
    monkeypatch.setenv("ALLOW_WEAK_PSEUDONYMIZATION", "1")


# ─── Helpers ────────────────────────────────────────────────────────────────


def _minimal_ls_textarea_json() -> dict:
    """
    JSON minimal valide après export LS (supplier_phone_raw / email_raw absents —
    supprimés par _build_ls_result selon ADR-013).
    """
    import copy

    from backend import FALLBACK_RESPONSE

    ann = copy.deepcopy(FALLBACK_RESPONSE)
    # Simuler ce que _build_ls_result fait : supprimer les _raw, ajouter blocs pseudos
    ident = ann.setdefault("identifiants", {})
    ident.pop("supplier_phone_raw", None)
    ident.pop("supplier_email_raw", None)
    ident["supplier_phone"] = {"pseudo": None, "present": False, "redacted": False}
    ident["supplier_email"] = {"pseudo": None, "present": False, "redacted": False}
    # Routing_source requis par Meta (optionnel dans le modèle mais peut manquer)
    ann.setdefault("_meta", {})
    return ann


def _build_task(text: str = "Texte source du document.") -> dict:
    return {"id": 42, "data": {"text": text}}


def _build_ann(json_payload: dict, status: str = "review_required") -> dict:
    return {
        "id": 7,
        "result": [
            {
                "from_name": "extracted_json",
                "to_name": "document_text",
                "type": "textarea",
                "value": {"text": [json.dumps(json_payload, ensure_ascii=False)]},
            },
            {
                "from_name": "annotation_status",
                "to_name": "annotation_status_choice",
                "type": "choices",
                "value": {"choices": [status]},
            },
        ],
    }


# ─── Tests _normalize_identifiants_for_ls_reimport ──────────────────────────


class TestNormalizeIdentifiantsForLsReimport:
    def test_adds_phone_raw_when_bloc_present(self) -> None:
        from m12_export_line import _normalize_identifiants_for_ls_reimport

        ann = {
            "identifiants": {
                "supplier_phone": {"pseudo": None, "present": False, "redacted": False}
            }
        }
        _normalize_identifiants_for_ls_reimport(ann)
        assert ann["identifiants"]["supplier_phone_raw"] == ""

    def test_adds_email_raw_when_bloc_present(self) -> None:
        from m12_export_line import _normalize_identifiants_for_ls_reimport

        ann = {
            "identifiants": {
                "supplier_email": {"pseudo": "x@y.com", "present": True, "redacted": True}
            }
        }
        _normalize_identifiants_for_ls_reimport(ann)
        assert ann["identifiants"]["supplier_email_raw"] == ""

    def test_adds_absent_when_no_bloc(self) -> None:
        from m12_export_line import _normalize_identifiants_for_ls_reimport

        ann = {"identifiants": {}}
        _normalize_identifiants_for_ls_reimport(ann)
        assert ann["identifiants"]["supplier_phone_raw"] == "ABSENT"
        assert ann["identifiants"]["supplier_email_raw"] == "ABSENT"

    def test_does_not_overwrite_existing(self) -> None:
        from m12_export_line import _normalize_identifiants_for_ls_reimport

        ann = {
            "identifiants": {
                "supplier_phone_raw": "explicit",
                "supplier_email_raw": "existing",
            }
        }
        _normalize_identifiants_for_ls_reimport(ann)
        assert ann["identifiants"]["supplier_phone_raw"] == "explicit"
        assert ann["identifiants"]["supplier_email_raw"] == "existing"

    def test_noop_when_no_identifiants_key(self) -> None:
        from m12_export_line import _normalize_identifiants_for_ls_reimport

        ann: dict = {}
        _normalize_identifiants_for_ls_reimport(ann)
        assert "identifiants" not in ann


# ─── Tests ls_annotation_to_m12_v2_line ─────────────────────────────────────


class TestLsAnnotationToM12V2Line:
    def test_raw_json_text_preserved_on_parse_error(self) -> None:
        """raw_json_text doit être stocké même si le JSON ne parse pas."""
        from m12_export_line import ls_annotation_to_m12_v2_line

        broken_json = "{not valid json {{{"
        ann = {
            "id": 1,
            "result": [
                {
                    "from_name": "extracted_json",
                    "to_name": "document_text",
                    "type": "textarea",
                    "value": {"text": [broken_json]},
                }
            ],
        }
        task = _build_task()
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=1)
        assert line["raw_json_text"] == broken_json
        assert line["dms_annotation"] is None
        assert any("json_parse_error" in e for e in line["export_errors"])

    def test_raw_json_text_none_when_extracted_json_empty(self) -> None:
        """Si extracted_json absent/vide, raw_json_text est None."""
        from m12_export_line import ls_annotation_to_m12_v2_line

        ann = {"id": 2, "result": []}
        task = _build_task()
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=1)
        assert line["raw_json_text"] is None
        assert any("missing_extracted_json" in e for e in line["export_errors"])

    def test_schema_validation_succeeds_with_fallback_json_from_ls(self) -> None:
        """
        Simulation du cas réel : JSON issu du textarea LS (sans supplier_phone_raw).
        Sans _normalize_identifiants_for_ls_reimport → schema_validation error.
        Avec → export_ok=True.
        """
        from m12_export_line import ls_annotation_to_m12_v2_line

        payload = _minimal_ls_textarea_json()
        ann = _build_ann(payload)
        task = _build_task()
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=1)
        schema_errors = [e for e in line["export_errors"] if "schema_validation" in e]
        assert schema_errors == [], (
            f"schema_validation doit réussir avec normalisation ADR-013. Erreurs: {schema_errors}"
        )
        assert line["dms_annotation"] is not None
        assert line["raw_json_text"] is not None

    def test_raw_json_text_stored_even_on_schema_error(self) -> None:
        """Si schema échoue, raw_json_text doit quand même être disponible."""
        from m12_export_line import ls_annotation_to_m12_v2_line

        invalid = {"some": "random", "keys": [1, 2, 3]}
        ann = _build_ann(invalid)
        task = _build_task()
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=1)
        assert line["raw_json_text"] is not None
        assert line["dms_annotation"] is None
        assert any("schema_validation" in e for e in line["export_errors"])

    def test_export_schema_version_is_m12_v2(self) -> None:
        from m12_export_line import ls_annotation_to_m12_v2_line

        ann = {"id": 99, "result": []}
        task = _build_task()
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=5)
        assert line["export_schema_version"] == "m12-v2"

    def test_ls_meta_contains_task_and_annotation_ids(self) -> None:
        from m12_export_line import ls_annotation_to_m12_v2_line

        ann = {"id": 77, "result": []}
        task = {"id": 123, "data": {"text": "x" * 200}}
        line = ls_annotation_to_m12_v2_line(ann, task, project_id=3)
        assert line["ls_meta"]["task_id"] == 123
        assert line["ls_meta"]["annotation_id"] == 77
        assert line["ls_meta"]["project_id"] == 3
