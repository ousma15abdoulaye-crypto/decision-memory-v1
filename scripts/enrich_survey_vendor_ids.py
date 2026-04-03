#!/usr/bin/env python3
"""
enrich_survey_vendor_ids.py — V5 Activation Wartime M15.

ETL vendor_id : enrichit public.market_surveys (vendor_id IS NULL)
en appliquant la logique de fuzzy matching pg_trgm de resolvers.py
(seuil similitude = 60%) sur supplier_name_raw.

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
    Applique le matching pg_trgm en batch.

    Pour chaque survey avec vendor_id IS NULL et supplier_name_raw non vide,
    cherche le vendor le plus proche (similarity >= threshold).
    Si dry_run : mesure le taux de match potentiel sans UPDATE.
    Si apply : execute les UPDATE et commit.
    """
    # Charger tous les surveys matchables (par batch de 1000 pour limiter memoire)
    # Colonne reelle : supplier_raw (pas supplier_name_raw)
    batch_query = """
        SELECT id, supplier_raw
        FROM public.market_surveys
        WHERE vendor_id IS NULL
          AND supplier_raw IS NOT NULL
          AND supplier_raw != ''
        ORDER BY id
    """
    if limit:
        batch_query += f" LIMIT {int(limit)}"

    cur.execute(batch_query)
    surveys = cur.fetchall()

    if not surveys:
        return {"matched": 0, "no_match": 0, "total": 0}

    logger.info("%d surveys a traiter (threshold=%.2f)", len(surveys), threshold)

    matched = 0
    no_match = 0
    no_vendor_table = 0

    for i, row in enumerate(surveys, 1):
        survey_id = row["id"]
        raw_name = row["supplier_raw"]

        # Fuzzy match via pg_trgm — meme logique que resolvers.py
        # Colonne reelle : vendors.name_raw (pas vendors.name)
        try:
            cur.execute(
                """
                SELECT id, name_raw, similarity(name_raw, %(name)s) AS sim
                FROM public.vendors
                WHERE similarity(name_raw, %(name)s) >= %(threshold)s
                ORDER BY sim DESC
                LIMIT 1
                """,
                {"name": raw_name, "threshold": threshold},
            )
            vendor_row = cur.fetchone()
        except Exception as exc:
            logger.error(
                "Erreur similarity sur survey %s (name=%r): %s",
                survey_id,
                raw_name[:40],
                exc,
            )
            no_vendor_table += 1
            if no_vendor_table > 3:
                logger.error(
                    "Table vendors inaccessible ou pg_trgm non disponible — arret."
                )
                break
            continue

        if vendor_row:
            vendor_id = vendor_row["id"]
            sim = vendor_row["sim"]
            vendor_name = vendor_row["name_raw"]

            if not dry_run:
                cur.execute(
                    "UPDATE public.market_surveys "
                    "SET vendor_id = %(vendor_id)s "
                    "WHERE id = %(survey_id)s AND vendor_id IS NULL",
                    {"vendor_id": str(vendor_id), "survey_id": str(survey_id)},
                )
            matched += 1

            if i <= 10 or matched % 1000 == 0:
                logger.info(
                    "MATCH %s | '%s' -> '%s' (sim=%.2f)",
                    survey_id,
                    raw_name[:40],
                    str(vendor_name)[:30],
                    sim,
                )
        else:
            no_match += 1

        if i % 500 == 0:
            pct = round(i * 100 / len(surveys), 1)
            logger.info(
                "[%d/%d (%s%%)] matched=%d no_match=%d",
                i,
                len(surveys),
                pct,
                matched,
                no_match,
            )

    return {
        "total": len(surveys),
        "matched": matched,
        "no_match": no_match,
        "match_rate_pct": round(matched * 100 / max(len(surveys), 1), 1),
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
                f"  {YELLOW}[WARN]{RESET} Taux < 20% — analyser supplier_name_raw :\n"
                "    SELECT supplier_name_raw, COUNT(*) FROM market_surveys "
                "    WHERE vendor_id IS NULL GROUP BY supplier_name_raw ORDER BY 2 DESC LIMIT 20;"
                f"\n  Essayer --threshold 0.4 ou mapping manuel top-50."
            )
    else:
        print(
            f"  {RED}[ROUGE]{RESET} Aucun match.\n"
            f"  Actions :\n"
            f"  1. Verifier SELECT COUNT(*) FROM public.vendors;\n"
            f"  2. Verifier colonne supplier_name_raw dans market_surveys\n"
            f"  3. Essayer --threshold 0.4 ou 0.3\n"
            f"  4. Verifier pg_trgm : SELECT similarity('test', 'test');"
        )

    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
