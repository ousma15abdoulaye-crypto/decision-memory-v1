"""Fixtures pour tests dict M7.3b · isolation transaction rollback."""

from __future__ import annotations

import os

import psycopg
import psycopg.rows
import pytest


def _normalize_db_url(url: str) -> str:
    """RÈGLE-39 · postgresql:// · jamais postgresql+psycopg://."""
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


@pytest.fixture(scope="session")
def db_url() -> str:
    """DATABASE_URL normalisé · session scope."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL non défini")
    return _normalize_db_url(url)


@pytest.fixture
def tx(db_url: str):
    """
    Connexion avec transaction rollback automatique.
    Zéro pollution inter-runs · RÈGLE-17.
    """
    conn = psycopg.connect(db_url, row_factory=psycopg.rows.dict_row)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
