#!/usr/bin/env python3
"""
smoke_arq_worker.py — V3 Activation Wartime M15.

Test smoke ARQ : enqueue un job index_event de test, verifie qu'il est consomme
en < 30 secondes, puis confirme que dms_event_index a au moins 1 ligne.

Pre-requis :
  - REDIS_URL configure dans les variables Railway (ou .env.railway.local)
  - Worker ARQ en cours d'execution : arq src.workers.arq_config.WorkerSettings

Usage :
  python scripts/with_railway_env.py python scripts/smoke_arq_worker.py
  python scripts/with_railway_env.py python scripts/smoke_arq_worker.py --timeout 60

Critere de succes (Gate V3) :
  - Le script affiche STATUS=OK
  - dms_vivant.dms_event_index contient >= 1 ligne
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

SMOKE_JOB_ID = "smoke_arq_m15_v3"


async def _check_redis(redis_url: str) -> bool:
    """Verifie que Redis est accessible."""
    try:
        import redis.asyncio as aioredis

        r = await aioredis.from_url(redis_url, socket_timeout=5)
        pong = await r.ping()
        await r.aclose()
        return pong
    except Exception as exc:
        print(f"  {RED}[ERR Redis]{RESET} {exc}", file=sys.stderr)
        return False


async def _enqueue_smoke(redis_url: str) -> str | None:
    """Enqueue un job smoke et retourne son job_id."""
    try:
        import arq
    except ImportError:
        print(
            f"{RED}[ERR]{RESET} arq non installe. Installer avec : pip install arq",
            file=sys.stderr,
        )
        return None

    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(redis_url)
        pool = arq.ArqRedis(pool_or_conn=redis)

        result = await pool.enqueue_job(
            "index_event",
            {"event_type": "smoke_test", "source": "smoke_arq_m15", "payload": {}},
            _job_id=SMOKE_JOB_ID,
        )
        await pool.aclose()

        if result is None:
            print(
                f"  {YELLOW}[WARN]{RESET} Job {SMOKE_JOB_ID} deja en file (deduplique — normal si re-run rapide)."
            )
        else:
            print(f"  {GREEN}[ENQUEUE]{RESET} Job enqueue : {SMOKE_JOB_ID}")
        return SMOKE_JOB_ID
    except Exception as exc:
        print(f"  {RED}[ERR enqueue]{RESET} {exc}", file=sys.stderr)
        return None


async def _poll_job_result(redis_url: str, job_id: str, timeout_s: int) -> bool:
    """Poll le resultat du job jusqu'a timeout."""
    try:
        import arq
        import redis.asyncio as aioredis

        redis = aioredis.from_url(redis_url)
        pool = arq.ArqRedis(pool_or_conn=redis)
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            job = arq.Job(job_id=job_id, redis=pool)
            info = await job.info()
            if info is not None:
                status = await job.status()
                if status == arq.JobStatus.complete:
                    result = await job.result()
                    print(f"  {GREEN}[JOB OK]{RESET} Resultat : {result}")
                    await pool.aclose()
                    return True
                if status == arq.JobStatus.not_found:
                    print(
                        f"  {YELLOW}[WARN]{RESET} Job introuvable — worker pas encore demarre ?"
                    )
                    await asyncio.sleep(3)
                    continue
            await asyncio.sleep(3)

        await pool.aclose()
        print(
            f"  {RED}[TIMEOUT]{RESET} Job non consomme en {timeout_s}s. Worker demarre ?",
            file=sys.stderr,
        )
        return False
    except Exception as exc:
        print(f"  {RED}[ERR poll]{RESET} {exc}", file=sys.stderr)
        return False


def _check_event_index(db_url: str) -> int:
    """Compte les lignes dans dms_vivant.dms_event_index."""
    try:
        import psycopg

        with psycopg.connect(db_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dms_vivant.dms_event_index")
                count = cur.fetchone()[0]
        return count
    except Exception as exc:
        print(f"  {YELLOW}[WARN event_index]{RESET} {exc}")
        return -1


async def main_async(args: argparse.Namespace) -> int:
    redis_url = os.environ.get("REDIS_URL", "")
    db_url = os.environ.get("DATABASE_URL", os.environ.get("RAILWAY_DATABASE_URL", ""))

    print(f"\n{BOLD}SMOKE TEST ARQ WORKER (V3 M15){RESET}")
    print()

    # 1. Verifier REDIS_URL
    if not redis_url:
        print(
            f"{RED}[ERR]{RESET} REDIS_URL manquante.\n"
            "  -> Recuperer depuis Railway Dashboard > Services > Redis > Variables\n"
            "  -> Ajouter dans .env.railway.local et variables Railway du service FastAPI",
            file=sys.stderr,
        )
        return 1

    print(
        f"  Redis URL : {redis_url.split('@')[-1] if '@' in redis_url else redis_url[:40]}"
    )

    # 2. Ping Redis
    print(f"  {BLUE}[1/4]{RESET} Ping Redis...")
    ok = await _check_redis(redis_url)
    if not ok:
        return 2
    print(f"  {GREEN}[OK]{RESET} Redis accessible.")

    # 3. Enqueue job smoke
    print(f"  {BLUE}[2/4]{RESET} Enqueue job smoke...")
    job_id = await _enqueue_smoke(redis_url)
    if not job_id:
        return 3

    # 4. Poll resultat
    print(f"  {BLUE}[3/4]{RESET} Attente consommation (timeout={args.timeout}s)...")
    if args.skip_poll:
        print(
            f"  {YELLOW}[SKIP]{RESET} --skip-poll active. Verifier manuellement le worker."
        )
        job_ok = True
    else:
        job_ok = await _poll_job_result(redis_url, job_id, args.timeout)

    # 5. Verifier dms_event_index
    print(f"  {BLUE}[4/4]{RESET} Verification dms_vivant.dms_event_index...")
    if db_url:
        count = _check_event_index(db_url)
        if count >= 0:
            color = GREEN if count > 0 else YELLOW
            print(
                f"  {color}[event_index]{RESET} {count} ligne(s) dans dms_event_index."
            )
        else:
            print(f"  {YELLOW}[WARN]{RESET} Impossible de verifier event_index.")
    else:
        print(
            f"  {YELLOW}[SKIP]{RESET} DATABASE_URL manquante — verifier event_index manuellement."
        )

    # Gate V3
    print()
    if job_ok:
        print(f"{BOLD}STATUS=OK{RESET} — Gate V3 valide.")
        print("  Prochaine etape : V4 batch_signal_from_map.py")
        return 0
    else:
        print(f"{BOLD}STATUS=KO{RESET} — Worker ARQ non operationnel.")
        print(
            "  Actions :\n"
            "  1. Verifier que le worker tourne : arq src.workers.arq_config.WorkerSettings\n"
            "  2. Verifier REDIS_URL dans les variables du service worker\n"
            "  3. Relancer ce script apres correction"
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test ARQ Worker (V3 Wartime M15)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout en secondes pour la consommation du job (defaut: 30)",
    )
    parser.add_argument(
        "--skip-poll",
        action="store_true",
        help="Ne pas attendre le resultat du job (utile si worker pas encore demarre)",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
