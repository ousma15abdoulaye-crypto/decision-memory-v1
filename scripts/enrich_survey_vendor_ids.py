#!/usr/bin/env python3
"""
enrich_survey_vendor_ids.py — V5 Activation Wartime M15.

ETL vendor_id : enrichit public.market_surveys (vendor_id IS NULL)
en appliquant la logique de fuzzy matching pg_trgm de resolvers.py
(seuil similitude = 60%) sur supplier_raw.

Diagnostic initial :
  - 21 850 market_surveys sans vendor_id (0% match)
  - resolve_vendor() existe dans src/couche_b/resolvers.py
  - pg_trgm disponible sur Railway prod

Procedure :
  1. Probe : compte vendors et surveys sans vendor_id
  2. Dry-run : mesure le taux de match potentiel sans ecriture
  3. Apply : UPDATE market_surveys SET vendor_id = ... WHERE match >= 60%
  4. Rapport : combien matches, taux reel, threshold efficace

Usage :
  python scripts/with_railway_env.py python scripts/enrich_survey_vendor_ids.py --dry-run
  python scripts/with_railway_env.py python scripts/enrich_survey_vendor_ids.py --apply
  python scripts/with_railway_env.py python scripts/enrich_survey_vendor_ids.py --apply --threshold 0.5
  python scripts/with_railway_env.py python scripts/enrich_survey_vendor_ids.py --apply --limit 1000

Gate de sortie V5 :
  SELECT COUNT(*) FILTER (WHERE vendor_id IS NOT NULL) FROM market_surveys > 0
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

DEFAULT_THRESHOLD = 0.60


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", os.environ.get("RAILWAY_DATABASE_URL", ""))
    if not url:
        raise SystemExit(
            f"{RED}[ERR]{RESET} DATABASE_URL manquante.\n"
            "  Lancer via : python scripts/with_railway_env.py python scripts/enrich_survey_vendor_ids.py"
        )
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def probe_state(cur) -> dict:
    """Mesure l'etat initial avant le matching."""
    cur.execute("SELECT COUNT(*) as cnt FROM public.vendors WHERE id IS NOT NULL")
    r = cur.fetchone()
    vendor_count = r["cnt"] if r else 0

    cur.execute(
        "SELECT COUNT(*) as cnt FROM public.market_surveys WHERE vendor_id IS NULL"
    )
    r = cur.fetchone()
    surveys_without_vendor = r["cnt"] if r else 0

    cur.execute(
        "SELECT COUNT(*) as cnt FROM public.market_surveys WHERE vendor_id IS NOT NULL"
    )
    r = cur.fetchone()
    surveys_with_vendor = r["cnt"] if r else 0

    cur.execute(
        "SELECT COUNT(*) as cnt FROM public.market_surveys "
        "WHERE vendor_id IS NULL AND supplier_raw IS NOT NULL AND supplier_raw != ''"
    )
    r = cur.fetchone()
    matchable = r["cnt"] if r else 0

    return {
        "vendors_total": vendor_count,
        "surveys_with_vendor": surveys_with_vendor,
        "surveys_without_vendor": surveys_without_vendor,
        "surveys_matchable": matchable,
    }


def _ensure_pg_trgm(cur) -> bool:
    """Verifie et active pg_trgm si necessaire."""
    try:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        exists = cur.fetchone() is not None
        if not exists:
            logger.warning("pg_trgm non installe — tentative CREATE EXTENSION...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        return True
    except Exception as exc:
        logger.error("pg_trgm non disponible : %s", exc)
        return False


def resolve_vendor_batch(
    cur, threshold: float, limit: int | None, dry_run: bool
) -> dict:
    """
    Applique le matching pg_trgm en une passe SQL (set-based, pas N+1).

    Pour chaque survey avec vendor_id IS NULL et supplier_raw non vide,
    selectionne le meilleur vendor par similarity >= threshold (LATERAL).
    """
    lim_sql = "LIMIT %(lim)s" if limit else ""
    params: dict[str, object] = {"threshold": threshold}
    if limit:
        params["lim"] = int(limit)

    # Requete unique : meilleur vendor par survey (anti N+1)
    sql_matches = f"""
        WITH target_surveys AS (
            SELECT s.id, s.supplier_raw
            FROM public.market_surveys s
            WHERE s.vendor_id IS NULL
              AND s.supplier_raw IS NOT NULL
              AND s.supplier_raw != ''
            ORDER BY s.id
            {lim_sql}
        ),
        best AS (
            SELECT
                ts.id AS survey_id,
                ts.supplier_raw,
                vm.vendor_id,
                vm.vendor_name,
                vm.sim
            FROM target_surveys ts
            LEFT JOIN LATERAL (
                SELECT
                    v.id AS vendor_id,
                    v.name_raw AS vendor_name,
                    similarity(v.name_raw, ts.supplier_raw) AS sim
                FROM public.vendors v
                WHERE similarity(v.name_raw, ts.supplier_raw) >= %(threshold)s
                ORDER BY sim DESC
                LIMIT 1
            ) vm ON TRUE
        )
        SELECT survey_id, supplier_raw, vendor_id, vendor_name, sim
        FROM best
        ORDER BY survey_id
    """

    try:
        cur.execute(sql_matches, params)
        matched_rows = cur.fetchall()
    except Exception as exc:
        logger.error("Erreur requete bulk similarity: %s", exc)
        return {"total": 0, "matched": 0, "no_match": 0, "match_rate_pct": 0.0}

    total = len(matched_rows)
    with_vendor = [r for r in matched_rows if r["vendor_id"] is not None]
    matched = len(with_vendor)
    no_match = total - matched

    logger.info(
        "%d surveys dans le scope (threshold=%.2f) — matches=%d sans_match=%d",
        total,
        threshold,
        matched,
        no_match,
    )

    for row in with_vendor[:10]:
        logger.info(
            "MATCH %s | '%s' -> '%s' (sim=%.2f)",
            row["survey_id"],
            str(row["supplier_raw"])[:40],
            str(row["vendor_name"])[:30],
            float(row["sim"]) if row["sim"] is not None else 0.0,
        )

    if not dry_run and with_vendor:
        sql_apply = f"""
            UPDATE public.market_surveys AS ms
            SET vendor_id = b.vendor_id
            FROM (
                WITH target_surveys AS (
                    SELECT s.id, s.supplier_raw
                    FROM public.market_surveys s
                    WHERE s.vendor_id IS NULL
                      AND s.supplier_raw IS NOT NULL
                      AND s.supplier_raw != ''
                    ORDER BY s.id
                    {lim_sql}
                ),
                best AS (
                    SELECT
                        ts.id AS survey_id,
                        vm.vendor_id
                    FROM target_surveys ts
                    INNER JOIN LATERAL (
                        SELECT v.id AS vendor_id
                        FROM public.vendors v
                        WHERE similarity(v.name_raw, ts.supplier_raw) >= %(threshold)s
                        ORDER BY similarity(v.name_raw, ts.supplier_raw) DESC
                        LIMIT 1
                    ) vm ON TRUE
                )
                SELECT survey_id, vendor_id FROM best
            ) AS b
            WHERE ms.id = b.survey_id AND ms.vendor_id IS NULL
        """
        cur.execute(sql_apply, params)

    return {
        "total": total,
        "matched": matched,
        "no_match": no_match,
        "match_rate_pct": round(matched * 100 / max(total, 1), 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ETL vendor_id sur market_surveys via pg_trgm (V5 Wartime M15)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode simulation sans UPDATE (defaut)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer les UPDATE en base",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Seuil de similarite pg_trgm (defaut: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre de surveys traites (test partiel)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    threshold = args.threshold

    print(f"\n{BOLD}ETL VENDOR MATCH — market_surveys (V5 M15){RESET}")
    print(f"Mode : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Threshold pg_trgm : {threshold}")
    print()

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        return 1

    db_url = _get_db_url()
    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    # Probe initiale
    state = probe_state(cur)
    print(f"  Vendors disponibles        : {state['vendors_total']}")
    print(f"  Surveys avec vendor_id     : {state['surveys_with_vendor']}")
    print(f"  Surveys sans vendor_id     : {state['surveys_without_vendor']}")
    print(f"  Surveys matchables (nom OK): {state['surveys_matchable']}")
    print()

    if state["vendors_total"] == 0:
        print(
            f"{RED}[BLOQUANT]{RESET} Aucun vendor en base Railway (table public.vendors vide).\n"
            "  Actions requises :\n"
            "  1. Demarrer Docker Desktop et restaurer la DB locale\n"
            "  2. Verifier : SELECT COUNT(*) FROM public.vendors; (local)\n"
            "  3. Si vendors presents en local : sync vendors local -> Railway\n"
            "     (pattern similaire a sync_dict_local_to_railway.py)\n"
            "  4. Re-lancer ce script apres sync vendors\n"
            "  Note : vendors.name_raw est la colonne de fuzzy matching (pas vendors.name)",
            file=sys.stderr,
        )
        conn.close()
        return 2

    if state["surveys_matchable"] == 0:
        print(
            f"{YELLOW}[WARN]{RESET} Aucun survey avec supplier_raw non vide.\n"
            "  Verifier : SELECT supplier_raw, COUNT(*) FROM market_surveys GROUP BY 1 LIMIT 5;"
        )
        conn.close()
        return 0

    # Verifier pg_trgm
    if not _ensure_pg_trgm(cur):
        print(
            f"{RED}[ERR]{RESET} pg_trgm non disponible. Impossible de continuer.",
            file=sys.stderr,
        )
        conn.close()
        return 3

    # Matching
    result = resolve_vendor_batch(
        cur, threshold=threshold, limit=args.limit, dry_run=dry_run
    )

    if not dry_run:
        conn.commit()

    conn.close()

    # Rapport
    print(f"\n{BOLD}=== RAPPORT ETL VENDOR MATCH V5 ==={RESET}")
    print(f"  Mode                       : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"  Surveys traites            : {result['total']}")
    print(f"  Matches trouves            : {result['matched']}")
    print(f"  Sans match (threshold {threshold}): {result['no_match']}")
    print(f"  Taux de match              : {result['match_rate_pct']}%")

    # Gate V5
    gate_ok = result["matched"] > 0
    print(f"\n{BOLD}Gate V5{RESET} (matched > 0) :")
    if gate_ok:
        print(f"  {GREEN}[VERT]{RESET} {result['matched']} vendors matches.")
        if result["match_rate_pct"] < 20:
            print(
                f"  {YELLOW}[WARN]{RESET} Taux < 20% — analyser supplier_raw :\n"
                "    SELECT supplier_raw, COUNT(*) FROM public.market_surveys "
                "    WHERE vendor_id IS NULL GROUP BY supplier_raw ORDER BY 2 DESC LIMIT 20;"
                f"\n  Essayer --threshold 0.4 ou mapping manuel top-50."
            )
    else:
        print(
            f"  {RED}[ROUGE]{RESET} Aucun match.\n"
            f"  Actions :\n"
            f"  1. Verifier SELECT COUNT(*) FROM public.vendors;\n"
            f"  2. Verifier colonne supplier_raw dans public.market_surveys\n"
            f"  3. Essayer --threshold 0.4 ou 0.3\n"
            f"  4. Verifier pg_trgm : SELECT similarity('test', 'test');"
        )

    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
