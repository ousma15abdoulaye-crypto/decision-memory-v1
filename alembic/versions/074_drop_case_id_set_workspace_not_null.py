"""074 - DROP case_id columns, SET workspace_id NOT NULL (V4.2.0)

Revision ID: 074_drop_case_id_set_workspace_not_null
Revises: 073_add_workspace_id_to_canon_tables
Create Date: 2026-04-04

Phase 3 — Big Bang partiel (schema aligné code existant) :

  - SET NOT NULL workspace_id sur les tables listées (market_surveys reste NULLABLE)
  - DROP COLUMN case_id sur les tables listées

Les RENAME cases/committees/committee_events vers _deprecated_* et le DROP de
committee_members sont **reportés** : le code applicatif (SQL brut + services)
référence encore les noms canon V4.1 (cases, committee_events, committee_members).
Les renommages documentés dans DMS_V4.2.0_SCHEMA.sql suivront un chantier dédié
(code + vues de compatibilité) avec GO CTO.

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "074_drop_case_id_set_workspace_not_null"
down_revision = "073_add_workspace_id_to_canon_tables"
branch_labels = None
depends_on = None

_TABLES_SET_NOT_NULL = [
    "documents",
    "dao_criteria",
    "offer_extractions",
    "score_history",
    "elimination_log",
    "evaluation_documents",
]

_TABLES_DROP_CASE_ID = [
    "documents",
    "dao_criteria",
    "offer_extractions",
    "score_history",
    "elimination_log",
    "evaluation_documents",
    "market_surveys",
]


def upgrade() -> None:
    for table in _TABLES_SET_NOT_NULL:
        op.execute(f"""
            ALTER TABLE {table}
            ALTER COLUMN workspace_id SET NOT NULL
            """)

    for table in _TABLES_DROP_CASE_ID:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS case_id CASCADE")


def downgrade() -> None:
    for table in _TABLES_DROP_CASE_ID:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS case_id TEXT")

    for table in reversed(_TABLES_SET_NOT_NULL):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN workspace_id DROP NOT NULL")
