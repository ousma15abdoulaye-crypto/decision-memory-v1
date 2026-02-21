"""022_seed_procurement_dict_v1_sahel

M-NORMALISATION-ITEMS — Étape 2 (ADR-0002)
- Charge le seed versionné db/seeds/procurement_dict_v1.sql
- Idempotent : ON CONFLICT géré dans le SQL
- Exécution statement par statement (anti-échecs silencieux)
"""

from pathlib import Path

from alembic import op

revision = "022_seed_dict_sahel"
down_revision = "021_m_normalisation_items_tables"
branch_labels = None
depends_on = None


def _load_seed_sql() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    seed_path = repo_root / "db" / "seeds" / "procurement_dict_v1.sql"
    if not seed_path.exists():
        raise RuntimeError(f"Seed file manquant : {seed_path}")
    return seed_path.read_text(encoding="utf-8")


def upgrade() -> None:
    sql = _load_seed_sql()
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        # PostgreSQL ignore naturellement les commentaires inline,
        # on exécute tous les statements y compris ceux commençant par --.
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DELETE FROM couche_b.procurement_dict_unit_conversions;")
    op.execute("DELETE FROM couche_b.procurement_dict_aliases;")
    op.execute("DELETE FROM couche_b.procurement_dict_items;")
    op.execute("DELETE FROM couche_b.procurement_dict_units;")
    op.execute("DELETE FROM couche_b.procurement_dict_families;")
