"""Linearize post-v52_p2 (merge obsolète — chaîne unique 077 → … → v52_p2)

Revision ID: 6ce2036bd346
Revises: v52_p2_001_price_line_market_delta
Create Date: 2026-04-10 23:04:16.333698

Historique : une première version fusionnait `076_fix_offer_extractions_fk_to_bundles`
avec `v52_p2_001` alors que la branche offer_extractions était parallèle à la ligne
RBAC (`075_rbac` / `076_evaluation_documents_*`). Après correction du graphe
(`075_fix_offer_extractions` → `076_fix_offer_extractions` → `077`), tout chemin
vers `v52_p2_001` inclut déjà ces révisions : ce nœud devient un simple no-op après
`v52_p2_001` pour conserver l’id `6ce2036bd346` déjà déployé.

"""

# revision identifiers, used by Alembic.
revision = "6ce2036bd346"
down_revision = "v52_p2_001_price_line_market_delta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
