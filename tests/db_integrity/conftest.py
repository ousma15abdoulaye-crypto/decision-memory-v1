"""
Fixtures pour tests db_integrity — migrations appliquées avant exécution.
"""

import importlib.util
import os
import subprocess
import uuid

import psycopg
import psycopg.rows
import pytest
from sqlalchemy import create_engine, text


def _get_conn():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)


def _ensure_base_schema():
    """Exécute migration 002 si documents n'existe pas (DB partielle)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='documents'"
            )
            if cur.fetchone() is not None:
                return
    finally:
        conn.close()
    # 002 pas appliquée — exécuter manuellement puis colonnes 013
    url = os.environ["DATABASE_URL"]
    if not url.startswith("postgresql+psycopg"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "alembic", "versions", "002_add_couche_a.py")
    spec = importlib.util.spec_from_file_location("migration_002", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.upgrade(engine=engine)
    # Colonnes M-EXTRACTION-ENGINE (013) sur documents/extractions
    with engine.connect() as cx:
        cx.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT")
        )
        cx.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_uri TEXT")
        )
        cx.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending'"
            )
        )
        cx.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method TEXT"
            )
        )
        # extractions (pour tests intégration)
        cx.execute(
            text("ALTER TABLE extractions ALTER COLUMN artifact_id DROP NOT NULL")
        )
        cx.execute(
            text("ALTER TABLE extractions ALTER COLUMN extraction_type DROP NOT NULL")
        )
        cx.execute(
            text("ALTER TABLE extractions ADD COLUMN IF NOT EXISTS document_id TEXT")
        )
        cx.execute(
            text("ALTER TABLE extractions ADD COLUMN IF NOT EXISTS raw_text TEXT")
        )
        cx.execute(
            text(
                "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS structured_data JSONB"
            )
        )
        cx.execute(
            text(
                "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extraction_method TEXT"
            )
        )
        cx.execute(
            text(
                "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS confidence_score REAL"
            )
        )
        cx.execute(
            text(
                "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ DEFAULT NOW()"
            )
        )
        cx.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id)"
            )
        )
        cx.commit()


@pytest.fixture(scope="session", autouse=True)
def run_migrations_before_db_integrity_tests():
    """
    Garantit que toutes les migrations sont appliquées avant les tests db_integrity.
    Documents, extraction_jobs, extraction_errors requis.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "Migrations Alembic échouées — tests db_integrity impossibles.\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )
    _ensure_base_schema()
    # Insérer un document minimal si documents est vide (requis pour FSM/§9 tests)
    conn = _get_conn()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM documents LIMIT 1")
            if cur.fetchone() is None:
                case_id = f"dbintegrity-{uuid.uuid4().hex[:8]}"
                cur.execute(
                    """
                    INSERT INTO cases (id, case_type, title, created_at, status)
                    VALUES (%s, 'DB_INTEGRITY', 'Fixtures FSM', NOW()::TEXT, 'draft')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (case_id,),
                )
                cur.execute(
                    """
                    INSERT INTO offers (id, case_id, supplier_name, offer_type, submitted_at, created_at)
                    VALUES (%s, %s, 'Test', 'technical', NOW()::TEXT, NOW()::TEXT)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (f"offer-{case_id}", case_id),
                )
                doc_id = f"doc-{uuid.uuid4().hex[:8]}"
                cur.execute(
                    """
                    INSERT INTO documents (id, case_id, offer_id, filename, path, uploaded_at)
                    VALUES (%s, %s, %s, 'fsm-test.pdf', '/tmp/fsm.pdf', NOW()::TEXT)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (doc_id, case_id, f"offer-{case_id}"),
                )
    finally:
        conn.close()
    yield


# db_conn fourni par tests/conftest.py (racine)


@pytest.fixture
def extraction_correction_fixture(db_conn):
    """Document + extraction + correction pour M-EXTRACTION-CORRECTIONS."""
    doc_id = f"corr-fixture-{uuid.uuid4().hex[:8]}"
    case_id = f"corr-case-{uuid.uuid4().hex[:8]}"
    offer_id = f"corr-offer-{uuid.uuid4().hex[:8]}"
    extraction_id = f"ext-{uuid.uuid4().hex[:12]}"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cases (id, case_type, title, created_at, status)
            VALUES (%s, 'CORR_TEST', 'Fixture corrections', NOW()::TEXT, 'draft')
            ON CONFLICT (id) DO NOTHING
            """,
            (case_id,),
        )
        cur.execute(
            """
            INSERT INTO offers (id, case_id, supplier_name, offer_type, submitted_at, created_at)
            VALUES (%s, %s, 'Fixture', 'technical', NOW()::TEXT, NOW()::TEXT)
            ON CONFLICT (id) DO NOTHING
            """,
            (offer_id, case_id),
        )
        cur.execute(
            """
            INSERT INTO documents (id, case_id, offer_id, filename, path, uploaded_at)
            VALUES (%s, %s, %s, 'fixture.pdf', '/tmp/fixture.pdf', NOW()::TEXT)
            ON CONFLICT (id) DO NOTHING
            """,
            (doc_id, case_id, offer_id),
        )
        cur.execute(
            """
            INSERT INTO extractions
                (id, case_id, document_id, raw_text, structured_data,
                 extraction_method, confidence_score, extracted_at,
                 data_json, extraction_type, created_at)
            VALUES (%s, %s, %s, '', '{}'::jsonb, 'native_pdf', 0.9, NOW(),
                    '{}', 'native_pdf', NOW()::TEXT)
            ON CONFLICT (id) DO NOTHING
            """,
            (extraction_id, case_id, doc_id),
        )
        cur.execute(
            """
            INSERT INTO extraction_corrections
                (extraction_id, document_id, structured_data,
                 confidence_override, correction_reason, corrected_by)
            VALUES (%s, %s, '{"corrected": true}'::jsonb, 0.95, 'test', 'fixture-user')
            RETURNING id
            """,
            (extraction_id, doc_id),
        )
        row = cur.fetchone()
        correction_id = str(row["id"]) if row else None
    yield (doc_id, extraction_id, correction_id)
