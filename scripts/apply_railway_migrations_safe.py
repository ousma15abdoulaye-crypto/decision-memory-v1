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
import functools
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


@functools.lru_cache(maxsize=1)
def _script_directory():
    """Graphe Alembic du dépôt — aligné ``diagnose_railway_migrations.py`` (merges inclus)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(REPO_ROOT))
    return ScriptDirectory.from_config(cfg)


def _revision_chain_base_to_head(head_revision: str) -> list[str]:
    """Révisions ordonnées base → ``head_revision`` (inclus), via ``walk_revisions``."""
    script = _script_directory()
    revs = list(script.walk_revisions("base", head_revision))
    return [r.revision for r in reversed(revs)]


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


def _get_pending_migrations(raw_url: str) -> list[str]:
    """Retourne la liste des revisions non appliquees, dans l'ordre (API ScriptDirectory)."""
    script = _script_directory()
    heads = script.get_heads()
    if not heads:
        print("ERREUR : impossible de determiner le head Alembic.", file=sys.stderr)
        sys.exit(1)
    if len(heads) > 1:
        print(
            f"STOP-1 : Multiple heads detectes : {sorted(heads)}",
            file=sys.stderr,
        )
        sys.exit(1)

    target_head = heads[0]
    current = _get_current_revision(raw_url)

    if current == target_head:
        return []

    chain = _revision_chain_base_to_head(target_head)
    if current is None:
        return chain

    try:
        idx = chain.index(current)
    except ValueError:
        print(
            f"ERREUR : revision DB {current!r} absente du graphe Alembic vers {target_head!r}.",
            file=sys.stderr,
        )
        sys.exit(1)
    return chain[idx + 1 :]


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
