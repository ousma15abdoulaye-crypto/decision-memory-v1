"""Enforce append-only constraints on audit tables.

Revision ID: 010_enforce_append_only_audit
Revises: 009_supplier_scores_eliminations
Create Date: 2026-02-18

Constitution V3.3.2 §8: Tables d'audit doivent être append-only.
REVOKE DELETE et UPDATE sur tables critiques.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = "010_enforce_append_only_audit"
down_revision = ("009_add_supplier_scoring_tables", "009_supplier_scores_eliminations")
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None):
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    if hasattr(target, "execute"):
        target.execute(text(sql))
        if hasattr(target, "commit"):
            target.commit()
    else:
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()


def _table_exists(bind, table_name: str) -> bool:
    """Vérifie si une table existe dans le schéma public."""
    if hasattr(bind, "execute"):
        result = bind.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """),
            {"table_name": table_name}
        )
        return result.fetchone()[0]
    else:
        with bind.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """),
                {"table_name": table_name}
            )
            return result.fetchone()[0]


def _revoke_write_privileges_from_grantees(bind, table_name: str) -> None:
    """Révoque DELETE et UPDATE sur une table pour tous les rôles qui en disposent."""
    # Récupérer tous les rôles qui ont DELETE ou UPDATE sur cette table
    if hasattr(bind, "execute"):
        result = bind.execute(
            text("""
                SELECT DISTINCT grantee
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public'
                AND table_name = :table_name
                AND privilege_type IN ('DELETE', 'UPDATE')
            """),
            {"table_name": table_name}
        )
        grantees = [row[0] for row in result.fetchall()]
    else:
        with bind.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT DISTINCT grantee
                    FROM information_schema.role_table_grants
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                    AND privilege_type IN ('DELETE', 'UPDATE')
                """),
                {"table_name": table_name}
            )
            grantees = [row[0] for row in result.fetchall()]
    
    # Révoquer DELETE et UPDATE pour chaque rôle
    for grantee in grantees:
        if grantee != "PUBLIC":  # PUBLIC sera traité séparément
            _execute_sql(
                bind,
                f"REVOKE DELETE, UPDATE ON {table_name} FROM {grantee};"
            )
    
    # Révoquer pour PUBLIC également
    _execute_sql(
        bind,
        f"REVOKE DELETE, UPDATE ON {table_name} FROM PUBLIC;"
    )


def _enforce_append_only(bind, table_name: str, comment: str) -> None:
    """Applique les contraintes append-only sur une table."""
    if not _table_exists(bind, table_name):
        # Table n'existe pas encore, skip
        return
    
    # Révoquer DELETE et UPDATE pour tous les rôles
    _revoke_write_privileges_from_grantees(bind, table_name)
    
    # Ajouter un commentaire explicatif
    _execute_sql(
        bind,
        f"COMMENT ON TABLE {table_name} IS '{comment}';"
    )


def upgrade(engine: Optional[Engine] = None) -> None:
    """Révoquer DELETE et UPDATE sur tables d'audit (append-only)."""
    bind = _get_bind(engine)

    # Tables d'audit Couche A
    _enforce_append_only(
        bind,
        "audits",
        "Append-only audit trail (Constitution V3.3.2 §8)"
    )

    # Tables Couche B (mémoire marché)
    _enforce_append_only(
        bind,
        "market_signals",
        "Append-only market memory (Constitution V3.3.2 §8)"
    )

    _enforce_append_only(
        bind,
        "memory_entries",
        "Append-only memory entries (Constitution V3.3.2 §8)"
    )


def downgrade(engine: Optional[Engine] = None) -> None:
    """Restaurer permissions DELETE et UPDATE (pour rollback uniquement)."""
    bind = _get_bind(engine)

    _execute_sql(bind, "GRANT DELETE, UPDATE ON audits TO PUBLIC;")
    _execute_sql(bind, "GRANT DELETE, UPDATE ON market_signals TO PUBLIC;")
    _execute_sql(bind, "GRANT DELETE, UPDATE ON memory_entries TO PUBLIC;")
