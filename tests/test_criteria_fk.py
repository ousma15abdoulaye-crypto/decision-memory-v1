"""
Test structurel -- M-CRITERIA-FK
Verifie existence FK et index uniquement.
Pas de test metier. Pas d'insert. Pas de mock.
psycopg v3 -- row_factory=dict_row.
"""

import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("DM_DATABASE_URL", ""))
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="module")
def db():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        conn.autocommit = True
        yield conn


def test_fk_fk_criteria_canonical_item_exists(db):
    """FK fk_criteria_canonical_item presente dans pg_constraint."""
    with db.cursor() as cur:
        cur.execute("""
            SELECT conname
            FROM pg_constraint
            WHERE conname = 'fk_criteria_canonical_item'
              AND contype = 'f';
        """)
        row = cur.fetchone()
    assert (
        row is not None
    ), "FK fk_criteria_canonical_item ABSENTE -- migration 023 non appliquee ou rollbackee"


def test_fk_index_criteria_canonical_item_id_exists(db):
    """Index idx_criteria_canonical_item_id present dans pg_indexes."""
    with db.cursor() as cur:
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename  = 'criteria'
              AND indexname  = 'idx_criteria_canonical_item_id';
        """)
        row = cur.fetchone()
    assert (
        row is not None
    ), "Index idx_criteria_canonical_item_id ABSENT -- migration 023 incomplete"
