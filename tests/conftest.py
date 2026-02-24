"""
Root pytest config. Set DATABASE_URL before any test imports src.db.

src.db creates the engine at import time (Constitution V2.1). Without DATABASE_URL,
any module that imports src.db (e.g. scoring engine) raises at collection time.
This conftest runs first so collection succeeds; same URL as CI for local runs.
"""

import os

# Doit être posé AVANT tout import src.* (ratelimit.py lu à l'import)
os.environ.setdefault("TESTING", "true")

import uuid
from datetime import UTC, datetime

import pytest

# Load .env and .env.local (local overrides) if present
try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

# Try psycopg (v3) first, fallback to psycopg2 (v2)
try:
    import psycopg
    from psycopg.rows import dict_row

    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2
        import psycopg2.extras

        PSYCOPG_VERSION = 2
    except ImportError:
        raise ImportError("Neither psycopg nor psycopg2 is installed")

# DATABASE_URL doit être défini dans .env ou environnement
if "DATABASE_URL" not in os.environ:
    raise RuntimeError("DATABASE_URL must be set in .env or environment")


def _get_db_conn():
    """Connexion DB autocommit — UN SEUL endroit (racine)."""
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(conninfo=url, row_factory=dict_row)
    conn.autocommit = True
    return conn


@pytest.fixture
def db_conn():
    """Connexion DB autocommit — partagée par db_integrity, integration, invariants."""
    conn = _get_db_conn()
    yield conn
    conn.close()


@pytest.fixture
def db_transaction():
    """Fixture pour tests DB-level avec rollback automatique.

    Connexion psycopg/psycopg2 à la DB de test avec RealDictCursor.
    Rollback automatique après chaque test (isolation).
    Retourne un cursor actif utilisable dans les tests.
    """
    if PSYCOPG_VERSION == 3:
        # psycopg v3 - remove +psycopg from URL
        db_url = os.environ["DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        )
        conn = psycopg.connect(
            conninfo=db_url,
            row_factory=dict_row,
        )
        conn.autocommit = False
        cur = conn.cursor()
        yield cur
        conn.rollback()
        cur.close()
        conn.close()
    else:
        # psycopg2 v2
        conn = psycopg2.connect(
            dsn=os.environ["DATABASE_URL"],
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        conn.autocommit = False
        cur = conn.cursor()
        yield cur
        conn.rollback()
        cur.close()
        conn.close()


@pytest.fixture
def case_factory(db_conn):
    """
    DB factory: crée un Case minimal dans public.cases et retourne case_id.
    Unblocks #8 (tests DB-level scoring).
    Scope: function (isolation maximale).

    Contrat sonde (NOT NULL sans default) :
      id (text), case_type (text), title (text), created_at (text), currency (text)
    db_conn est autocommit=True — pas de commit/rollback explicite.
    """
    created_ids: list[str] = []

    def _factory(currency: str = "XOF", status: str = "draft") -> str:
        case_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.cases
                    (id, case_type, title, created_at, currency, status)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    "test",
                    f"test-factory-{case_id[:8]}",
                    datetime.now(UTC).isoformat(),
                    currency,
                    status,
                ),
            )
        created_ids.append(case_id)
        return case_id

    yield _factory

    if created_ids:
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.cases WHERE id = ANY(%s)",
                    (created_ids,),
                )
        except Exception:
            pass


@pytest.fixture
def _tx(db_conn):
    """Transaction rollback-only — zéro DELETE teardown.

    Sauvegarde et restaure autocommit pour ne pas contaminer
    les fixtures suivantes si la valeur originale n'était pas True.
    """
    original_autocommit = db_conn.autocommit
    db_conn.autocommit = False
    try:
        yield
    finally:
        db_conn.rollback()
        db_conn.autocommit = original_autocommit


@pytest.fixture
def committee_factory(db_conn):
    """Factory comité draft — rollback-only, zéro DELETE teardown.

    Usage : committee_id = committee_factory(case_id=..., status='open')
    """

    def _factory(
        case_id: str,
        org_id: str = "org-test",
        committee_type: str = "achat",
        created_by: str = "test-user",
        status: str = "draft",
    ) -> str:
        committee_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.committees "
                "(committee_id, case_id, org_id, committee_type, created_by, status) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (committee_id, case_id, org_id, committee_type, created_by, status),
            )
            cur.execute(
                "INSERT INTO public.committee_events "
                "(committee_id, event_type, payload, created_by) "
                "VALUES (%s, 'committee_created', '{}', %s)",
                (committee_id, created_by),
            )
        return committee_id

    yield _factory
