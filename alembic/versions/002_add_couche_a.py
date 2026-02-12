"""Add Couche A procurement pipeline tables."""
from __future__ import annotations

from typing import Optional

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

from src.couche_a.models import get_engine, metadata

revision = "002_add_couche_a"
down_revision = "001_add_couche_b"
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Connection | Engine:
    if op is not None:
        return op.get_bind()
    return engine or get_engine()


def upgrade(engine: Optional[Engine] = None) -> None:
    """Create Couche A tables."""
    bind = _get_bind(engine)
    metadata.create_all(bind)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Drop Couche A tables created in this migration (preserve 'cases')."""
    bind = _get_bind(engine)
    tables_to_drop = ["analyses", "extractions", "documents", "offers", "lots", "audits"]

    if op is not None:
        # Contexte Alembic (migration CLI)
        for table in tables_to_drop:
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    else:
        # Contexte de test (Engine direct)
        with bind.connect() as conn:
            for table in tables_to_drop:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            conn.commit()