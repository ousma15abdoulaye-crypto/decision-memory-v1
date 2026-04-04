"""074 - DROP case_id columns, SET workspace_id NOT NULL, rename deprecated tables (V4.2.0)

Revision ID: 074_drop_case_id_set_workspace_not_null
Revises: 073_add_workspace_id_to_canon_tables
Create Date: 2026-04-04

Migration Big Bang Phase 3 — A executer UNIQUEMENT apres :
  1. scripts/migrate_cases_to_workspaces.py --verify-only retourne 0 orphelins
  2. Tous les artefacts dans les 10 tables ont workspace_id NON NULL
  3. CI verte sur feat/v420-phase2-dual-write
  4. GO CTO explicite

Cette migration :
  - SET NOT NULL workspace_id sur 9 tables (market_surveys reste NULLABLE = W2)
  - DROP COLUMN case_id sur 10 tables canon
  - RENAME cases -> _deprecated_cases (conservation, pas DROP)
  - RENAME committees -> _deprecated_committees
  - RENAME committee_events -> _deprecated_committee_events
  - RENAME submission_registries -> _deprecated_submission_registries
  - RENAME criteria_weighting_validation -> _deprecated_criteria_weighting_validation
  - DROP TABLE committees_members (integre dans committee_session_members)

STOP SIGNALS avant execution :
  S1 : verify_migration() retourne > 0 -> STOP TOTAL
  S2 : alembic heads > 1 -> STOP TOTAL
  S7 : workspace_id NULL dans une table NOT NULL -> STOP

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 499-533
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "074_drop_case_id_set_workspace_not_null"
down_revision = "073_add_workspace_id_to_canon_tables"
branch_labels = None
depends_on = None

# Tables qui passent workspace_id en NOT NULL (market_surveys reste NULLABLE)
_TABLES_SET_NOT_NULL = [
    "documents",
    "dao_criteria",
    "offer_extractions",
    "score_history",
    "elimination_log",
    "evaluation_documents",
]

# Tables qui perdent case_id (inclut market_surveys)
_TABLES_DROP_CASE_ID = [
    "documents",
    "dao_criteria",
    "offer_extractions",
    "score_history",
    "elimination_log",
    "evaluation_documents",
    "market_surveys",
]

# Tables depot : RENAME (conservation données, pas DROP)
_RENAMED_TABLES = [
    ("cases", "_deprecated_cases"),
    ("committees", "_deprecated_committees"),
    ("committee_events", "_deprecated_committee_events"),
    ("submission_registries", "_deprecated_submission_registries"),
]


def upgrade() -> None:
    for table in _TABLES_SET_NOT_NULL:
        op.execute(f"""
            ALTER TABLE {table}
            ALTER COLUMN workspace_id SET NOT NULL
            """)

    for table in _TABLES_DROP_CASE_ID:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS case_id")

    for old_name, new_name in _RENAMED_TABLES:
        op.execute(f"ALTER TABLE IF EXISTS {old_name} RENAME TO {new_name}")

    op.execute("DROP TABLE IF EXISTS committee_members CASCADE")


def downgrade() -> None:
    for old_name, new_name in reversed(_RENAMED_TABLES):
        op.execute(f"ALTER TABLE IF EXISTS {new_name} RENAME TO {old_name}")

    for table in _TABLES_DROP_CASE_ID:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS case_id TEXT")

    for table in reversed(_TABLES_SET_NOT_NULL):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN workspace_id DROP NOT NULL")
