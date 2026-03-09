#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_mrd_state.py
---------------------
Outil CTO -- executer avant chaque session de travail.
Donne une vue complete de l'etat du systeme en < 15 secondes.
Zero ecriture. Lecture seule.

Usage :
  python scripts/validate_mrd_state.py
  python scripts/validate_mrd_state.py --railway   # probe Railway aussi
"""

import io
import os
import sys
import subprocess
from pathlib import Path

# Force UTF-8 sur stdout (Windows CP1252 sinon)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"{GREEN}[OK]  {RESET} {msg}")
def warn(msg): print(f"{YELLOW}[WARN]{RESET} {msg}")
def err(msg):  print(f"{RED}[ERR] {RESET} {msg}")
def info(msg): print(f"{BLUE}[->]  {RESET} {msg}")
def head(msg): print(f"\n{BOLD}-- {msg} --{RESET}")

STOPS_DETECTED = []


def stop(code: str, msg: str):
    err(f"STOP-{code} : {msg}")
    STOPS_DETECTED.append(f"STOP-{code}: {msg}")


def _load_dotenv():
    """Charge .env dans os.environ si présent (sans dépendance python-dotenv)."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _normalize_db_url(url: str) -> str:
    """Convertit postgresql+psycopg:// → postgresql:// pour psycopg3 direct."""
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


# ── S0 : Variables d'environnement ───────────────────────────────────────
def check_env() -> tuple[str, str, str, bool]:
    head("ENVIRONNEMENT")
    _load_dotenv()

    db_url          = os.environ.get("DATABASE_URL", "")
    railway_db_url  = os.environ.get("RAILWAY_DATABASE_URL", "")
    env             = os.environ.get("ENV", "unknown")
    redis           = os.environ.get("REDIS_URL", "")

    if not db_url:
        stop("ENV", "DATABASE_URL absente (ni shell ni .env)")
    else:
        is_railway = "railway" in db_url.lower() or "rlwy" in db_url.lower()
        db_type = "RAILWAY" if is_railway else "LOCAL"
        if is_railway:
            warn(f"DATABASE_URL → {db_type} (prod — attention)")
        else:
            ok(f"DATABASE_URL → {db_type}")

    if railway_db_url:
        ok("RAILWAY_DATABASE_URL → DÉFINIE")
    else:
        warn("RAILWAY_DATABASE_URL → ABSENTE")

    info(f"ENV={env}")
    ok(f"REDIS_URL={'DÉFINIE' if redis else 'ABSENTE'}")

    is_railway_local = bool(db_url) and (
        "railway" in db_url.lower() or "rlwy" in db_url.lower()
    )
    return db_url, railway_db_url, env, is_railway_local


# ── S1 : Git ──────────────────────────────────────────────────────────────
def check_git() -> str:
    head("GIT")
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True
    ).stdout.strip()
    info(f"Branch : {branch}")

    log = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        capture_output=True, text=True
    ).stdout.strip()
    info(f"Log :\n  {log.replace(chr(10), chr(10)+'  ')}")

    stash = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True, text=True
    ).stdout.strip()
    if stash:
        count = len(stash.splitlines())
        warn(f"Stash non vide : {count} entrée(s)")
    else:
        ok("Stash : vide")

    dirty = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        warn(f"Fichiers modifiés non commités :\n  {dirty}")
    else:
        ok("Working tree : propre")

    return branch


# ── S2 : Alembic ──────────────────────────────────────────────────────────
def check_alembic() -> tuple[list, str]:
    head("ALEMBIC")
    heads_result = subprocess.run(
        ["alembic", "heads"],
        capture_output=True, text=True
    )
    current_result = subprocess.run(
        ["alembic", "current"],
        capture_output=True, text=True
    )

    head_lines = [
        line.strip().split()[0]
        for line in heads_result.stdout.strip().splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    current_line = next(
        (line.strip() for line in current_result.stdout.splitlines()
         if line.strip() and not line.startswith("INFO")),
        "INACCESSIBLE"
    )

    if len(head_lines) == 1:
        ok(f"Heads (repo) : {head_lines[0]}")
    elif len(head_lines) == 0:
        stop("ALC1", "alembic heads = 0 lignes")
    else:
        stop("ALC2", f"alembic heads = {len(head_lines)} têtes : {head_lines}")

    info(f"Current (DB locale) : {current_line}")
    return head_lines, current_line


# ── S3 : Database locale ──────────────────────────────────────────────────
def check_db(db_url: str) -> dict:
    head("DATABASE LOCALE")
    result = {
        "accessible": False,
        "pg_version": None,
        "alembic_version": None,
        "schemas": [],
        "counts": {},
        "triggers": [],
        "cascades": [],
    }

    if not db_url:
        err("DATABASE_URL absente — skip probe DB")
        return result

    try:
        import psycopg
    except ImportError:
        err("psycopg non installé — pip install psycopg[binary]")
        return result

    conn_url = _normalize_db_url(db_url)

    try:
        conn = psycopg.connect(conn_url, connect_timeout=5)
        cur  = conn.cursor()
        result["accessible"] = True
        ok("Connexion DB : OK")

        cur.execute("SELECT version()")
        result["pg_version"] = cur.fetchone()[0].split(",")[0]
        ok(f"PostgreSQL : {result['pg_version']}")

        try:
            cur.execute("SELECT version_num FROM alembic_version")
            rows = cur.fetchall()
            result["alembic_version"] = [r[0] for r in rows]
            ok(f"alembic_version DB : {result['alembic_version']}")
        except Exception as e:
            warn(f"alembic_version : ERREUR — {e}")

        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name NOT IN (
                'information_schema','pg_catalog','pg_toast','pg_temp_1'
            )
            ORDER BY schema_name
        """)
        result["schemas"] = [r[0] for r in cur.fetchall()]
        ok(f"Schémas : {result['schemas']}")

        if "couche_b" in result["schemas"]:
            for label, q in [
                ("dict_items_actifs",
                 "SELECT COUNT(*) FROM couche_b.procurement_dict_items WHERE active=TRUE"),
                ("dict_items_total",
                 "SELECT COUNT(*) FROM couche_b.procurement_dict_items"),
                ("aliases",
                 "SELECT COUNT(*) FROM couche_b.procurement_dict_aliases"),
                ("seeds_human_validated",
                 ("SELECT COUNT(*) FROM couche_b.procurement_dict_items "
                  "WHERE human_validated=TRUE AND active=TRUE")),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:35} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

            # Triggers critiques
            cur.execute("""
                SELECT trigger_name FROM information_schema.triggers
                WHERE trigger_schema = 'couche_b'
                  AND event_object_table = 'procurement_dict_items'
                ORDER BY trigger_name
            """)
            result["triggers"] = [r[0] for r in cur.fetchall()]
            expected = {
                "trg_dict_compute_hash",
                "trg_dict_write_audit",
                "trg_protect_item_identity",
                "trg_protect_item_with_aliases",
            }
            found   = set(result["triggers"])
            missing = expected - found
            if missing:
                stop("TRG", f"Triggers manquants : {missing}")
            else:
                ok("Triggers critiques : tous présents")

            # CASCADE FK
            cur.execute("""
                SELECT tc.table_name, kcu.column_name, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema    = kcu.table_schema
                JOIN information_schema.referential_constraints rc
                  ON rc.constraint_name   = tc.constraint_name
                 AND rc.constraint_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema    = 'couche_b'
                  AND rc.delete_rule     = 'CASCADE'
            """)
            result["cascades"] = cur.fetchall()
            if result["cascades"]:
                stop("CAS", f"CASCADE FK détectée : {result['cascades']}")
            else:
                ok("CASCADE FK : aucune ✓")

        if "public" in result["schemas"]:
            for label, q in [
                ("vendors",    "SELECT COUNT(*) FROM public.vendors"),
                ("mercurials", "SELECT COUNT(*) FROM public.mercurials"),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:35} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

        conn.close()

    except Exception as e:
        stop("DB", f"DB inaccessible : {e}")
        err("Vérifier que PostgreSQL local est démarré")
        err("Vérifier DATABASE_URL dans .env")

    return result


# ── S4 : Database Railway (optionnel) ─────────────────────────────────────
def check_railway_db(railway_db_url: str) -> dict:
    head("DATABASE RAILWAY")
    result = {"accessible": False, "alembic_version": None, "counts": {}}

    if not railway_db_url:
        warn("RAILWAY_DATABASE_URL absente — skip probe Railway")
        return result

    try:
        import psycopg
        conn = psycopg.connect(railway_db_url, connect_timeout=15)
        cur  = conn.cursor()
        result["accessible"] = True
        ok("Railway DB : ACCESSIBLE")

        cur.execute("SELECT version()")
        pg_ver = cur.fetchone()[0].split(",")[0]
        ok(f"Railway PostgreSQL : {pg_ver}")

        try:
            cur.execute("SELECT version_num FROM alembic_version")
            rows = cur.fetchall()
            result["alembic_version"] = [r[0] for r in rows]
            ok(f"Railway alembic_version : {result['alembic_version']}")
        except Exception as e:
            warn(f"Railway alembic_version : ERREUR — {e}")

        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema','pg_catalog','pg_toast')
            ORDER BY schema_name
        """)
        schemas = [r[0] for r in cur.fetchall()]
        ok(f"Railway schémas : {schemas}")

        if "couche_b" in schemas:
            for label, q in [
                ("railway_dict_items_actifs",
                 "SELECT COUNT(*) FROM couche_b.procurement_dict_items WHERE active=TRUE"),
                ("railway_aliases",
                 "SELECT COUNT(*) FROM couche_b.procurement_dict_aliases"),
                ("railway_seeds_human_validated",
                 ("SELECT COUNT(*) FROM couche_b.procurement_dict_items "
                  "WHERE human_validated=TRUE AND active=TRUE")),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:40} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

        if "public" in schemas:
            for label, q in [
                ("railway_vendors",    "SELECT COUNT(*) FROM public.vendors"),
                ("railway_mercurials", "SELECT COUNT(*) FROM public.mercurials"),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:40} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

        conn.close()

    except Exception as e:
        warn(f"Railway DB INACCESSIBLE : {e}")

    return result


# ── S5 : MRD State ────────────────────────────────────────────────────────
def check_mrd_state() -> dict:
    head("MRD STATE")
    state_path = Path("docs/freeze/MRD_CURRENT_STATE.md")
    if not state_path.exists():
        stop("MRD", "MRD_CURRENT_STATE.md absent")
        return {}

    content = state_path.read_text(encoding="utf-8")
    info(f"MRD_CURRENT_STATE.md :\n{'='*40}")
    print(content.strip())
    print("=" * 40)

    for line in content.splitlines():
        if line.startswith("next_milestone"):
            parts = line.split(":")
            if len(parts) >= 2:
                ok(f"Next milestone : {parts[1].strip()}")
    return {"content": content}


# ── S6 : Alignement repo vs DB ────────────────────────────────────────────
def check_alignment(head_lines: list, db_result: dict, railway_result: dict):
    head("ALIGNEMENT REPO ↔ LOCAL ↔ RAILWAY")
    repo_head  = head_lines[0] if head_lines else None
    local_ver  = db_result.get("alembic_version", [])
    rail_ver   = railway_result.get("alembic_version", [])

    if repo_head and local_ver:
        if repo_head in local_ver:
            ok(f"REPO ↔ LOCAL  : ALIGNÉ   ({repo_head})")
        else:
            stop("ALN-LOCAL", f"DÉSALIGNÉ repo={repo_head} local={local_ver}")
    else:
        warn("REPO ↔ LOCAL  : non vérifiable")

    if repo_head and rail_ver:
        if repo_head in rail_ver:
            ok(f"REPO ↔ RAILWAY: ALIGNÉ   ({repo_head})")
        else:
            stop("ALN-RAIL", f"DÉSALIGNÉ repo={repo_head} railway={rail_ver}")
    elif not rail_ver:
        warn("REPO ↔ RAILWAY: non vérifiable (Railway inaccessible ou RAILWAY_DATABASE_URL absente)")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  DMS — VALIDATE MRD STATE{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")

    db_url, railway_db_url, env, is_railway = check_env()
    check_git()
    head_lines, current = check_alembic()
    db_result           = check_db(db_url)
    mrd_state           = check_mrd_state()

    railway_result: dict = {}
    if "--railway" in sys.argv or railway_db_url:
        railway_result = check_railway_db(railway_db_url)

    check_alignment(head_lines, db_result, railway_result)

    head("VERDICT")
    if STOPS_DETECTED:
        print(f"\n{RED}{BOLD}STOPS DÉTECTÉS — NE PAS COMMENCER DE MILESTONE{RESET}")
        for s in STOPS_DETECTED:
            err(s)
        print(f"\n{RED}Poster ce résultat au CTO avant toute action.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}{BOLD}SYSTÈME OK — PRÊT POUR LECTURE DU MANDAT{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
