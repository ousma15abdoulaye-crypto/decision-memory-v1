# src/db/connection.py
"""
Connexion DB centralisée.
Constitution V3.3.2 §3 : pas d'ORM, requêtes paramétrées.
"""

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from src.db.tenant_context import (
    get_rls_is_admin,
    get_rls_tenant_id,
    get_rls_user_id,
)

load_dotenv()


def _apply_rls_session_settings(cur) -> None:
    """Pose app.tenant_id / app.is_admin / app.user_id pour les policies RLS."""
    tid = get_rls_tenant_id()
    if tid:
        cur.execute(
            "SELECT set_config('app.tenant_id', %s, true)",
            (tid,),
        )
    if get_rls_is_admin():
        cur.execute(
            "SELECT set_config('app.is_admin', 'true', true)",
        )
    uid = get_rls_user_id()
    if uid:
        cur.execute(
            "SELECT set_config('app.user_id', %s, true)",
            (uid,),
        )


def apply_rls_session_vars_to_connection(conn: psycopg.Connection) -> None:
    """Applique le même contexte RLS que `get_db_cursor` sur une connexion psycopg brute.

    À appeler après `psycopg.connect` dans les dépendances FastAPI qui ne passent pas
    par `get_db_cursor` (ex. pipeline, analysis_summary, committee) une fois que
    `get_current_user` / `require_case_access_dep` ont posé le contexte requête.
    """
    with conn.cursor() as cur:
        _apply_rls_session_settings(cur)


@contextmanager
def get_db_cursor():
    """
    Fournit un cursor psycopg avec dict_row.
    Commit automatique si pas d'exception.
    Rollback automatique si exception.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url or not database_url.strip():
        raise RuntimeError("DATABASE_URL manquant.")
    if "sqlite" in database_url.lower():
        raise RuntimeError("SQLite interdit — PostgreSQL uniquement.")
    # psycopg v3 : retirer le préfixe +psycopg si présent
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            _apply_rls_session_settings(cur)
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
