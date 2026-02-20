"""
Root pytest config. Set DATABASE_URL before any test imports src.db.

src.db creates the engine at import time (Constitution V2.1). Without DATABASE_URL,
any module that imports src.db (e.g. scoring engine) raises at collection time.
This conftest runs first so collection succeeds; same URL as CI for local runs.
"""

import os

import pytest

# Load .env file if present
try:
    from dotenv import load_dotenv

    load_dotenv()
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

# db_conn : UN SEUL endroit — tests/db_integrity/conftest.py
# (integration/invariants utilisent pytest_plugins pour le charger)


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
