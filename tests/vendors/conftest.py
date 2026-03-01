"""
Fixtures pour tests vendors — M4 Vendor Importer Mali.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from psycopg.rows import dict_row


@pytest.fixture(scope="module")
def db_conn_vendors():
    """
    Connexion DB module-scoped pour vendors — autocommit=True, dict_row.
    Nécessaire pour les fixtures de seed de test (scope=module).
    """
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(conninfo=url, row_factory=dict_row)
    conn.autocommit = True
    yield conn
    conn.close()
