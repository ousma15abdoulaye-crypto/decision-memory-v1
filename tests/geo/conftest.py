"""
Fixtures pour tests geo — M3 GEO MASTER MALI.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from src.api.main import app
from src.geo.seed_mali import run_seed


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """TestClient FastAPI partagé pour tous les tests geo."""
    return TestClient(app)


@pytest.fixture(scope="session")
def db_conn_geo():
    """
    Connexion DB session-scoped pour geo — autocommit=True, dict_row.
    Nécessaire car geo_seed est session-scoped et db_conn (root) est function-scoped.
    """
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(conninfo=url, row_factory=dict_row)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def geo_seed(db_conn_geo):
    """
    Seed Mali inséré une seule fois par session.
    Idempotent (ON CONFLICT DO NOTHING).
    """
    counts = run_seed(db_conn_geo)
    return counts
