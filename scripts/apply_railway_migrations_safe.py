#!/usr/bin/env python3
"""Applique les migrations Alembic une par une avec verification entre chaque etape.

Usage :
    python scripts/apply_railway_migrations_safe.py --dry-run
    python scripts/apply_railway_migrations_safe.py --apply
    python scripts/apply_railway_migrations_safe.py --apply --db-url "postgresql+psycopg://..."

Securites :
    - Mode dry-run par defaut (ne fait rien sans --apply)
    - Applique les migrations une par une
    - Verifie que chaque migration a bien ete appliquee
    - S'arrete immediatement si une migration echoue
    - Log detaille de chaque etape
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _get_db_url(cli_url: str | None = None) -> str:
    url = (
        cli_url
        or os.environ.get("RAILWAY_DATABASE_URL", "").strip()
        or os.environ.get("DATABASE_URL", "").strip()
    )
    if not url:
        print(
            "ERREUR : aucune URL de base de donnees fournie.",
            file=sys.stderr,
        )
        sys.exit(1)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if "postgresql+psycopg" not in url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _get_current_revision(db_url: str) -> str | None:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        return row[0] if row else None


def _get_pending_migrations(db_url: str) -> list[str]:
    """Retourne la liste des revisions non appliquees, dans l'ordre."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url

    subprocess.run(
        ["alembic", "history", "--verbose"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )

    current = _get_current_revision(db_url)

    result_heads = subprocess.run(
        ["alembic", "heads"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    heads_output = result_heads.stdout.strip()
    head_revisions = []
    for line in heads_output.splitlines():
        rev = line.strip().split(" ")[0] if line.strip() else ""
        if rev:
            head_revisions.append(rev)

    if not head_revisions:
        print("ERREUR : impossible de determiner le head Alembic.", file=sys.stderr)
        sys.exit(1)

    if len(head_revisions) > 1:
        print(
            f"STOP-1 : Multiple heads detectes : {head_revisions}",
            file=sys.stderr,
        )
        sys.exit(1)

    target_head = head_revisions[0]

    if current == target_head:
        return []

    result_pending = subprocess.run(
        ["alembic", "history", f"{current or 'base'}:{target_head}"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )

    pending = []
    for line in result_pending.stdout.strip().splitlines():
        line = line.strip()
        if " -> " in line:
            parts = line.split(" -> ")
            if len(parts) >= 2:
                rev = parts[1].split(" ")[0].split(",")[0].strip()
                if rev:
                    pending.append(rev)

    pending.reverse()
    return pending


def main():
    parser = argparse.ArgumentParser(
        description="Applique les migrations Railway une par une"
    )
    parser.add_argument("--db-url", help="URL PostgreSQL (override env)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer les migrations (sans ce flag = dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode simulation (defaut)",
    )
    args = parser.parse_args()

    db_url = _get_db_url(args.db_url)
    safe_url = db_url.split("@")[-1] if "@" in db_url else "***"
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f":: Mode : {mode}")
    print(f":: Cible : ...@{safe_url}")

    current = _get_current_revision(db_url)
    print(f":: Revision actuelle : {current or '(aucune)'}")

    pending = _get_pending_migrations(db_url)
    if not pending:
        print("\n[OK] Aucune migration en attente. La DB est a jour.")
        return

    print(f"\n:: {len(pending)} migration(s) en attente :")
    for i, rev in enumerate(pending, 1):
        print(f"    {i:3d}. {rev}")

    if not args.apply:
        print("\n:: DRY-RUN — aucune migration appliquee.")
        print(f":: Pour appliquer : python {__file__} --apply")
        return

    print("\n:: Application sequentielle...")
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url

    for i, rev in enumerate(pending, 1):
        print(f"\n  [{i}/{len(pending)}] Upgrade vers {rev}...")
        t0 = time.time()

        result = subprocess.run(
            ["alembic", "upgrade", rev],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )

        elapsed = time.time() - t0

        if result.returncode != 0:
            print(f"  ECHEC ({elapsed:.1f}s) !")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            print(f"\n:: ARRET IMMEDIAT — la migration {rev} a echoue.")
            print(f":: Revision actuelle apres echec : {_get_current_revision(db_url)}")
            sys.exit(1)

        new_current = _get_current_revision(db_url)
        if new_current != rev:
            print(
                f"  ATTENTION : apres upgrade, la revision est {new_current} "
                f"(attendu {rev})"
            )
        else:
            print(f"  OK ({elapsed:.1f}s) — revision = {rev}")

    final = _get_current_revision(db_url)
    print(f"\n:: Terminé. Revision finale : {final}")
    print(f":: {len(pending)} migration(s) appliquee(s) avec succes.")


if __name__ == "__main__":
    main()
