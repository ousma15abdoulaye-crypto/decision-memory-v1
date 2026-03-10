#!/usr/bin/env python3
"""
CB-08 COLLISION_TRIAGE — M8
Usage : python scripts/triage_collisions_m8.py --report

Adaptation schéma réel : dict_collision_log utilise resolution
(unresolved/auto_merged/proposal_created), pas status.
"""

import argparse
import os
import sys

import psycopg
from psycopg.rows import dict_row

T1, T2 = 95, 85


def env() -> str:
    u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL absente")
    if "railway" in u.lower():
        raise SystemExit("CONTRACT-02")
    return u


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def probe(cur) -> dict:
    cur.execute("""
        SELECT table_schema FROM information_schema.tables
        WHERE table_name = 'dict_collision_log' LIMIT 1
    """)
    r = cur.fetchone()
    if not r:
        raise SystemExit("dict_collision_log absente")
    schema = r["table_schema"]
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'dict_collision_log'
          AND table_schema = %s
    """,
        (schema,),
    )
    cols = {r["column_name"] for r in cur.fetchall()}
    if "fuzzy_score" not in cols:
        return {"mode": "LIMITED", "reason": "fuzzy_score absente", "schema": schema}
    la = next((c for c in ["label_a", "raw_text_1"] if c in cols), None)
    lb = next((c for c in ["label_b", "raw_text_2"] if c in cols), None)
    return {"mode": "FULL" if la else "TIER_ONLY", "schema": schema, "la": la, "lb": lb}


def run(db_url: str) -> dict:
    conn = psycopg.connect(_normalize_db_url(db_url), row_factory=dict_row)
    cur = conn.cursor()
    info = probe(cur)
    print(f"Triage mode : {info['mode']}")
    if info["mode"] == "LIMITED":
        print(f"Raison : {info['reason']}")
        conn.close()
        return {"verdict": "LIMITED"}
    s = info["schema"]
    la = info.get("la")
    lb = info.get("lb")
    sel = f", {la} AS la, {lb} AS lb" if la else ""
    # Schéma réel : resolution='unresolved' (pas status='pending')
    cur.execute(f"""
        SELECT id, fuzzy_score * 100 AS score{sel}
        FROM {s}.dict_collision_log
        WHERE resolution = 'unresolved'
        ORDER BY fuzzy_score DESC
    """)
    rows = cur.fetchall()
    t1 = [r for r in rows if r["score"] >= T1]
    t2 = [r for r in rows if T2 <= r["score"] < T1]
    t3 = [r for r in rows if r["score"] < T2]
    print(f"Total unresolved : {len(rows)}")
    print(f"TIER-1 (>={T1})  : {len(t1)} batch-review")
    print(f"TIER-2 ({T2}-{T1-1}): {len(t2)} revue assistée")
    print(f"TIER-3 (<{T2})   : {len(t3)} revue experte")
    if la and t1:
        print("Top 10 TIER-1 :")
        for r in t1[:10]:
            print(
                f"  {r['score']:3} | "
                f"{str(r.get('la', ''))[:35]} <-> "
                f"{str(r.get('lb', ''))[:35]}"
            )
    conn.close()
    return {
        "mode": info["mode"],
        "total": len(rows),
        "t1": len(t1),
        "t2": len(t2),
        "t3": len(t3),
        "verdict": "PASS",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if not a.report:
        print("Usage : --report")
        sys.exit(1)
    try:
        from pathlib import Path

        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
    except ImportError:
        pass
    r = run(env())
    sys.exit(0 if r.get("verdict") == "PASS" else 1)
