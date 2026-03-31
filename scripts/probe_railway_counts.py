#!/usr/bin/env python3
"""
probe_railway_counts.py  v1
---------------------------
Probe lecture seule sur Railway (ou DB locale) — compte les lignes critiques.
Zero ecriture. Utilisable avant / apres chaque lot de migration.

Usage :
  python scripts/probe_railway_counts.py              # DB locale
  python scripts/probe_railway_counts.py --railway    # Railway

Tables sondees :
  public        : documents, vendors, mercurials, cases, extraction_jobs
  couche_a      : agent_checkpoints, agent_runs_log
  couche_b      : procurement_dict_items, procurement_dict_aliases
  public        : m12_correction_log (si migration 054 appliquee)
  alembic_version (affiche la tete courante)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _load_dotenv() -> None:
    for name in (".env.local", ".env"):
        p = _PROJECT_ROOT / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


_PROBES: list[tuple[str, str, str]] = [
    # (schema_check, table_fqn, label)
    ("public", "public.documents", "documents"),
    ("public", "public.vendors", "vendors"),
    ("public", "public.cases", "cases"),
    ("public", "public.mercurials", "mercurials"),
    ("public", "public.extraction_jobs", "extraction_jobs (SLA-B queue)"),
    ("couche_a", "couche_a.agent_checkpoints", "agent_checkpoints"),
    ("couche_a", "couche_a.agent_runs_log", "agent_runs_log"),
    ("couche_b", "couche_b.procurement_dict_items", "dict_items"),
    ("couche_b", "couche_b.procurement_dict_aliases", "dict_aliases"),
    ("public", "public.m12_correction_log", "m12_correction_log (migration 054)"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Railway counts (read-only).")
    parser.add_argument(
        "--railway", action="store_true", help="Utiliser RAILWAY_DATABASE_URL."
    )
    args = parser.parse_args()

    _load_dotenv()

    if args.railway:
        db_url = os.environ.get("RAILWAY_DATABASE_URL", "")
        label = "Railway"
        if not db_url:
            print(f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL absente.")
            return 2
    else:
        db_url = os.environ.get("DATABASE_URL", "")
        label = "Local"
        if not db_url:
            print(f"{RED}[ERR]{RESET} DATABASE_URL absente.")
            return 2

    try:
        import psycopg
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe — pip install psycopg[binary]")
        return 2

    print(f"\n{BOLD}=== Probe Counts — {label} ==={RESET}")

    try:
        conn = psycopg.connect(_normalize_url(db_url), connect_timeout=15)
        cur = conn.cursor()

        # Alembic head
        try:
            cur.execute("SELECT version_num FROM alembic_version")
            rows = cur.fetchall()
            heads = [r[0] for r in rows]
            print(f"{GREEN}[OK]{RESET}   alembic_version           : {heads}")
        except Exception as e:
            print(f"{YELLOW}[WARN]{RESET} alembic_version : {e}")

        # Schemas disponibles
        cur.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT IN ('information_schema','pg_catalog','pg_toast') "
            "ORDER BY schema_name"
        )
        schemas = {r[0] for r in cur.fetchall()}
        print(f"{BLUE}[->]{RESET}   schemas                   : {sorted(schemas)}")

        print()
        # Tables
        stops = []
        for schema, table_fqn, label_col in _PROBES:
            if schema not in schemas:
                print(
                    f"  {YELLOW}SKIP{RESET}  {label_col:40} (schema '{schema}' absent)"
                )
                continue
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table_fqn}")
                count = cur.fetchone()[0]
                print(f"  {GREEN}OK{RESET}    {label_col:40} : {count:,}")
            except Exception as e:
                msg = str(e)[:80]
                print(f"  {YELLOW}WARN{RESET}  {label_col:40} : {msg}")

        # Triggers couche_b
        if "couche_b" in schemas:
            print()
            expected_triggers = {
                "trg_dict_compute_hash",
                "trg_dict_write_audit",
                "trg_protect_item_identity",
                "trg_protect_item_with_aliases",
            }
            cur.execute(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE trigger_schema = 'couche_b' "
                "AND event_object_table = 'procurement_dict_items' "
                "ORDER BY trigger_name"
            )
            found_triggers = {r[0] for r in cur.fetchall()}
            missing = expected_triggers - found_triggers
            if missing:
                stops.append(f"Triggers manquants couche_b : {missing}")
                print(f"  {RED}STOP{RESET}  triggers couche_b : MANQUANTS {missing}")
            else:
                print(f"  {GREEN}OK{RESET}    triggers couche_b : tous presents")

        conn.close()

        if stops:
            print(f"\n{RED}{BOLD}STOPS DETECTES — NE PAS CONTINUER{RESET}")
            for s in stops:
                print(f"  {RED}{s}{RESET}")
            return 1

        print(f"\n{GREEN}{BOLD}PROBE OK — {label} operationnel{RESET}")
        return 0

    except Exception as e:
        print(f"{RED}[ERR]{RESET} DB inaccessible : {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
