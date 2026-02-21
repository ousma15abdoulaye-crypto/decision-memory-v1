# src/couche_a/models.py
"""
Couche A — Couche d'accès aux données (DAL).
Source de vérité unique pour les tables et utilitaires Couche A.
Constitution V3.3.2 §1 — ADR-0003 : psycopg uniquement, zéro ORM.

Ce module expose les symboles attendus par les services Couche A :
  - *_table  : références aux noms de tables (str) — pas de SQLAlchemy
  - get_engine     : pont vers get_connection() psycopg
  - ensure_schema  : pont vers init_db_schema()
  - generate_id    : générateur d'identifiants UUID4
  - serialize_json / deserialize_json : utilitaires JSON
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from src.db.core import get_connection, init_db_schema

# ---------------------------------------------------------------------------
# Références de tables — noms canoniques (psycopg, pas SQLAlchemy)
# ---------------------------------------------------------------------------
analyses_table: str = "analyses"
audits_table: str = "audits"
documents_table: str = "documents"
extractions_table: str = "offer_extractions"
lots_table: str = "lots"
offers_table: str = "offers"

# ---------------------------------------------------------------------------
# Ponts DB — conformes ADR-0003
# ---------------------------------------------------------------------------

def get_engine():
    """
    Retourne le context manager de connexion psycopg.
    Pont de compatibilité : les services appellent get_engine()
    comme ils appelaient SQLAlchemy create_engine().

    Usage dans les services :
        with get_engine() as conn:
            conn.execute("SELECT ...", params)
    """
    return get_connection()


def ensure_schema() -> None:
    """
    Crée les tables Core si elles n'existent pas.
    Pont vers init_db_schema() — ADR-0003.
    """
    init_db_schema()


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def generate_id() -> str:
    """Génère un identifiant UUID4 unique."""
    return str(uuid.uuid4())


def serialize_json(data: Any) -> str:
    """Sérialise un objet Python en JSON string."""
    return json.dumps(data, ensure_ascii=False, default=str)


def deserialize_json(data: str | None) -> Any:
    """Désérialise un JSON string en objet Python. Retourne None si vide."""
    if data is None:
        return None
    return json.loads(data)
