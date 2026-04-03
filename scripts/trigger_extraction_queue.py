#!/usr/bin/env python3
"""
trigger_extraction_queue.py — V6 Activation Wartime M15.

Declenche le traitement des documents en statut 'pending' sur Railway
en soumettant chaque document au pipeline d'extraction.

Pre-requis (gate V2 et V3 verts) :
  - ANNOTATION_USE_PASS_ORCHESTRATOR=1 en prod
  - ARQ worker operationnel (smoke_arq_worker.py STATUS=OK)

Strategies :
  A. Via API HTTP POST (mode --api, defaut) :
     POST /api/documents/{id}/extract pour chaque document pending
  B. Via ARQ direct (mode --arq) :
     Enqueue un job 'process_document' par document dans la queue ARQ

Gate de sortie V6 :
  - coverage_extraction >= 80% (documents traites / total)
  - dms_event_index non vide
  - Au moins 1 candidate_rule generee

Usage :
  # Mode API (defaut)
  python scripts/with_railway_env.py python scripts/trigger_extraction_queue.py --dry-run
  python scripts/with_railway_env.py python scripts/trigger_extraction_queue.py --apply

  # Mode ARQ direct (si API indisponible)
  python scripts/with_railway_env.py python scripts/trigger_extraction_queue.py --apply --mode arq

  # Limiter a N documents
  python scripts/with_railway_env.py python scripts/trigger_extraction_queue.py --apply --limit 10

  # Intervalle entre requetes (secondes)
  python scripts/with_railway_env.py python scripts/trigger_extraction_queue.py --apply --interval 30
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
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


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", os.environ.get("RAILWAY_DATABASE_URL", ""))
    if not url:
        raise SystemExit(f"{RED}[ERR]{RESET} DATABASE_URL manquante.")
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def _get_api_url() -> str:
    url = os.environ.get("RAILWAY_URL", os.environ.get("API_BASE_URL", ""))
    if not url:
        # Construire depuis RAILWAY_DATABASE_URL hostname comme fallback
        db_url = os.environ.get("RAILWAY_DATABASE_URL", "")
        if "railway.app" in db_url:
            logger.warning(
                "RAILWAY_URL absent — utiliser --api-url pour specifier manuellement"
            )
    return url.rstrip("/")


def fetch_pending_documents(cur, limit: int | None) -> list[dict]:
    """Charge les documents en statut 'pending' depuis Railway."""
    query = """
        SELECT id, filename, extraction_status, uploaded_at
        FROM public.documents
        WHERE extraction_status = 'pending'
        ORDER BY uploaded_at ASC
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    return [dict(r) for r in cur.fetchall()]


def probe_extraction_state(cur) -> dict:
    """Mesure l'etat extraction avant et apres trigger."""
    cur.execute(
        "SELECT extraction_status, COUNT(*) as cnt "
        "FROM public.documents "
        "GROUP BY extraction_status ORDER BY cnt DESC"
    )
    status_dist = {r["extraction_status"]: r["cnt"] for r in cur.fetchall()}

    total = sum(status_dist.values())
    processed = sum(v for k, v in status_dist.items() if k not in ("pending", None))

    # Verifier event_index V2 (table dans public, pas dms_vivant)
    event_count = 0
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM public.dms_event_index")
        r = cur.fetchone()
        event_count = r["cnt"] if r else 0
    except Exception:
        event_count = -1  # Table absente

    # Verifier candidate_rules (table dans public)
    rules_count = 0
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM public.candidate_rules")
        r = cur.fetchone()
        rules_count = r["cnt"] if r else 0
    except Exception:
        rules_count = -1

    return {
        "status_distribution": status_dist,
        "total_documents": total,
        "processed_documents": processed,
        "coverage_pct": round(processed * 100 / max(total, 1), 1),
        "dms_event_index_count": event_count,
        "candidate_rules_count": rules_count,
    }


def trigger_via_api(
    doc: dict,
    api_url: str,
    dry_run: bool,
    interval_s: float,
) -> dict:
    """Declenche l'extraction d'un document via l'API HTTP."""
    doc_id = doc["id"]
    endpoint = f"{api_url}/api/documents/{doc_id}/extract"

    if dry_run:
        logger.info("[DRY-RUN] POST %s", endpoint)
        return {"doc_id": str(doc_id), "status": "dry_run", "endpoint": endpoint}

    try:
        import requests

        resp = requests.post(
            endpoint,
            timeout=60,
            headers={"Content-Type": "application/json"},
        )

        if resp.status_code in (200, 201, 202):
            logger.info("OK doc=%s status=%d", doc_id, resp.status_code)
            result = {
                "doc_id": str(doc_id),
                "status": "triggered",
                "http_code": resp.status_code,
            }
            try:
                result["response"] = resp.json()
            except Exception:
                pass
        else:
            logger.warning(
                "WARN doc=%s status=%d body=%s",
                doc_id,
                resp.status_code,
                resp.text[:200],
            )
            result = {
                "doc_id": str(doc_id),
                "status": "error",
                "http_code": resp.status_code,
            }

        time.sleep(interval_s)
        return result

    except Exception as exc:
        logger.error("ERR doc=%s : %s", doc_id, exc)
        return {"doc_id": str(doc_id), "status": "exception", "error": str(exc)}


async def trigger_via_arq(
    doc: dict,
    redis_url: str,
    dry_run: bool,
) -> dict:
    """Enqueue un job ARQ 'process_document' pour un document."""
    doc_id = doc["id"]

    if dry_run:
        logger.info("[DRY-RUN] ARQ enqueue process_document doc=%s", doc_id)
        return {"doc_id": str(doc_id), "status": "dry_run"}

    try:
        import arq
        import redis.asyncio as aioredis

        pool = arq.ArqRedis(pool_or_conn=aioredis.from_url(redis_url))
        await pool.enqueue_job("process_document", {"document_id": str(doc_id)})
        await pool.aclose()
        logger.info("ARQ enqueued doc=%s", doc_id)
        return {"doc_id": str(doc_id), "status": "enqueued"}
    except Exception as exc:
        logger.error("ARQ ERR doc=%s : %s", doc_id, exc)
        return {"doc_id": str(doc_id), "status": "exception", "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trigger extraction queue — 25 docs pending (V6 Wartime M15)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode simulation sans trigger (defaut)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Declencher reellement les extractions",
    )
    parser.add_argument(
        "--mode",
        choices=["api", "arq"],
        default="api",
        help="Mode de trigger : 'api' (HTTP POST) ou 'arq' (queue directe) (defaut: api)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="URL de base de l'API Railway (ex: https://dms-prod.railway.app)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre maximum de documents a traiter (defaut: 25)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Intervalle entre les requetes en secondes (defaut: 30)",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Afficher seulement l'etat extraction sans trigger",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    print(f"\n{BOLD}TRIGGER EXTRACTION QUEUE — V6 M15{RESET}")
    print(f"Mode trigger   : {args.mode.upper()}")
    print(f"Mode ecriture  : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Limite         : {args.limit} documents")
    print(f"Intervalle     : {args.interval}s entre chaque")
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
    print(f"  {BLUE}[PROBE]{RESET} Etat extraction Railway...")
    state = probe_extraction_state(cur)

    print("\n  Distribution documents :")
    for status, cnt in sorted(
        state["status_distribution"].items(), key=lambda x: -x[1]
    ):
        print(f"    {str(status):30}: {cnt}")
    print(f"\n  Total documents           : {state['total_documents']}")
    print(f"  Traites (non pending)     : {state['processed_documents']}")
    print(f"  Coverage extraction       : {state['coverage_pct']}%")

    if state["dms_event_index_count"] >= 0:
        print(
            f"  dms_event_index           : {state['dms_event_index_count']} evenements"
        )
    else:
        print(f"  dms_event_index           : {YELLOW}schema V2 non present{RESET}")

    if state["candidate_rules_count"] >= 0:
        print(f"  candidate_rules           : {state['candidate_rules_count']}")
    else:
        print(f"  candidate_rules           : {YELLOW}schema V2 non present{RESET}")

    if args.probe_only:
        conn.close()
        return 0

    # Charger documents pending
    pending = fetch_pending_documents(cur, args.limit)
    print(
        f"\n  {GREEN}[PENDING]{RESET} {len(pending)} document(s) en attente de traitement"
    )

    if not pending:
        print(
            f"  {YELLOW}[WARN]{RESET} Aucun document pending.\n"
            "  Verifier : SELECT extraction_status, COUNT(*) FROM documents GROUP BY 1;"
        )
        conn.close()

        # Rapport gate meme si rien a faire
        _print_gate(state)
        return 0

    conn.close()

    # Mode API
    if args.mode == "api":
        api_url = args.api_url or _get_api_url()
        if not api_url:
            print(
                f"{RED}[ERR]{RESET} RAILWAY_URL ou --api-url requis pour le mode api.\n"
                "  Definir : $env:RAILWAY_URL = 'https://your-app.railway.app'\n"
                "  Ou utiliser : --mode arq",
                file=sys.stderr,
            )
            return 2

        print(f"  API URL : {api_url}")
        results = []
        for doc in pending:
            res = trigger_via_api(doc, api_url, dry_run, args.interval)
            results.append(res)

        triggered = sum(1 for r in results if r["status"] in ("triggered", "dry_run"))
        errors = sum(1 for r in results if r["status"] in ("error", "exception"))
        print(f"\n  Triggers : {triggered} OK, {errors} erreurs")

    # Mode ARQ
    elif args.mode == "arq":
        redis_url = os.environ.get("REDIS_URL", "")
        if not redis_url:
            print(
                f"{RED}[ERR]{RESET} REDIS_URL manquante pour le mode arq.\n"
                "  Definir REDIS_URL dans .env.railway.local",
                file=sys.stderr,
            )
            return 3

        async def run_arq():
            tasks = [trigger_via_arq(doc, redis_url, dry_run) for doc in pending]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_arq())
        triggered = sum(1 for r in results if r["status"] in ("enqueued", "dry_run"))
        errors = sum(1 for r in results if r["status"] in ("exception",))
        print(f"\n  Jobs ARQ enqueues : {triggered}, erreurs : {errors}")

    # Probe post-trigger (attente 5s pour laisser le temps au pipeline)
    if not dry_run and pending:
        logger.info("Attente 5s puis re-probe...")
        time.sleep(5)
        conn2 = psycopg.connect(db_url, row_factory=dict_row)
        cur2 = conn2.cursor()
        state_post = probe_extraction_state(cur2)
        conn2.close()

        print(f"\n  Coverage post-trigger : {state_post['coverage_pct']}%")
        print(f"  dms_event_index : {state_post['dms_event_index_count']}")
        print(f"  candidate_rules : {state_post['candidate_rules_count']}")
        _print_gate(state_post)
    else:
        _print_gate(state)

    return 0 if not errors else 1


def _print_gate(state: dict) -> None:
    """Affiche le resultat des gates V6."""
    coverage = state["coverage_pct"]
    events = state["dms_event_index_count"]
    rules = state["candidate_rules_count"]

    print(f"\n{BOLD}Gates V6{RESET} :")

    # Gate coverage_extraction >= 80%
    gate1 = coverage >= 80
    color1 = GREEN if gate1 else YELLOW
    print(
        f"  {color1}[{'VERT' if gate1 else 'PARTIEL'}]{RESET} coverage_extraction = {coverage}% (seuil: 80%)"
    )

    # Gate event_index non vide
    gate2 = events > 0
    color2 = GREEN if gate2 else (RED if events == 0 else YELLOW)
    label2 = "VERT" if gate2 else ("ROUGE" if events == 0 else "N/A")
    print(
        f"  {color2}[{label2}]{RESET} dms_event_index = {events} evenements (>0 requis)"
    )

    # Gate candidate_rules >= 1
    gate3 = rules > 0
    color3 = GREEN if gate3 else (RED if rules == 0 else YELLOW)
    label3 = "VERT" if gate3 else ("ROUGE" if rules == 0 else "N/A")
    print(f"  {color3}[{label3}]{RESET} candidate_rules = {rules} (>=1 requis)")

    all_green = gate1 and gate2 and gate3
    if all_green:
        print(
            f"\n  {GREEN}{BOLD}M15 GATES V6 TOUS VERTS{RESET} — Passer au traitement 100 dossiers."
        )
    else:
        print(f"\n  {YELLOW}Gates V6 partiels.{RESET}")
        if not gate1:
            print("  -> Relancer trigger pour les documents restants")
        if not gate2:
            print("  -> Verifier migrations V2 (schema dms_vivant) et bridge triggers")
        if not gate3:
            print("  -> Verifier ARQ worker et job detect_patterns")


if __name__ == "__main__":
    raise SystemExit(main())
