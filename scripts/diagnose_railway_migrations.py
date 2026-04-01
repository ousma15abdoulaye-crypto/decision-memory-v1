#!/usr/bin/env python3
"""Diagnostic des migrations Railway — identifie la revision actuelle et les ecarts.

Usage :
    python scripts/diagnose_railway_migrations.py
    python scripts/diagnose_railway_migrations.py --db-url "postgresql+psycopg://..."

Requis :
    RAILWAY_DATABASE_URL ou DATABASE_URL (env) ou --db-url (CLI).
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _script_directory():
    """Script Alembic du dépôt — même source de vérité que `alembic heads`."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    return ScriptDirectory.from_config(cfg)


def _get_db_url(cli_url: str | None = None) -> str:
    url = (
        cli_url
        or os.environ.get("RAILWAY_DATABASE_URL", "").strip()
        or os.environ.get("DATABASE_URL", "").strip()
    )
    if not url:
        print(
            "ERREUR : aucune URL de base de donnees fournie.\n"
            "Definir RAILWAY_DATABASE_URL, DATABASE_URL, ou --db-url.",
            file=sys.stderr,
        )
        sys.exit(1)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if "postgresql+psycopg" not in url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _get_local_head() -> str:
    """Head local = `alembic heads` (ScriptDirectory), pas un parse naïf des fichiers.

    L'ancienne heuristique (révisions − parents) échouait dès qu'une ligne
    `down_revision = ...` contenait un commentaire `#` inline (ex. 004_users_rbac.py),
    ce qui faisait apparaître à tort `003_add_procurement_extensions` comme second head.
    """
    try:
        script = _script_directory()
        heads = script.get_heads()
        if len(heads) == 1:
            return heads[0]
        if len(heads) > 1:
            return f"MULTIPLE HEADS (alembic) : {sorted(heads)}"
        return "INCONNU (aucun head)"
    except Exception as exc:
        return f"INCONNU ({exc})"


def _build_chain(head_revision: str) -> list[str]:
    """Chaîne ordonnée base → head (même graphe qu'Alembic, merge inclus)."""
    try:
        script = _script_directory()
        revs = list(script.walk_revisions("base", head_revision))
        return [r.revision for r in reversed(revs)]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Diagnostic migrations Railway DMS")
    parser.add_argument("--db-url", help="URL PostgreSQL (override env)")
    args = parser.parse_args()

    db_url = _get_db_url(args.db_url)
    safe_url = db_url.split("@")[-1] if "@" in db_url else "***"
    print(f":: Cible DB : ...@{safe_url}")

    local_head = _get_local_head()
    print(f":: Head Alembic local : {local_head}")

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import ProgrammingError

        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            try:
                row = conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).fetchone()
                if row:
                    db_revision = row[0]
                else:
                    db_revision = "(table vide — aucune migration appliquee)"
            except ProgrammingError as exc:
                if "alembic_version" in str(exc).lower():
                    db_revision = (
                        "(table alembic_version absente — aucune migration appliquee)"
                    )
                else:
                    raise
    except Exception as exc:
        print(f"ERREUR connexion DB : {exc}", file=sys.stderr)
        print(
            "\nDiagnostic partiel (sans acces DB) :",
        )
        print(f"  Head local : {local_head}")
        print("  Verifier manuellement : SELECT version_num FROM alembic_version;")
        sys.exit(1)

    print(f":: Revision DB actuelle : {db_revision}")

    if local_head.startswith("INCONNU") or local_head.startswith("MULTIPLE"):
        print(f"\n[ATTENTION] Head local non utilisable : {local_head}")
        return

    if db_revision == local_head:
        print("\n[OK] La DB est synchronisee avec le head local.")
        return

    print(f"\n[ECART] DB={db_revision} vs Local={local_head}")

    chain = _build_chain(local_head)
    if not chain:
        print("  Impossible de construire la chain — verifier manuellement.")
        return

    if db_revision in chain:
        idx = chain.index(db_revision)
        missing = chain[idx + 1 :]
        print(f"\n  Migrations manquantes ({len(missing)}) :")
        for i, rev in enumerate(missing, 1):
            marker = " <-- HEAD" if rev == local_head else ""
            print(f"    {i:3d}. {rev}{marker}")
    else:
        print(
            f"\n  ATTENTION : la revision DB '{db_revision}' n'est pas dans la chain locale."
        )
        print("  Cela peut indiquer une migration renommee ou supprimee.")
        print("  Verifier manuellement avec : alembic history")

    print("\n:: Recommandation :")
    print("  1. Verifier que les tables pre-requises existent (pas de DROP accidentel)")
    print("  2. Appliquer avec : alembic upgrade head  (ou une par une)")
    print("  3. Sur Railway : DMS_ALLOW_RAILWAY_MIGRATE=1 dans les Variables")


if __name__ == "__main__":
    main()
