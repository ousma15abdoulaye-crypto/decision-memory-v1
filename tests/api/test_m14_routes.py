"""M14 Evaluation Engine — API route integration tests.

GAP-7 hardening: typed responses, auth enforcement, 404 handling,
and OpenAPI schema contract validation on both entrypoints.

Auth-401 tests require a running Postgres instance (middleware dependency);
they are skipped locally when the DB is unreachable and enforced in CI.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.procurement.m14_evaluation_models import (
    EvaluationDocumentEnvelope,
    EvaluationReport,
    M14StatusResponse,
)


def _db_reachable() -> bool:
    """Return True if the local Postgres accepts connections."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    try:
        conn = psycopg.connect(
            url.replace("postgresql+psycopg://", "postgresql://"),
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


_skip_no_db = pytest.mark.skipif(
    not _db_reachable(),
    reason="Postgres unreachable — auth-401 tests require DB (runs in CI)",
)


def _fake_user() -> UserClaims:
    return UserClaims(
        user_id="42",
        role="admin",
        jti="test-jti-m14",
        tenant_id="tenant-test",
    )


MINIMAL_INPUT: dict[str, Any] = {
    "case_id": "case-m14-test",
    "source_rules_document_id": "doc-src-1",
    "offers": [
        {
            "document_id": "offer-1",
            "supplier_name": "Supplier A",
            "process_role": "offer_technical",
            "present_admin_subtypes": ["nif"],
            "capability_sections_present": ["methodology"],
            "currency": "XOF",
            "total_price": 5_000_000,
        },
    ],
    "h2_capability_skeleton": {
        "procurement_family": "goods",
        "active_capability_sections": ["methodology", "workplan"],
        "scoring_structure": {
            "criteria": [
                {"criteria_name": "methodology", "weight_percent": 60.0},
                {"criteria_name": "experience", "weight_percent": 40.0},
            ],
            "ponderation_coherence": "OK",
        },
    },
    "h3_market_context": {
        "prices_detected": True,
        "currency_detected": "XOF",
        "material_price_index_applicable": False,
        "material_categories_detected": [],
        "zone_for_price_reference": ["bamako"],
    },
    "rh1_compliance_checklist": {
        "per_offer_checks": [
            {
                "check_id": "G-NIF",
                "check_name": "NIF",
                "verification_method": "document_presence",
                "is_eliminatory": True,
                "expected_admin_subtype": "nif",
            },
        ],
        "case_level_checks": [],
    },
    "rh2_evaluation_blueprint": {
        "evaluation_method": "mieux_disant",
        "procedure_requirements_ref": "m13/case-m14-test/latest",
    },
}

KILL_LIST_FIELDS = {"winner", "rank", "recommendation", "best_offer"}


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture()
def _m14_auth_override():
    """Override auth for both apps to avoid JWT/DB login."""
    from main import app as root_app
    from src.api.main import app as modular_app

    for a in (root_app, modular_app):
        a.dependency_overrides[get_current_user] = _fake_user
    yield
    for a in (root_app, modular_app):
        a.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def root_client() -> TestClient:
    from main import app

    return TestClient(app)


@pytest.fixture()
def modular_client() -> TestClient:
    from src.api.main import app

    return TestClient(app)


# =====================================================================
# AUTH enforcement (no token = 401)
# =====================================================================


@_skip_no_db
class TestM14Auth:
    """Routes M14 require Bearer auth — 401 without token.

    Requires a running Postgres because the TenantContextMiddleware
    opens a DB connection before the auth dependency rejects the request.
    """

    def test_status_without_token_401(self, modular_client: TestClient) -> None:
        r = modular_client.get("/api/m14/status")
        assert r.status_code == 401

    def test_evaluate_without_token_401(self, modular_client: TestClient) -> None:
        r = modular_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 401

    def test_get_evaluation_without_token_401(self, modular_client: TestClient) -> None:
        r = modular_client.get("/api/m14/evaluations/case-does-not-exist")
        assert r.status_code == 401

    def test_root_app_status_without_token_401(self, root_client: TestClient) -> None:
        r = root_client.get("/api/m14/status")
        assert r.status_code == 401

    def test_root_app_evaluate_without_token_401(self, root_client: TestClient) -> None:
        r = root_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 401


# =====================================================================
# GET /status — typed response
# =====================================================================


class TestM14Status:
    @pytest.mark.usefixtures("_m14_auth_override")
    def test_status_returns_typed_response(self, modular_client: TestClient) -> None:
        r = modular_client.get("/api/m14/status")
        assert r.status_code == 200
        parsed = M14StatusResponse.model_validate(r.json())
        assert parsed.module == "M14 Evaluation Engine"
        assert parsed.version == "1.0.0"

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_root_status_returns_typed_response(self, root_client: TestClient) -> None:
        r = root_client.get("/api/m14/status")
        assert r.status_code == 200
        M14StatusResponse.model_validate(r.json())


# =====================================================================
# POST /evaluate — typed response + REGLE-09 kill list
# =====================================================================


class TestM14Evaluate:
    @pytest.mark.usefixtures("_m14_auth_override")
    def test_evaluate_returns_evaluation_report(
        self, modular_client: TestClient
    ) -> None:
        r = modular_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 200
        report = EvaluationReport.model_validate(r.json())
        assert report.case_id == "case-m14-test"
        assert report.evaluation_method == "mieux_disant"
        assert report.total_offers_evaluated == 1
        assert len(report.offer_evaluations) == 1

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_evaluate_kill_list_absent(self, modular_client: TestClient) -> None:
        """REGLE-09: forbidden fields never appear in response."""
        r = modular_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 200
        data = r.json()
        for field in KILL_LIST_FIELDS:
            assert field not in data, f"REGLE-09 violation: {field} in response"

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_evaluate_confidences_in_allowed_set(
        self, modular_client: TestClient
    ) -> None:
        r = modular_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 200
        confidences = _collect_confidences(r.json())
        allowed = {0.6, 0.8, 1.0}
        for c in confidences:
            assert c in allowed, f"confidence={c} not in {allowed}"

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_evaluate_extra_field_rejected_422(
        self, modular_client: TestClient
    ) -> None:
        """E-49: extra=forbid on M14EvaluationInput rejects unknown fields."""
        bad = {**MINIMAL_INPUT, "winner": "Supplier A"}
        r = modular_client.post("/api/m14/evaluate", json=bad)
        assert r.status_code == 422

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_root_evaluate_returns_evaluation_report(
        self, root_client: TestClient
    ) -> None:
        r = root_client.post("/api/m14/evaluate", json=MINIMAL_INPUT)
        assert r.status_code == 200
        EvaluationReport.model_validate(r.json())

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_evaluate_empty_offers_review_required(
        self, modular_client: TestClient
    ) -> None:
        payload = {**MINIMAL_INPUT, "offers": []}
        r = modular_client.post("/api/m14/evaluate", json=payload)
        assert r.status_code == 200
        report = EvaluationReport.model_validate(r.json())
        assert report.total_offers_evaluated == 0
        assert "no_offers_provided" in report.m14_meta.review_reasons


# =====================================================================
# GET /evaluations/{case_id} — 404 + typed envelope
# =====================================================================


class TestM14GetEvaluation:
    @pytest.mark.usefixtures("_m14_auth_override")
    def test_get_evaluation_not_found_404(self, modular_client: TestClient) -> None:
        r = modular_client.get("/api/m14/evaluations/case-nonexistent")
        assert r.status_code == 404
        assert "case-nonexistent" in r.json().get("detail", "")

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_root_get_evaluation_not_found_404(self, root_client: TestClient) -> None:
        r = root_client.get("/api/m14/evaluations/case-nonexistent")
        assert r.status_code == 404


# =====================================================================
# OpenAPI schema contract — both apps expose typed M14 operations
# =====================================================================


class TestM14OpenAPIContract:
    """Verify that OpenAPI schema advertises M14 response models."""

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_modular_openapi_m14_operations(self, modular_client: TestClient) -> None:
        r = modular_client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        paths = schema.get("paths", {})

        assert "/api/m14/status" in paths
        assert "/api/m14/evaluate" in paths
        assert "/api/m14/evaluations/{case_id}" in paths

        status_get = paths["/api/m14/status"].get("get", {})
        resp_200 = status_get.get("responses", {}).get("200", {})
        assert resp_200, "/api/m14/status missing 200 response in OpenAPI"

        evaluate_post = paths["/api/m14/evaluate"].get("post", {})
        resp_200 = evaluate_post.get("responses", {}).get("200", {})
        assert resp_200, "/api/m14/evaluate missing 200 response in OpenAPI"

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_root_openapi_m14_operations(self, root_client: TestClient) -> None:
        r = root_client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/api/m14/status" in paths
        assert "/api/m14/evaluate" in paths
        assert "/api/m14/evaluations/{case_id}" in paths

    @pytest.mark.usefixtures("_m14_auth_override")
    def test_openapi_schemas_include_evaluation_report(
        self, modular_client: TestClient
    ) -> None:
        r = modular_client.get("/openapi.json")
        schemas = r.json().get("components", {}).get("schemas", {})
        assert (
            "EvaluationReport" in schemas
        ), "EvaluationReport not in OpenAPI schemas — response_model not wired"
        assert "M14StatusResponse" in schemas
        assert "EvaluationDocumentEnvelope" in schemas


# =====================================================================
# EvaluationDocumentEnvelope unit validation
# =====================================================================


class TestEvaluationDocumentEnvelope:
    """Verify the envelope model correctly wraps DB rows."""

    def test_valid_envelope(self) -> None:
        report_data = EvaluationReport(
            case_id="c1",
            evaluation_method="lowest_price",
        ).model_dump(mode="json")

        envelope = EvaluationDocumentEnvelope.model_validate(
            {
                "id": "abc-123",
                "case_id": "c1",
                "version": 1,
                "scores_matrix": report_data,
                "justifications": {},
                "status": "draft",
                "created_at": "2026-04-03T10:00:00+00:00",
            }
        )
        assert isinstance(envelope.scores_matrix, EvaluationReport)
        assert envelope.scores_matrix.case_id == "c1"

    def test_extra_field_rejected(self) -> None:
        """E-49: extra=forbid."""
        with pytest.raises(ValidationError):
            EvaluationDocumentEnvelope.model_validate(
                {
                    "id": "abc",
                    "case_id": "c1",
                    "version": 1,
                    "scores_matrix": {"case_id": "c1", "evaluation_method": "unknown"},
                    "status": "draft",
                    "created_at": "2026-04-03T10:00:00",
                    "unexpected_field": True,
                }
            )

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvaluationDocumentEnvelope.model_validate(
                {
                    "id": "abc",
                    "case_id": "c1",
                    "version": 1,
                    "scores_matrix": {"case_id": "c1", "evaluation_method": "unknown"},
                    "status": "INVALID_STATUS",
                    "created_at": "2026-04-03T10:00:00",
                }
            )


# =====================================================================
# Helpers
# =====================================================================


def _collect_confidences(obj: object) -> list[float]:
    found: list[float] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "confidence" and isinstance(v, (int, float)):
                found.append(float(v))
            else:
                found.extend(_collect_confidences(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_confidences(item))
    return found
