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
    """Lit le head Alembic local via la chain de fichiers."""
    versions_dir = REPO_ROOT / "alembic" / "versions"
    if not versions_dir.is_dir():
        return "INCONNU (dossier alembic/versions/ absent)"

    all_revisions: set[str] = set()
    all_down_revisions: set[str] = set()

    for py_file in versions_dir.glob("*.py"):
        if py_file.name == "__pycache__":
            continue
        revision = None
        down_revision = None
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("revision =") or stripped.startswith(
                    "revision="
                ):
                    revision = stripped.split("=", 1)[1].strip().strip("\"'")
                if stripped.startswith("down_revision =") or stripped.startswith(
                    "down_revision="
                ):
                    val = stripped.split("=", 1)[1].strip().strip("\"'")
                    if val and val != "None":
                        if "(" in val:
                            parts = val.strip("()").split(",")
                            for p in parts:
                                p = p.strip().strip("\"'")
                                if p:
                                    all_down_revisions.add(p)
                        else:
                            down_revision = val
        except Exception:
            continue
        if revision:
            all_revisions.add(revision)
        if down_revision:
            all_down_revisions.add(down_revision)

    heads = all_revisions - all_down_revisions
    if len(heads) == 1:
        return heads.pop()
    if len(heads) > 1:
        return f"MULTIPLE HEADS : {sorted(heads)}"
    return "INCONNU (aucun head detecte)"


def _build_chain() -> list[str]:
    """Construit la chain ordonnee des revisions depuis le head."""
    versions_dir = REPO_ROOT / "alembic" / "versions"
    rev_to_down: dict[str, str | None] = {}

    for py_file in versions_dir.glob("*.py"):
        revision = None
        down_revision = None
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("revision ="):
                    revision = stripped.split("=", 1)[1].strip().strip("\"'")
                if stripped.startswith("down_revision ="):
                    val = stripped.split("=", 1)[1].strip().strip("\"'")
                    if val and val != "None" and "(" not in val:
                        down_revision = val
        except Exception:
            continue
        if revision:
            rev_to_down[revision] = down_revision

    down_to_rev: dict[str | None, list[str]] = {}
    for rev, down in rev_to_down.items():
        down_to_rev.setdefault(down, []).append(rev)

    all_downs = set(rev_to_down.values()) - {None}
    all_revs = set(rev_to_down.keys())
    heads = all_revs - all_downs

    if not heads:
        return []

    head = sorted(heads)[0]
    chain = [head]
    visited = {head}
    current = head
    while current in rev_to_down and rev_to_down[current]:
        current = rev_to_down[current]
        if current in visited:
            break
        visited.add(current)
        chain.append(current)

    chain.reverse()
    return chain


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
                    db_revision = "(table alembic_version absente — aucune migration appliquee)"
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

    if db_revision == local_head:
        print("\n[OK] La DB est synchronisee avec le head local.")
        return

    print(f"\n[ECART] DB={db_revision} vs Local={local_head}")

    chain = _build_chain()
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
