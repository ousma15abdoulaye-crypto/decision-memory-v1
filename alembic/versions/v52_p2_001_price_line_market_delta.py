"""v52_p2_001 — Persistance market_delta_pct dans price_line_bundle_values.

Option B (enterprise) : le delta prix-marché est stocké en base et calculé
lors des mises à jour de prix ou de signaux — pas à chaque affichage.

Colonnes ajoutées à price_line_bundle_values :
  market_delta_pct        NUMERIC      delta signé (fournisseur vs marché M9)
  market_delta_computed_at TIMESTAMPTZ horodatage du dernier calcul

Index ajouté à price_line_comparisons :
  idx_plc_workspace_label  (workspace_id, label) pour la jointure item/zone.

Revision ID: v52_p2_001_price_line_market_delta
Revises: v52_p1_003_rls_completion
Create Date: 2026-04-09
"""

from __future__ import annotations

from alembic import op

revision = "v52_p2_001_price_line_market_delta"
down_revision = "v52_p1_003_rls_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── price_line_bundle_values : colonnes delta ──────────────────────────
    op.execute("""
        ALTER TABLE price_line_bundle_values
            ADD COLUMN IF NOT EXISTS market_delta_pct         NUMERIC,
            ADD COLUMN IF NOT EXISTS market_delta_computed_at TIMESTAMPTZ
        """)

    # Index (workspace_id) déjà présent sur price_line_bundle_values via RLS.
    # On ajoute un index composite pour le refresh batch par workspace.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_plbv_ws_delta_stale
            ON price_line_bundle_values (workspace_id, market_delta_computed_at NULLS FIRST)
        """)

    # Index sur label pour la jointure market_delta (similarity + exact match)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_plc_workspace_label
            ON price_line_comparisons (workspace_id, lower(label))
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_plc_workspace_label")
    op.execute("DROP INDEX IF EXISTS idx_plbv_ws_delta_stale")
    op.execute("""
        ALTER TABLE price_line_bundle_values
            DROP COLUMN IF EXISTS market_delta_pct,
            DROP COLUMN IF EXISTS market_delta_computed_at
        """)
