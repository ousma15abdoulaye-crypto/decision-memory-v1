# tests/integration/conftest.py
"""
Fixtures d'intégration — M-EXTRACTION-ENGINE.
Données réelles en DB de test.
Nettoyage automatique après chaque test.
"""

import os
import uuid

import psycopg
import psycopg.rows
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from src.api.main import app

load_dotenv()


def _get_conn():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(
        url,
        row_factory=psycopg.rows.dict_row,
    )


@pytest.fixture
def integration_client():
    """TestClient FastAPI pour tests d'intégration."""
    return TestClient(app)


@pytest.fixture
def db_conn():
    """
    Connexion DB avec autocommit pour setup/teardown.
    Utilisé uniquement pour insérer/lire des fixtures.
    """
    conn = _get_conn()
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def test_case_id(db_conn):
    """
    Crée un case de test et le supprime après le test.
    """
    case_id = f"integ-case-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cases
                (id, case_type, title, status, created_at)
            VALUES (%s, %s, %s, 'DRAFT', NOW()::TEXT)
            ON CONFLICT (id) DO NOTHING
        """,
            (
                case_id,
                "INTEGRATION_TEST",
                f"Case intégration {case_id}",
            ),
        )
    yield case_id
    # Nettoyage
    with db_conn.cursor() as cur:
        try:
            cur.execute(
                "DELETE FROM extraction_errors "
                "WHERE document_id IN ("
                "  SELECT id FROM documents WHERE case_id = %s"
                ")",
                (case_id,),
            )
        except Exception:
            pass  # Ignore permission errors
        try:
            cur.execute(
                "DELETE FROM extraction_jobs "
                "WHERE document_id IN ("
                "  SELECT id FROM documents WHERE case_id = %s"
                ")",
                (case_id,),
            )
        except Exception:
            pass
        try:
            cur.execute(
                "DELETE FROM extractions "
                "WHERE document_id IN ("
                "  SELECT id FROM documents WHERE case_id = %s"
                ")",
                (case_id,),
            )
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM documents WHERE case_id = %s", (case_id,))
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
        except Exception:
            pass


@pytest.fixture
def test_doc_pdf(db_conn, test_case_id):
    """
    Crée un document PDF natif en DB pour les tests.
    extraction_method = native_pdf (SLA-A).
    """
    doc_id = f"integ-doc-pdf-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents
                (id, case_id, filename, path, uploaded_at,
                 mime_type, storage_uri, extraction_status,
                 extraction_method)
            VALUES (%s, %s, %s, %s, NOW()::TEXT,
                    %s, %s, 'pending', 'native_pdf')
        """,
            (
                doc_id,
                test_case_id,
                "test_native.pdf",
                "/tmp/test_native.pdf",
                "application/pdf",
                "/tmp/test_native.pdf",
            ),
        )
    yield doc_id


@pytest.fixture
def test_doc_scan(db_conn, test_case_id):
    """
    Crée un document scan en DB pour les tests.
    extraction_method = tesseract (SLA-B).
    """
    doc_id = f"integ-doc-scan-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents
                (id, case_id, filename, path, uploaded_at,
                 mime_type, storage_uri, extraction_status,
                 extraction_method)
            VALUES (%s, %s, %s, %s, NOW()::TEXT,
                    %s, %s, 'pending', 'tesseract')
        """,
            (
                doc_id,
                test_case_id,
                "test_scan.tif",
                "/tmp/test_scan.tif",
                "image/tiff",
                "/tmp/test_scan.tif",
            ),
        )
    yield doc_id


@pytest.fixture
def test_doc_already_extracted(db_conn, test_case_id):
    """
    Document déjà extrait (extraction_status = done).
    """
    doc_id = f"integ-doc-done-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents
                (id, case_id, filename, path, uploaded_at,
                 mime_type, storage_uri, extraction_status,
                 extraction_method)
            VALUES (%s, %s, %s, %s, NOW()::TEXT,
                    %s, %s, 'done', 'native_pdf')
        """,
            (
                doc_id,
                test_case_id,
                "already_done.pdf",
                "/tmp/already_done.pdf",
                "application/pdf",
                "/tmp/already_done.pdf",
            ),
        )
        # Insérer aussi une extraction existante
        extraction_id = f"ext-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """
            INSERT INTO extractions
                (id, case_id, document_id, raw_text, structured_data,
                 extraction_method, confidence_score, extracted_at,
                 data_json, extraction_type, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, NOW(),
                    %s, %s, NOW()::TEXT)
        """,
            (
                extraction_id,
                test_case_id,
                doc_id,
                "Texte déjà extrait.",
                '{"doc_kind": null}',
                "native_pdf",
                0.85,
                '{"doc_kind": null}',  # data_json
                "native_pdf",  # extraction_type
            ),
        )
    yield doc_id
