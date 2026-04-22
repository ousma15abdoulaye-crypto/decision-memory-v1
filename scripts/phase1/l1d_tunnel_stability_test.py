#!/usr/bin/env python3
"""
DMS Phase 1 L1-D — Test stabilité tunnel Railway CLI (45 min continue)

Usage:
    python scripts/phase1/l1d_tunnel_stability_test.py \
        --duration 2700 \
        --interval 30 \
        --output decisions/phase1/L1_D_raw_measurements.csv

Prérequis:
    - Tunnel Railway CLI ouvert dans un terminal séparé
      (railway connect postgres)
    - psycopg[binary] installé (pip install psycopg[binary])
    - DATABASE_URL dans l'environnement OU connexion via tunnel local
      sur port attendu

Le script exécute `SELECT 1` à intervalles réguliers, logge latence
et erreurs dans un CSV. Affiche progression en stdout toutes les 5 min.
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]")
    sys.exit(1)


def run_test(duration_sec: int, interval_sec: int, output_path: Path) -> None:
    """
    Execute SELECT 1 every interval_sec for duration_sec.
    Log each attempt to CSV: timestamp, latency_ms, status, error_message.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL not set. Use: railway run python ... OR set env var.")
        sys.exit(1)

    start = time.monotonic()
    end_target = start + duration_sec
    attempt = 0
    success = 0
    failure = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "attempt", "latency_ms", "status", "error"])

        print(f"[L1-D] Starting tunnel stability test: duration={duration_sec}s, interval={interval_sec}s")
        print(f"[L1-D] Output: {output_path}")

        while time.monotonic() < end_target:
            attempt += 1
            ts = datetime.now(timezone.utc).isoformat()
            t0 = time.perf_counter()
            status = "OK"
            error = ""
            latency_ms = 0.0
            try:
                with psycopg.connect(dsn, connect_timeout=5) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                latency_ms = (time.perf_counter() - t0) * 1000
                success += 1
            except Exception as e:
                latency_ms = (time.perf_counter() - t0) * 1000
                status = "FAIL"
                error = str(e)[:200]
                failure += 1

            writer.writerow([ts, attempt, f"{latency_ms:.2f}", status, error])
            f.flush()

            if attempt % 10 == 0:
                elapsed_min = (time.monotonic() - start) / 60
                print(f"[L1-D] t={elapsed_min:.1f}min | attempts={attempt} | success={success} | fail={failure}")

            remaining = end_target - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(interval_sec, remaining))

    elapsed_total = time.monotonic() - start
    print(f"\n[L1-D] Test complete: {elapsed_total/60:.1f}min elapsed")
    print(f"[L1-D] Attempts: {attempt} | Success: {success} | Failure: {failure}")
    print(f"[L1-D] Success rate: {100*success/max(attempt,1):.1f}%")


def main():
    parser = argparse.ArgumentParser(description="DMS L1-D tunnel stability test")
    parser.add_argument("--duration", type=int, default=2700, help="Duration in seconds (default 2700 = 45min)")
    parser.add_argument("--interval", type=int, default=30, help="Interval between requests in seconds (default 30)")
    parser.add_argument("--output", type=Path, required=True, help="Output CSV path")
    args = parser.parse_args()

    run_test(args.duration, args.interval, args.output)


if __name__ == "__main__":
    main()
