# tests/integration/test_extraction_e2e.py
"""
Tests d'intégration e2e — M-EXTRACTION-ENGINE.
🔴 BLOQUANTS CI.
Scénarios complets avec DB réelle.
Constitution V3.3.2 §9 (doctrine échec).
ADR-0002 §2.5 (SLA deux classes).
"""
import pytest
from unittest.mock import patch


# ── Classe 1 — SLA-A PDF natif ───────────────────────────────────

class TestExtractionSLAAe2e:
    """
    Scénario SLA-A complet :
    document en DB → POST /extract → vérifier résultat en DB.
    """

    def test_extraction_sla_a_complete(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        SLA-A : POST /extract → status done → résultat en DB.
        Mock du parseur pdfplumber pour éviter un vrai fichier.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            return_value=(
                "Texte extrait du PDF natif. " * 30,
                {"doc_kind": None, "_low_confidence": False,
                 "_requires_human_review": False,
                 "_extraction_duration_ms": None,
                 "_sla_class": None,
                 "detected_tables": [],
                 "detected_sections": [],
                 "candidate_criteria": [],
                 "candidate_line_items": [],
                 "currency_detected": None,
                 "dates_detected": [],
                 "supplier_candidates": [],
                 "language_detected": None},
            ),
        ):
            response = integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "done"
        assert data["sla_class"] == "A"
        assert data["method"] == "native_pdf"
        assert data["duration_ms"] is not None
        assert data["duration_ms"] < 60_000

        # Vérifier que l'extraction est bien persistée en DB
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT confidence_score, extraction_method
                FROM extractions
                WHERE document_id = %s
            """, (test_doc_pdf,))
            row = cur.fetchone()

        assert row is not None, \
            "L'extraction doit être persistée en DB"
        assert row["extraction_method"] == "native_pdf"
        assert row["confidence_score"] > 0

    def test_extraction_sla_a_document_status_updated(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        SLA-A : après extraction réussie →
        documents.extraction_status = 'done'.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            return_value=(
                "x" * 600,
                {"doc_kind": None, "_low_confidence": False,
                 "_requires_human_review": False,
                 "_extraction_duration_ms": None,
                 "_sla_class": None,
                 "detected_tables": [], "detected_sections": [],
                 "candidate_criteria": [],
                 "candidate_line_items": [],
                 "currency_detected": None,
                 "dates_detected": [],
                 "supplier_candidates": [],
                 "language_detected": None},
            ),
        ):
            integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT extraction_status
                FROM documents
                WHERE id = %s
            """, (test_doc_pdf,))
            row = cur.fetchone()

        assert row["extraction_status"] == "done"

    def test_get_extraction_result_apres_extraction(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        GET /documents/{id} retourne le résultat
        après une extraction réussie.
        """
        # 1. Lancer l'extraction
        with patch(
            "src.extraction.engine._extract_native_pdf",
            return_value=(
                "Contenu riche du document. " * 40,
                {"doc_kind": None, "_low_confidence": False,
                 "_requires_human_review": False,
                 "_extraction_duration_ms": None,
                 "_sla_class": None,
                 "detected_tables": [], "detected_sections": [],
                 "candidate_criteria": [],
                 "candidate_line_items": [],
                 "currency_detected": None,
                 "dates_detected": [],
                 "supplier_candidates": [],
                 "language_detected": None},
            ),
        ):
            integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        # 2. Récupérer le résultat
        response = integration_client.get(
            f"/api/extractions/documents/{test_doc_pdf}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_doc_pdf
        assert data["confidence_score"] is not None
        assert data["confidence_score"] > 0
        assert data["extraction_method"] == "native_pdf"
        assert data["raw_text"] is not None
        assert len(data["raw_text"]) > 0


# ── Classe 2 — SLA-B OCR asynchrone ─────────────────────────────

class TestExtractionSLABe2e:
    """
    Scénario SLA-B complet :
    document scan → POST /extract → job en DB → GET status.
    """

    def test_extraction_sla_b_cree_job_en_db(
        self, integration_client, test_doc_scan, db_conn
    ):
        """
        SLA-B : POST /extract → job inséré dans extraction_jobs.
        """
        response = integration_client.post(
            f"/api/extractions/documents/{test_doc_scan}/extract"
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["sla_class"] == "B"
        assert data["job_id"] is not None

        # Vérifier que le job est en DB
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT status, method, sla_class
                FROM extraction_jobs
                WHERE id = %s
            """, (data["job_id"],))
            job = cur.fetchone()

        assert job is not None, "Le job doit être en DB"
        assert job["status"] == "pending"
        assert job["method"] == "tesseract"
        assert job["sla_class"] == "B"

    def test_get_job_status_apres_creation(
        self, integration_client, test_doc_scan
    ):
        """
        SLA-B : GET /jobs/{id}/status retourne pending
        immédiatement après création.
        """
        # 1. Créer le job
        response = integration_client.post(
            f"/api/extractions/documents/{test_doc_scan}/extract"
        )
        job_id = response.json()["job_id"]

        # 2. Consulter le statut
        status_response = integration_client.get(
            f"/api/extractions/jobs/{job_id}/status"
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["sla_class"] == "B"
        assert data["queued_at"] is not None
        assert data["started_at"] is None
        assert data["completed_at"] is None

    def test_extraction_sla_b_retour_immediat(
        self, integration_client, test_doc_scan
    ):
        """
        SLA-B : la réponse est immédiate (pas de blocage).
        Le job_id est retourné sans attendre le traitement.
        """
        import time
        start = time.monotonic()

        integration_client.post(
            f"/api/extractions/documents/{test_doc_scan}/extract"
        )

        elapsed = time.monotonic() - start
        assert elapsed < 2.0, \
            f"SLA-B doit répondre < 2s, obtenu {elapsed:.2f}s"


# ── Classe 3 — Erreurs §9 e2e ────────────────────────────────────

class TestErreurse2e:
    """§9 : erreurs persistées et signalées correctement."""

    def test_document_deja_extrait_409(
        self, integration_client, test_doc_already_extracted
    ):
        """
        Document déjà extrait → 409 (pas de double extraction).
        Vérification contre DB réelle.
        """
        response = integration_client.post(
            f"/api/extractions/documents/"
            f"{test_doc_already_extracted}/extract"
        )

        assert response.status_code == 409
        assert "déjà extrait" in response.json()["detail"]

    def test_document_inexistant_404(self, integration_client):
        """Document inexistant → 404 avec message explicite."""
        response = integration_client.post(
            "/api/extractions/documents/"
            "doc-qui-nexiste-vraiment-pas/extract"
        )

        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()

    def test_echec_extraction_enregistre_erreur(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        §9 : extraction échouée →
        extraction_errors contient une entrée.
        requires_human = True.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            side_effect=RuntimeError("Parseur pdfplumber planté"),
        ):
            response = integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        assert response.status_code == 500

        # Vérifier que l'erreur est enregistrée en DB
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT error_code, error_detail, requires_human
                FROM extraction_errors
                WHERE document_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (test_doc_pdf,))
            error = cur.fetchone()

        assert error is not None, \
            "§9 : l'erreur doit être persistée en DB"
        assert error["error_code"] == "PARSE_ERROR"
        assert "Parseur pdfplumber planté" in error["error_detail"]
        assert error["requires_human"] is True

    def test_echec_extraction_status_failed(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        §9 : extraction échouée →
        documents.extraction_status = 'failed'.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            side_effect=RuntimeError("Erreur critique"),
        ):
            integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT extraction_status
                FROM documents WHERE id = %s
            """, (test_doc_pdf,))
            row = cur.fetchone()

        assert row["extraction_status"] == "failed"

    def test_get_result_avant_extraction_404(
        self, integration_client, test_doc_pdf
    ):
        """
        GET résultat avant extraction →
        404 explicite (pas de données partielles).
        """
        response = integration_client.get(
            f"/api/extractions/documents/{test_doc_pdf}"
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "extract" in detail.lower() or \
               "aucune" in detail.lower()


# ── Classe 4 — Cohérence DB après extraction ────────────────────

class TestCohérenceDBe2e:
    """Vérifications de cohérence en DB après extraction."""

    def test_une_seule_extraction_inseree(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        Une seule extraction insérée par appel.
        Pas de doublon.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            return_value=(
                "x" * 600,
                {"doc_kind": None, "_low_confidence": False,
                 "_requires_human_review": False,
                 "_extraction_duration_ms": None,
                 "_sla_class": None,
                 "detected_tables": [], "detected_sections": [],
                 "candidate_criteria": [],
                 "candidate_line_items": [],
                 "currency_detected": None,
                 "dates_detected": [],
                 "supplier_candidates": [],
                 "language_detected": None},
            ),
        ):
            integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as nb
                FROM extractions
                WHERE document_id = %s
            """, (test_doc_pdf,))
            row = cur.fetchone()

        assert row["nb"] == 1, \
            f"Attendu 1 extraction, obtenu {row['nb']}"

    def test_confidence_score_persiste_correctement(
        self, integration_client, test_doc_pdf, db_conn
    ):
        """
        confidence_score persisté en DB correspond
        au score calculé par _compute_confidence.
        Texte long → 0.85.
        """
        with patch(
            "src.extraction.engine._extract_native_pdf",
            return_value=(
                "Texte très long pour le test. " * 50,
                {"doc_kind": None, "_low_confidence": False,
                 "_requires_human_review": False,
                 "_extraction_duration_ms": None,
                 "_sla_class": None,
                 "detected_tables": [], "detected_sections": [],
                 "candidate_criteria": [],
                 "candidate_line_items": [],
                 "currency_detected": None,
                 "dates_detected": [],
                 "supplier_candidates": [],
                 "language_detected": None},
            ),
        ):
            integration_client.post(
                f"/api/extractions/documents/{test_doc_pdf}/extract"
            )

        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT confidence_score
                FROM extractions
                WHERE document_id = %s
            """, (test_doc_pdf,))
            row = cur.fetchone()

        assert row["confidence_score"] == pytest.approx(0.85)
