# -*- coding: utf-8 -*-
"""Migration stub 018 — vide (remplacee par 019_consolidate_ec).

Revision ID: 018_fix_alembic_heads
Revises    : 016_fix_015_views_triggers
Create Date: 2026-02-21

Cette migration etait vide. Elle est conservee uniquement pour permettre
a alembic de localiser la revision presente en DB (018_fix_alembic_heads)
et d'executer la migration suivante 019_consolidate_ec.
La 019 est idempotente et applique tous les artefacts necessaires.
"""
from __future__ import annotations

from alembic import op

revision      = "018_fix_alembic_heads"
down_revision = "016_fix_015_views_triggers"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
