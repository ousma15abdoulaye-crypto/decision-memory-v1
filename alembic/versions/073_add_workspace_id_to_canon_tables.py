"""073 - Add workspace_id to 10 canon tables + CHECK no_winner (V4.2.0)

Revision ID: 073_add_workspace_id_to_canon_tables
Revises: 072_vendor_market_signals_watchlist
Create Date: 2026-04-04

Migration additive (workspace_id NULLABLE) sur 10 tables existantes.
Aucune donnee touchee. Code existant continue de fonctionner.
C'est la fenetre de demarrage du dual-write (Phase 2).

Tables modifiees :
  documents, evaluation_criteria, offer_extractions,
  extraction_review_queue, score_history, elimination_log,
  evaluation_documents, decision_history, dict_proposals,
  market_surveys

Contrainte CHECK INV-W06 sur evaluation_documents :
  interdit les champs winner/rank/recommendation/best_offer/selected_vendor
  dans scores_matrix (REGLE-09 canon V4.1.0).

Note : market_surveys.workspace_id reste NULLABLE apres 074 egalement
       (zone W2 — mercuriale interrogeable sans processus ouvert).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 471-491
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "073_add_workspace_id_to_canon_tables"
down_revision = "072_vendor_market_signals_watchlist"
branch_labels = None
depends_on = None

_TABLES = [
    "documents",
    "evaluation_criteria",
    "offer_extractions",
    "extraction_review_queue",
    "score_history",
    "elimination_log",
    "evaluation_documents",
    "decision_history",
    "dict_proposals",
    "market_surveys",
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS workspace_id UUID
            REFERENCES process_workspaces(id)
            """)

    op.execute("""
        ALTER TABLE evaluation_documents
        ADD CONSTRAINT no_winner_field CHECK (
            (scores_matrix IS NULL) OR (
                (scores_matrix->>'winner') IS NULL AND
                (scores_matrix->>'rank') IS NULL AND
                (scores_matrix->>'recommendation') IS NULL AND
                (scores_matrix->>'best_offer') IS NULL AND
                (scores_matrix->>'selected_vendor') IS NULL
            )
        )
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE evaluation_documents
        DROP CONSTRAINT IF EXISTS no_winner_field
        """)

    for table in reversed(_TABLES):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS workspace_id")
