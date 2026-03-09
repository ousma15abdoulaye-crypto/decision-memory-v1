#!/usr/bin/env python3
"""
validate_mrd_state.py
─────────────────────
Outil CTO — exécuter avant chaque session de travail.
Donne une vue complète de l'état du système en < 15 secondes.
Zéro écriture. Lecture seule.

Usage :
  python scripts/validate_mrd_state.py
  python scripts/validate_mrd_state.py --railway   # probe Railway aussi
"""

import os
import sys
import subprocess
from pathlib import Path

# Charger .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(Path.cwd() / ".env.local")
except ImportError:
    pass

# ── Couleurs terminal ─────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"{GREEN}✓{RESET} {msg}")
def warn(msg): print(f"{YELLOW}⚠{RESET} {msg}")
def err(msg):  print(f"{RED}✗{RESET} {msg}")
def info(msg): print(f"{BLUE}→{RESET} {msg}")
def head(msg): print(f"\n{BOLD}── {msg} ──{RESET}")

STOPS_DETECTED = []

def stop(code: str, msg: str):
    err(f"STOP-{code} : {msg}")
    STOPS_DETECTED.append(f"STOP-{code}: {msg}")

# ── S0 : Variables d'environnement ───────────────────────────────────────
def check_env() -> tuple[str, str, bool]:
    head("ENVIRONNEMENT")
    db_url = os.environ.get("DATABASE_URL", "")
    env    = os.environ.get("ENV", "unknown")
    redis  = os.environ.get("REDIS_URL", "")

    if not db_url:
        stop("ENV", "DATABASE_URL absente")
    else:
        is_railway = "railway" in db_url.lower()
        db_type = "RAILWAY" if is_railway else "LOCAL"
        if is_railway:
            warn(f"DATABASE_URL → {db_type} (prod)")
        else:
            ok(f"DATABASE_URL → {db_type}")

    info(f"ENV={env}")
    ok(f"REDIS_URL={'DÉFINIE' if redis else 'ABSENTE'}")

    return db_url.replace("postgresql+psycopg://", "postgresql://"), env, "railway" in db_url.lower()

# ── S1 : Git ──────────────────────────────────────────────────────────────
def check_git() -> str:
    head("GIT")
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=Path.cwd()
    ).stdout.strip()
    info(f"Branch : {branch}")

    log = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        capture_output=True, text=True, cwd=Path.cwd()
    ).stdout.strip()
    info(f"Log :\n  {log.replace(chr(10), chr(10)+'  ')}")

    stash = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True, text=True, cwd=Path.cwd()
    ).stdout.strip()
    if stash:
        warn(f"Stash non vide :\n  {stash}")
    else:
        ok("Stash : vide")

    dirty = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True, cwd=Path.cwd()
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
        capture_output=True, text=True, cwd=Path.cwd()
    )
    current_result = subprocess.run(
        ["alembic", "current"],
        capture_output=True, text=True, cwd=Path.cwd()
    )

    head_lines = [
        l.strip().split()[0]
        for l in heads_result.stdout.strip().splitlines()
        if l.strip() and not l.startswith("INFO")
    ]
    current_line = current_result.stdout.strip()

    if len(head_lines) == 1:
        ok(f"Heads (repo) : {head_lines[0]}")
    elif len(head_lines) == 0:
        stop("ALC1", "alembic heads = 0 lignes")
    else:
        stop("ALC2", f"alembic heads = {len(head_lines)} lignes : {head_lines}")

    info(f"Current (repo) : {current_line}")
    return head_lines, current_line

# ── S3 : Database ─────────────────────────────────────────────────────────
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

    try:
        conn = psycopg.connect(db_url, connect_timeout=5)
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
                 """SELECT COUNT(*) FROM couche_b.procurement_dict_items
                    WHERE human_validated=TRUE AND active=TRUE"""),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:30} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

            # Triggers — Framework Partie 6 : trg_dict_compute_hash, trg_dict_write_audit
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
            }
            found   = set(result["triggers"])
            missing = expected - found
            if missing:
                stop("TRG", f"Triggers manquants : {missing}")
            else:
                ok(f"Triggers critiques (hash chain) : tous présents")

            # CASCADE
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
                    ok(f"{label:30} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR — {e}")

        conn.close()

    except Exception as e:
        stop("DB", f"DB inaccessible : {e}")
        err("Vérifier que PostgreSQL local est démarré")
        err("Vérifier DATABASE_URL dans .env")

    return result

# ── S4 : MRD State ────────────────────────────────────────────────────────
def check_mrd_state() -> dict:
    head("MRD STATE")
    state_path = Path("docs/freeze/MRD_CURRENT_STATE.md")
    if not state_path.exists():
        stop("MRD", "MRD_CURRENT_STATE.md absent")
        return {}

    content = state_path.read_text()
    info(f"MRD_CURRENT_STATE.md :\n{'='*40}")
    print(content.strip())
    print("="*40)

    for line in content.splitlines():
        if line.startswith("next_milestone"):
            parts = line.split(":")
            if len(parts) >= 2:
                ok(f"Next milestone : {parts[1].strip()}")
    return {"content": content}

# ── S5 : Alignement repo vs DB ──────────────────────────────────────────
def check_alignment(head_lines: list, db_result: dict):
    head("ALIGNEMENT REPO ↔ DB")
    if not head_lines or not db_result.get("alembic_version"):
        warn("Alignement non vérifiable — données manquantes")
        return
    repo_head = head_lines[0] if head_lines else None
    db_heads  = db_result.get("alembic_version", [])
    if repo_head and db_heads and repo_head in db_heads:
        ok(f"ALIGNÉ — repo={repo_head} db={db_heads}")
    elif repo_head and db_heads:
        stop("ALN", f"DÉSALIGNÉ — repo={repo_head} db={db_heads}")
    else:
        warn("Alignement partiel — vérifier manuellement")

# ── Railway optionnel ─────────────────────────────────────────────────────
def check_railway():
    head("RAILWAY (optionnel)")
    cli = subprocess.run(
        ["railway", "--version"],
        capture_output=True, text=True
    )
    if cli.returncode != 0:
        warn("Railway CLI absent — skip probe Railway")
        warn("Installer : npm install -g @railway/cli")
        return
    ok(f"Railway CLI : {cli.stdout.strip()}")

    result = subprocess.run(
        ["railway", "run", "python", "-c",
         "import os, psycopg; db=os.environ.get('DATABASE_URL',''); print('Railway DB:', bool(db)); conn=psycopg.connect(db, connect_timeout=5); cur=conn.cursor(); cur.execute('SELECT version_num FROM alembic_version'); print('alembic:', cur.fetchall()); conn.close()"],
        capture_output=True, text=True, timeout=30, cwd=Path.cwd()
    )
    if result.returncode == 0:
        ok(f"Railway probe :\n{result.stdout.strip()}")
    else:
        warn(f"Railway probe ÉCHOUÉ :\n{result.stderr.strip()}")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}  DMS — VALIDATE MRD STATE{RESET}")
    print(f"{BOLD}{'='*50}{RESET}")

    db_url, env, is_railway = check_env()
    check_git()
    head_lines, current     = check_alembic()
    db_result               = check_db(db_url)
    mrd_state               = check_mrd_state()
    check_alignment(head_lines, db_result)

    if "--railway" in sys.argv:
        check_railway()

    # ── Verdict final ────────────────────────────────────────────────────
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
