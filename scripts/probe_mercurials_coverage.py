#!/usr/bin/env python3
"""
probe_mercurials_coverage.py — Phase 3.1 M15 / Mesurer couverture mercurials_item_map.

Mesure le ratio items du dictionnaire couverts par au moins un mercuriel.
Si coverage < 70% -> exporte unmapped_items.csv pour mapping manuel.

Usage :
  python scripts/with_railway_env.py python scripts/probe_mercurials_coverage.py
  python scripts/with_railway_env.py python scripts/probe_mercurials_coverage.py --export-unmapped

Colonnes reelles mercurials_item_map (verifiees Railway 2026-04-03) :
  item_canonical, dict_item_id, score, confiance

ZERO ECRITURE. --export-unmapped ecrit unmapped_items.csv.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

GATE_COVERAGE_PCT = 70.0


def _get_url() -> str:
    url = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(
            f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL absente.",
            file=sys.stderr,
        )
        sys.exit(2)
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def _connect(url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        sys.exit(2)
    return psycopg.connect(
        url, row_factory=dict_row, connect_timeout=20, autocommit=True
    )


def measure_coverage(cur) -> dict:
    """Mesure la couverture mercurials_item_map."""
    cur.execute(
        "SELECT COUNT(DISTINCT dict_item_id) AS mapped FROM public.mercurials_item_map"
    )
    mapped = int(cur.fetchone()["mapped"])

    cur.execute("SELECT COUNT(*) AS total FROM couche_b.procurement_dict_items")
    total = int(cur.fetchone()["total"])

    pct = round(mapped * 100.0 / total, 2) if total else 0.0
    unmapped = total - mapped
    gate_ok = pct >= GATE_COVERAGE_PCT

    return {
        "mapped": mapped,
        "total": total,
        "unmapped": unmapped,
        "coverage_pct": pct,
        "gate_ok": gate_ok,
    }


def fetch_unmapped_items(cur) -> list[dict]:
    """Retourne les items du dictionnaire sans mapping mercuriel."""
    cur.execute("""
        SELECT
            pdi.item_id,
            pdi.item_code,
            pdi.label_fr,
            pdi.taxo_l1,
            pdi.taxo_l2,
            pdi.label_status,
            COUNT(DISTINCT ms.id)            AS signal_count,
            COUNT(DISTINCT mim.dict_item_id) AS mercuriel_count
        FROM couche_b.procurement_dict_items pdi
        LEFT JOIN public.market_signals_v2 ms
            ON ms.item_id = pdi.item_id
        LEFT JOIN public.mercurials_item_map mim
            ON mim.dict_item_id = pdi.item_id
        GROUP BY pdi.item_id, pdi.item_code, pdi.label_fr,
                 pdi.taxo_l1, pdi.taxo_l2, pdi.label_status
        HAVING COUNT(DISTINCT mim.dict_item_id) = 0
        ORDER BY signal_count DESC, pdi.taxo_l1, pdi.label_fr
        LIMIT 200
    """)
    return [dict(r) for r in cur.fetchall()]


def fetch_coverage_by_taxo(cur) -> list[dict]:
    """Couverture par famille taxonomique L1."""
    cur.execute("""
        SELECT
            pdi.taxo_l1,
            COUNT(DISTINCT pdi.item_id)              AS total_items,
            COUNT(DISTINCT mim.dict_item_id)         AS mapped_items,
            ROUND(
                COUNT(DISTINCT mim.dict_item_id) * 100.0
                / NULLIF(COUNT(DISTINCT pdi.item_id), 0),
                2
            )                                        AS coverage_pct
        FROM couche_b.procurement_dict_items pdi
        LEFT JOIN public.mercurials_item_map mim
            ON mim.dict_item_id = pdi.item_id
        GROUP BY pdi.taxo_l1
        ORDER BY coverage_pct ASC NULLS FIRST
    """)
    return [dict(r) for r in cur.fetchall()]


def export_unmapped_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        print(f"  {YELLOW}[WARN]{RESET} Aucun item a mapper.")
        return
    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: (str(v) if v is not None else "") for k, v in row.items()}
            )
    print(f"  {GREEN}[OK]{RESET} CSV ecrit : {output_path} ({len(rows)} items)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe couverture mercurials_item_map (Phase 3.1 M15)"
    )
    parser.add_argument(
        "--export-unmapped",
        action="store_true",
        help="Exporter les items sans mapping dans docs/data/unmapped_items.csv",
    )
    args = parser.parse_args()

    url = _get_url()
    target = url.split("@")[-1].split("/")[0] if "@" in url else url[:30]

    print(f"\n{BOLD}PROBE COUVERTURE MERCURIALS_ITEM_MAP{RESET}")
    print(f"Cible : {target}")
    print()

    conn = _connect(url)
    with conn.cursor() as cur:
        cov = measure_coverage(cur)
        taxo_rows = fetch_coverage_by_taxo(cur)
        unmapped_rows = (
            fetch_unmapped_items(cur)
            if (not cov["gate_ok"] or args.export_unmapped)
            else []
        )

    conn.close()

    # Affichage resultats
    pct = cov["coverage_pct"]
    color = GREEN if cov["gate_ok"] else YELLOW
    print(f"  Items dict total    : {cov['total']}")
    print(f"  Items mappes        : {cov['mapped']}")
    print(f"  Items non mappes    : {cov['unmapped']}")
    print(f"  {color}Coverage            : {pct}%{RESET}")
    print(
        f"  Gate >= {GATE_COVERAGE_PCT}%       : {color}{'VERT' if cov['gate_ok'] else 'ROUGE'}{RESET}"
    )

    print(f"\n  {BOLD}Couverture par famille L1 :{RESET}")
    for r in taxo_rows:
        c = float(r.get("coverage_pct") or 0)
        col = GREEN if c >= 70 else (YELLOW if c >= 40 else RED)
        taxo_label = str(r["taxo_l1"] or "NULL")
        print(
            f"  {col}{taxo_label:30}{RESET} {r['mapped_items']:4}/{r['total_items']:4} = {r['coverage_pct']}%"
        )

    if not cov["gate_ok"]:
        print(
            f"\n  {YELLOW}[ACTION REQUISE]{RESET} Coverage {pct}% < {GATE_COVERAGE_PCT}%\n"
            f"  A mapper : {cov['unmapped']} items (seuil : {int(cov['total'] * GATE_COVERAGE_PCT / 100) - cov['mapped'] + 1} min)\n"
            f"  Utiliser --export-unmapped pour generer la liste prioritaire."
        )
    else:
        print(f"\n  {GREEN}[OK]{RESET} Gate couverture atteint — Phase 3.2 deblocable.")

    if args.export_unmapped or not cov["gate_ok"]:
        output_path = ROOT / "docs" / "data" / "unmapped_items.csv"
        export_unmapped_csv(unmapped_rows, output_path)

    return 0 if cov["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
