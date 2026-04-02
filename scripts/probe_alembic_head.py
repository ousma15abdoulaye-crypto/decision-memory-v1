#!/usr/bin/env python3
"""
probe_alembic_head.py  v1
-------------------------
Probe de tete Alembic sur la DB locale OU Railway (lecture seule).
Affiche le delta exact (migrations pending) entre la DB cible et le repo.

Usage :
  python scripts/probe_alembic_head.py              # probe DB locale
  python scripts/probe_alembic_head.py --railway    # probe Railway (RAILWAY_DATABASE_URL)

Code de sortie :
  0  — DB alignee sur le repo head
  1  — DB desynchronisee (delta affiche)
  2  — DB inaccessible ou DATABASE_URL absente
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Chaine ordonnee des migrations depuis 044 jusqu'au head repo (aligner validate_mrd_state.py)
# Mettre a jour manuellement lors de chaque nouvelle migration (REGLE-ANCHOR-05).
KNOWN_CHAIN: list[str] = [
    "044_decision_history",
    "045_agent_native_foundation",
    "046_imc_category_item_map",
    "046b_imc_map_fix_restrict_indexes",
    "047_couche_a_service_columns",
    "048_vendors_sensitive_data",
    "049_validate_pipeline_runs_fk",
    "050_documents_sha256_not_null",
    "051_cases_tenant_user_tenants_rls",
    "052_dm_app_rls_role",
    "053_dm_app_enforce_security_attrs",
    "054_m12_correction_log",
    "055_extend_rls_documents_extraction_jobs",
    "056_evaluation_documents",
    "057_m13_regulatory_profile_and_correction_log",
]

REPO_HEAD = KNOWN_CHAIN[-1]

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


def probe(db_url: str, label: str) -> tuple[list[str], bool]:
    """Probe alembic_version sur une DB. Retourne (versions_list, accessible)."""
    try:
        import psycopg
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe — pip install psycopg[binary]")
        return [], False

    try:
        conn = psycopg.connect(_normalize_url(db_url), connect_timeout=15)
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        rows = cur.fetchall()
        versions = [r[0] for r in rows]
        conn.close()
        return versions, True
    except Exception as e:
        print(f"{RED}[ERR]{RESET} {label} inaccessible : {e}")
        return [], False


def compute_delta(db_versions: list[str]) -> list[str]:
    """Retourne la liste ordonnee des migrations manquantes."""
    if not db_versions:
        return KNOWN_CHAIN[:]
    # Trouver la position courante dans la chaine
    current = None
    for v in db_versions:
        if v in KNOWN_CHAIN:
            idx = KNOWN_CHAIN.index(v)
            if current is None or idx > current:
                current = idx
    if current is None:
        return KNOWN_CHAIN[:]
    return KNOWN_CHAIN[current + 1 :]


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Alembic head vs repo.")
    parser.add_argument(
        "--railway",
        action="store_true",
        help="Probe Railway DB via RAILWAY_DATABASE_URL.",
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

    print(f"\n{BOLD}=== Probe Alembic Head — {label} ==={RESET}")
    print(f"{BLUE}[->]{RESET}  Repo head   : {REPO_HEAD}")

    versions, accessible = probe(db_url, label)
    if not accessible:
        return 2

    print(f"{BLUE}[->]{RESET}  DB versions : {versions}")

    delta = compute_delta(versions)
    if not delta:
        print(f"\n{GREEN}{BOLD}ALIGNE — {label} est a jour ({REPO_HEAD}){RESET}")
        return 0

    print(
        f"\n{RED}{BOLD}DESYNCHRONISE — {len(delta)} migration(s) manquante(s) :{RESET}"
    )
    for i, m in enumerate(delta, 1):
        print(f"  {i:2}. {m}")
    print(
        f"\n{YELLOW}[WARN]{RESET} Appliquer avec DMS_ALLOW_RAILWAY_MIGRATE=1 "
        f"apres GO CTO (voir RAILWAY_MIGRATION_RUNBOOK.md)"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
