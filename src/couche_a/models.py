"""Database models and helpers for Couche A using SQLAlchemy Core.

PostgreSQL ONLY (Constitution V2.1 ONLINE-ONLY).
Uses DATABASE_URL via the global engine from src.db.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.engine import Engine

from src.db import engine

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BASE_DIR / "data" / "couche_a"
DATA_DIR = Path(os.getenv("COUCHE_A_DATA_DIR", DEFAULT_DATA_DIR))

metadata = MetaData()

cases_table = Table(
    "cases",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("title", String(255), nullable=False),
    Column("buyer_name", String(255), nullable=False, default="Acheteur"),
    Column("status", String(40), nullable=False, default="OUVERT"),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

lots_table = Table(
    "lots",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("case_id", String(20), ForeignKey("cases.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

offers_table = Table(
    "offers",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("case_id", String(20), ForeignKey("cases.id"), nullable=False),
    Column("lot_id", String(20), ForeignKey("lots.id"), nullable=False),
    Column("supplier_name", String(255), nullable=False),
    Column("offer_type", String(40), nullable=False, default="AUTRE"),
    Column("submitted_at", DateTime(timezone=True), nullable=True),
    Column("amount", Float, nullable=True),
    Column("status", String(40), nullable=False, default="EN_ATTENTE"),
    Column("score", Float, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

documents_table = Table(
    "documents",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("case_id", String(20), ForeignKey("cases.id"), nullable=False),
    Column("lot_id", String(20), ForeignKey("lots.id"), nullable=False),
    Column("offer_id", String(20), ForeignKey("offers.id"), nullable=False),
    Column("document_type", String(40), nullable=False),
    Column("filename", String(255), nullable=False),
    Column("storage_path", Text, nullable=False),
    Column("mime_type", String(120), nullable=False),
    Column("metadata_json", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

extractions_table = Table(
    "extractions",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("document_id", String(20), ForeignKey("documents.id"), nullable=False),
    Column("offer_id", String(20), ForeignKey("offers.id"), nullable=False),
    Column("extracted_json", Text, nullable=False),
    Column("missing_json", Text, nullable=False),
    Column("used_llm", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

analyses_table = Table(
    "analyses",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("offer_id", String(20), ForeignKey("offers.id"), nullable=False),
    Column("essentials_score", Float, nullable=True),
    Column("capacity_score", Float, nullable=True),
    Column("sustainability_score", Float, nullable=True),
    Column("commercial_score", Float, nullable=True),
    Column("total_score", Float, nullable=True),
    Column("status", String(40), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

audits_table = Table(
    "audits",
    metadata,
    Column("id", String(20), primary_key=True),
    Column("entity_type", String(40), nullable=False),
    Column("entity_id", String(20), nullable=False),
    Column("action", String(80), nullable=False),
    Column("actor", String(120), nullable=True),
    Column("details_json", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def generate_id() -> str:
    """Generate a 20-character identifier."""
    return secrets.token_hex(10)


def serialize_json(payload: Any) -> str:
    """Serialize a payload into JSON for storage."""
    return json.dumps(payload, ensure_ascii=False, default=str)


def deserialize_json(payload: Optional[str]) -> Any:
    """Deserialize JSON payloads safely."""
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload detected.")
        return {}


def get_engine() -> Engine:
    """Return the configured PostgreSQL engine for Couche A (from DATABASE_URL)."""
    return engine


def reset_engine() -> None:
    """No-op: engine is global (kept for backward compatibility in tests)."""
    pass


def ensure_schema(engine: Optional[Engine] = None) -> None:
    """Create all Couche A tables if they do not exist."""
    active_engine = engine or get_engine()
    metadata.create_all(active_engine)
