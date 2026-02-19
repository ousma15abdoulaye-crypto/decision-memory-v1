# tests/phase0/test_extraction_engine_api.py
"""
Tests API — M-EXTRACTION-ENGINE endpoints.
🔴 BLOQUANTS CI.
Constitution V3.3.2 §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────

FAKE_DOC_PDF = {
    "id": "doc-test-pdf-001",
    "mime_type": "application/pdf",
    "storage_uri": "/tmp/test.pdf",
    "extraction_status": "pending",
    "extraction_method": "native_pdf",
}

FAKE_DOC_SCAN = {
    "id": "doc-test-scan-001",
    "mime_type": "image/tiff",
    "storage_uri": "/tmp/test.tif",
    "extraction_status": "pending",
    "extraction_method": "tesseract",
}

FAKE_DOC_DONE = {
    "id": "doc-test-done-001",
    "mime_type": "application/pdf",
    "storage_uri": "/tmp/done.pdf",
    "extraction_status": "done",
    "extraction_method": "native_pdf",
}

FAKE_EXTRACT_RESULT_SLA_A = {
    "document_id": "doc-test-pdf-001",
    "status": "done",
    "method": "native_pdf",
    "sla_class": "A",
    "duration_ms": 1200.0,
    "confidence": 0.85,
    "requires_human_review": False,
}

FAKE_EXTRACT_RESULT_SLA_B = {
    "document_id": "doc-test-scan-001",
    "job_id": "job-test-001",
    "status": "pending",
    "sla_class": "B",
    "method": "tesseract",
    "message": "Extraction OCR mise en queue.",
}

FAKE_JOB = {
    "id": "job-test-001",
    "document_id": "doc-test-scan-001",
    "status": "pending",
    "method": "tesseract",
    "sla_class": "B",
    "queued_at": "2024-01-01T10:00:00+00:00",
    "started_at": None,
    "completed_at": None,
    "duration_ms": None,
    "error_message": None,
}

FAKE_EXTRACTION_ROW = {
    "document_id": "doc-test-pdf-001",
    "raw_text": "Contenu extrait du document PDF.",
    "structured_data": {"doc_kind": None, "_low_confidence": False},
    "extraction_method": "native_pdf",
    "confidence_score": 0.85,
    "extracted_at": "2024-01-01T10:01:00+00:00",
}

FAKE_EXTRACTION_LOW_CONF = {
    "document_id": "doc-test-pdf-001",
    "raw_text": "x",
    "structured_data": {"_low_confidence": True},
    "extraction_method": "native_pdf",
    "confidence_score": 0.3,
    "extracted_at": "2024-01-01T10:01:00+00:00",
}


# ── Classe 1 — POST /extract SLA-A ──────────────────────────────

class TestTriggerExtractionSLAA:
    """SLA-A : extraction synchrone PDF natif."""

    def test_sla_a_returns_202_done(self):
        """PDF natif → 202 + status done + sla_class A."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_PDF,
        ), patch(
            "src.api.routes.extractions.extract_sync",
            return_value=FAKE_EXTRACT_RESULT_SLA_A,
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-pdf-001/extract"
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "done"
        assert data["sla_class"] == "A"
        assert data["method"] == "native_pdf"

    def test_sla_a_duration_sous_60s(self):
        """SLA-A : duration_ms < 60000 dans la réponse."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_PDF,
        ), patch(
            "src.api.routes.extractions.extract_sync",
            return_value=FAKE_EXTRACT_RESULT_SLA_A,
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-pdf-001/extract"
            )

        data = response.json()
        assert data["duration_ms"] < 60_000

    def test_sla_a_timeout_returns_504(self):
        """SLA-A TimeoutError → 504."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_PDF,
        ), patch(
            "src.api.routes.extractions.extract_sync",
            side_effect=TimeoutError("SLA-A violé : 65000ms"),
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-pdf-001/extract"
            )

        assert response.status_code == 504
        assert "SLA-A" in response.json()["detail"]


# ── Classe 2 — POST /extract SLA-B ──────────────────────────────

class TestTriggerExtractionSLAB:
    """SLA-B : extraction asynchrone OCR."""

    def test_sla_b_returns_202_pending(self):
        """Scan OCR → 202 + status pending + job_id."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_SCAN,
        ), patch(
            "src.api.routes.extractions.extract_async",
            return_value=FAKE_EXTRACT_RESULT_SLA_B,
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-scan-001/extract"
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["sla_class"] == "B"
        assert data["job_id"] is not None

    def test_sla_b_retourne_job_id(self):
        """SLA-B : job_id non null dans la réponse."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_SCAN,
        ), patch(
            "src.api.routes.extractions.extract_async",
            return_value=FAKE_EXTRACT_RESULT_SLA_B,
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-scan-001/extract"
            )

        data = response.json()
        assert data["job_id"] == "job-test-001"


# ── Classe 3 — Erreurs §9 ────────────────────────────────────────

class TestErreurs:
    """§9 : erreurs explicites jamais masquées."""

    def test_document_inconnu_returns_404(self):
        """Document inexistant → 404 avec message explicite."""
        with patch(
            "src.api.routes.extractions._get_document",
            side_effect=ValueError("Document 'xyz' introuvable."),
        ):
            response = client.post(
                "/api/extractions/documents/xyz/extract"
            )

        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()

    def test_document_deja_extrait_returns_409(self):
        """Document déjà extrait → 409 Conflict."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_DONE,
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-done-001/extract"
            )

        assert response.status_code == 409
        assert "déjà extrait" in response.json()["detail"]

    def test_exception_interne_returns_500(self):
        """Exception interne → 500 avec message."""
        with patch(
            "src.api.routes.extractions._get_document",
            return_value=FAKE_DOC_PDF,
        ), patch(
            "src.api.routes.extractions.extract_sync",
            side_effect=RuntimeError("Parseur planté"),
        ):
            response = client.post(
                "/api/extractions/documents/doc-test-pdf-001/extract"
            )

        assert response.status_code == 500
        assert "Extraction échouée" in response.json()["detail"]


# ── Classe 4 — GET /jobs/{id}/status ────────────────────────────

class TestJobStatus:
    """Statut des jobs SLA-B."""

    def test_job_status_valid_returns_200(self):
        """Job existant → 200 + champs requis."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = FAKE_JOB

        with patch(
            "src.api.routes.extractions.get_db_cursor"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: mock_cursor
            mock_ctx.return_value.__exit__ = MagicMock(
                return_value=False
            )
            response = client.get(
                "/api/extractions/jobs/job-test-001/status"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in (
            "pending", "processing", "done", "failed"
        )
        assert "sla_class" in data
        assert "queued_at" in data

    def test_job_inconnu_returns_404(self):
        """Job inexistant → 404."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        with patch(
            "src.api.routes.extractions.get_db_cursor"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: mock_cursor
            mock_ctx.return_value.__exit__ = MagicMock(
                return_value=False
            )
            response = client.get(
                "/api/extractions/jobs/job-inexistant/status"
            )

        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()


# ── Classe 5 — GET /documents/{id} ──────────────────────────────

class TestGetExtractionResult:
    """Résultats d'extraction."""

    def test_extraction_existante_returns_200(self):
        """Extraction existante → 200 + champs."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = FAKE_EXTRACTION_ROW

        with patch(
            "src.api.routes.extractions.get_db_cursor"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: mock_cursor
            mock_ctx.return_value.__exit__ = MagicMock(
                return_value=False
            )
            response = client.get(
                "/api/extractions/documents/doc-test-pdf-001"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc-test-pdf-001"
        assert data["confidence_score"] == 0.85
        assert data["warning"] is None

    def test_extraction_absente_returns_404(self):
        """Aucune extraction → 404 explicite."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        with patch(
            "src.api.routes.extractions.get_db_cursor"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: mock_cursor
            mock_ctx.return_value.__exit__ = MagicMock(
                return_value=False
            )
            response = client.get(
                "/api/extractions/documents/doc-inexistant"
            )

        assert response.status_code == 404

    def test_confidence_faible_warning_present(self):
        """§9 : confidence < 0.6 → warning dans réponse."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = FAKE_EXTRACTION_LOW_CONF

        with patch(
            "src.api.routes.extractions.get_db_cursor"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: mock_cursor
            mock_ctx.return_value.__exit__ = MagicMock(
                return_value=False
            )
            response = client.get(
                "/api/extractions/documents/doc-test-pdf-001"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["warning"] is not None
        assert "revue humaine" in data["warning"].lower()
        assert data["confidence_score"] < 0.6
