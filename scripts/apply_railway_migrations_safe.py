#!/usr/bin/env python3
"""Applique les migrations Alembic une par une avec verification entre chaque etape.

Usage :
    python scripts/apply_railway_migrations_safe.py
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dms_pg_connect import (  # noqa: E402
    alembic_database_url,
    get_raw_database_url,
    psycopg_connect_kwargs,
    safe_target_hint,
)


def _get_db_url(cli_url: str | None = None) -> str:
    try:
        return get_raw_database_url(cli_url)
    except ValueError as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        sys.exit(1)


def _get_current_revision(raw_url: str) -> str | None:
    import psycopg
    from psycopg import errors as pg_errors

    conn_kw = psycopg_connect_kwargs(raw_url)
    with psycopg.connect(**conn_kw) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
                row = cur.fetchone()
            except pg_errors.UndefinedTable:
                return None
            return row[0] if row else None


def _parse_history_edges(stdout: str) -> dict[str, str]:
    """parent_rev -> enfant_rev depuis `alembic history -r` (une ligne = une arete)."""
    child_of: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        line = line.strip()
        if " -> " not in line:
            continue
        left, rest = line.split(" -> ", 1)
        parent = left.split()[0].strip()
        if parent.startswith("<") and parent.endswith(">"):
            parent = parent[1:-1]
        child = rest.split()[0].strip().rstrip(",")
        if parent and child:
            child_of[parent] = child
    return child_of


def _pending_chain(
    current: str | None, target_head: str, child_of: dict[str, str]
) -> list[str]:
    """Revisions a appliquer dans l'ordre pour aller de current a target_head."""
    cur = "base" if current is None else current
    pending: list[str] = []
    while cur != target_head:
        nxt = child_of.get(cur)
        if nxt is None:
            print(
                f"ERREUR : chaine cassee entre {cur!r} et {target_head!r} "
                "(pas d'arete parent->enfant dans alembic history -r).",
                file=sys.stderr,
            )
            sys.exit(1)
        pending.append(nxt)
        cur = nxt
    return pending


def _get_pending_migrations(raw_url: str) -> list[str]:
    """Retourne la liste des revisions non appliquees, dans l'ordre."""
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url(raw_url)

    result_history = subprocess.run(
        ["alembic", "history", "--verbose"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result_history.returncode != 0:
        print(
            "ERREUR : echec de la commande 'alembic history --verbose'.",
            file=sys.stderr,
        )
        if result_history.stderr:
            print(result_history.stderr.strip(), file=sys.stderr)
        sys.exit(1)

    current = _get_current_revision(raw_url)

    result_heads = subprocess.run(
        ["alembic", "heads"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result_heads.returncode != 0:
        print("ERREUR : echec de la commande 'alembic heads'.", file=sys.stderr)
        if result_heads.stderr:
            print(result_heads.stderr.strip(), file=sys.stderr)
        sys.exit(1)
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
        [
            "alembic",
            "history",
            "-r",
            f"{current or 'base'}:{target_head}",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result_pending.returncode != 0:
        print(
            "ERREUR : echec de la commande 'alembic history -r <debut>:<fin>'.",
            file=sys.stderr,
        )
        if result_pending.stderr:
            print(result_pending.stderr.strip(), file=sys.stderr)
        sys.exit(1)

    child_of = _parse_history_edges(result_pending.stdout)
    return _pending_chain(current, target_head, child_of)


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
    args = parser.parse_args()

    raw_url = _get_db_url(args.db_url)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f":: Mode : {mode}")
    print(f":: Cible : {safe_target_hint(raw_url)}")

    current = _get_current_revision(raw_url)
    print(f":: Revision actuelle : {current or '(aucune)'}")

    pending = _get_pending_migrations(raw_url)
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
    env["DATABASE_URL"] = alembic_database_url(raw_url)

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
            print(
                f":: Revision actuelle apres echec : {_get_current_revision(raw_url)}"
            )
            sys.exit(1)

        new_current = _get_current_revision(raw_url)
        if new_current != rev:
            print(
                f"  ATTENTION : apres upgrade, la revision est {new_current} "
                f"(attendu {rev})"
            )
        else:
            print(f"  OK ({elapsed:.1f}s) — revision = {rev}")

    final = _get_current_revision(raw_url)
    print(f"\n:: Terminé. Revision finale : {final}")
    print(f":: {len(pending)} migration(s) appliquee(s) avec succes.")


if __name__ == "__main__":
    main()
