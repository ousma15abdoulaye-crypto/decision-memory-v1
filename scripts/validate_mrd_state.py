#!/usr/bin/env python3
"""
validate_mrd_state.py  v2
-------------------------
Outil CTO -- executer avant chaque session de travail.
Donne une vue complete de l'etat du systeme en < 15 secondes.
Zero ecriture. Lecture seule.

Usage :
  python scripts/validate_mrd_state.py
  python scripts/validate_mrd_state.py --railway   # probe Railway aussi

v2 : ajout check_system_contract() -- CONTRACT-01/02/04/05
     appelé en PREMIER dans main(), avant tout autre check.
"""

import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path

FREEZE_HASHES_PATH = Path("docs/freeze/FREEZE_HASHES.md")
DOCS_FREEZE_DIR = Path("docs/freeze")

# Force UTF-8 sur stdout (Windows CP1252 sinon)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"{GREEN}[OK]  {RESET} {msg}")


def warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def err(msg):
    print(f"{RED}[ERR] {RESET} {msg}")


def info(msg):
    print(f"{BLUE}[->]  {RESET} {msg}")


def head(msg):
    print(f"\n{BOLD}-- {msg} --{RESET}")


STOPS_DETECTED = []


def stop(code: str, msg: str):
    err(f"STOP-{code} : {msg}")
    STOPS_DETECTED.append(f"STOP-{code}: {msg}")


def _load_dotenv():
    """Charge .env dans os.environ si present (sans dependance python-dotenv)."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def check_freeze_hashes() -> bool:
    """
    Vérifier chaque SHA256 listé dans FREEZE_HASHES.md.
    Format attendu : NOM_DOCUMENT.md = <sha256_64_chars>
    Ligne vide ou # = ignorée.
    Tout écart = exit(1). Zéro skip silencieux.
    """
    if not FREEZE_HASHES_PATH.exists():
        print(f"ERREUR : {FREEZE_HASHES_PATH} absent")
        return False

    ok = True
    checked = 0
    errors = []

    for raw_line in FREEZE_HASHES_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f"FORMAT INVALIDE : {line!r}")
            ok = False
            continue

        doc_name, hash_expected = (p.strip() for p in line.split("=", 1))
        hash_expected = hash_expected.lower()

        if len(hash_expected) != 64:
            errors.append(f"HASH LONGUEUR INVALIDE : {doc_name}")
            ok = False
            continue

        doc_path = DOCS_FREEZE_DIR / doc_name
        if not doc_path.exists():
            errors.append(f"FICHIER ABSENT : {doc_path}")
            ok = False
            continue

        sha256 = hashlib.sha256(doc_path.read_bytes()).hexdigest()

        if sha256 != hash_expected:
            errors.append(
                f"HASH MISMATCH : {doc_name}\n"
                f"  attendu  : {hash_expected}\n"
                f"  calculé  : {sha256}"
            )
            ok = False
        else:
            print(f"  HASH OK  : {doc_name}")
            checked += 1

    if errors:
        print(f"\nERREURS FREEZE ({len(errors)}) :")
        for e in errors:
            print(f"  {e}")

    print(f"\nFREEZE HASHES : {checked} OK / " f"{checked + len(errors)} total")
    return ok


def _normalize_db_url(url: str) -> str:
    """Convertit postgresql+psycopg:// en postgresql:// pour psycopg3 direct."""
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


# ── C0 : Verification SYSTEM_CONTRACT present ────────────────────────────
def check_system_contract() -> bool:
    head("SYSTEM CONTRACT")

    # SYSTEM_CONTRACT.md doit exister
    contract_path = Path("docs/freeze/SYSTEM_CONTRACT.md")
    if not contract_path.exists():
        stop(
            "SC00",
            "SYSTEM_CONTRACT.md absent -- " "fondation manquante -- ne pas continuer",
        )
        return False
    ok("SYSTEM_CONTRACT.md : present")

    # MRD_CURRENT_STATE.md doit exister
    state_path = Path("docs/freeze/MRD_CURRENT_STATE.md")
    if not state_path.exists():
        stop(
            "SC01",
            "MRD_CURRENT_STATE.md absent -- "
            "etat courant inconnu -- ne pas continuer",
        )
        return False
    ok("MRD_CURRENT_STATE.md : present")

    # BASELINE (warning seulement -- absente avant MRD-1)
    baseline_path = Path("docs/freeze/BASELINE_MRD_PRE_REBUILD.md")
    if not baseline_path.exists():
        warn("BASELINE_MRD_PRE_REBUILD.md absente -- " "MRD-1 non complete (attendu)")
    else:
        ok("BASELINE_MRD_PRE_REBUILD.md : presente")

    # CONTRACT-02 : DATABASE_URL ne doit pas pointer Railway
    _load_dotenv()
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url and ("railway" in db_url.lower() or "rlwy" in db_url.lower()):
        stop(
            "SC02",
            "CONTRACT-02 VIOLE -- "
            "DATABASE_URL contient 'railway' -- interdit en local",
        )
        return False
    if db_url:
        ok("CONTRACT-02 : DATABASE_URL locale (pas railway)")
    else:
        warn("CONTRACT-02 : DATABASE_URL absente -- sera verifie dans check_env()")

    # CONTRACT-04 : lire next_milestone
    content = state_path.read_text(encoding="utf-8")
    next_ms = None
    for line in content.splitlines():
        if line.strip().startswith("next_milestone"):
            parts = line.split(":")
            if len(parts) >= 2:
                next_ms = parts[1].strip()
                break
    if next_ms:
        ok(f"CONTRACT-04 : next_milestone = {next_ms}")
        info(f"Si ton mandat != {next_ms} " "-> STOP avant toute action")
    else:
        warn("next_milestone non lisible dans MRD_CURRENT_STATE.md")

    # CONTRACT-05 : verifier tag du dernier milestone complete
    last_completed = None
    for line in content.splitlines():
        if line.strip().startswith("last_completed"):
            parts = line.split(":")
            if len(parts) >= 2:
                last_completed = parts[1].strip()
                break

    if last_completed and last_completed not in ("NONE", "N/A", ""):
        tag_check = subprocess.run(
            ["git", "tag", "--list", "mrd-*-done"], capture_output=True, text=True
        )
        tags = tag_check.stdout.strip().splitlines()
        raw = last_completed.lower().replace("mrd-", "").split()[0]
        expected_tag = f"mrd-{raw}-done"
        if any(expected_tag in t for t in tags):
            ok(f"CONTRACT-05 : tag {expected_tag} present")
        else:
            warn(
                f"CONTRACT-05 : tag {expected_tag} absent -- "
                "peut indiquer merge sans tag CTO"
            )
    return True


# ── S0 : Variables d'environnement ───────────────────────────────────────
def check_env() -> tuple[str, str, str, bool]:
    head("ENVIRONNEMENT")
    _load_dotenv()

    db_url = os.environ.get("DATABASE_URL", "")
    railway_db_url = os.environ.get("RAILWAY_DATABASE_URL", "")
    env = os.environ.get("ENV", "unknown")
    redis = os.environ.get("REDIS_URL", "")

    if not db_url:
        stop("ENV", "DATABASE_URL absente (ni shell ni .env)")
    else:
        is_railway = "railway" in db_url.lower() or "rlwy" in db_url.lower()
        db_type = "RAILWAY" if is_railway else "LOCAL"
        if is_railway:
            warn(f"DATABASE_URL -> {db_type} (prod -- attention)")
        else:
            ok(f"DATABASE_URL -> {db_type}")

    if railway_db_url:
        ok("RAILWAY_DATABASE_URL -> DEFINIE")
    else:
        warn("RAILWAY_DATABASE_URL -> ABSENTE")

    info(f"ENV={env}")
    ok(f"REDIS_URL={'DEFINIE' if redis else 'ABSENTE'}")

    is_railway_local = bool(db_url) and (
        "railway" in db_url.lower() or "rlwy" in db_url.lower()
    )
    return db_url, railway_db_url, env, is_railway_local


# ── S1 : Git ──────────────────────────────────────────────────────────────
def check_git() -> str:
    head("GIT")
    branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()
    info(f"Branch : {branch}")

    log = subprocess.run(
        ["git", "log", "--oneline", "-3"], capture_output=True, text=True
    ).stdout.strip()
    info(f"Log :\n  {log.replace(chr(10), chr(10)+'  ')}")

    stash = subprocess.run(
        ["git", "stash", "list"], capture_output=True, text=True
    ).stdout.strip()
    if stash:
        count = len(stash.splitlines())
        warn(f"Stash non vide : {count} entree(s)")
    else:
        ok("Stash : vide")

    dirty = subprocess.run(
        ["git", "diff", "--name-only"], capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        warn(f"Fichiers modifies non commites :\n  {dirty}")
    else:
        ok("Working tree : propre")

    return branch


# ── S2 : Alembic ──────────────────────────────────────────────────────────
def check_alembic() -> tuple[list, str]:
    head("ALEMBIC")
    heads_result = subprocess.run(["alembic", "heads"], capture_output=True, text=True)
    current_result = subprocess.run(
        ["alembic", "current"], capture_output=True, text=True
    )

    head_lines = [
        line.strip().split()[0]
        for line in heads_result.stdout.strip().splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    current_line = next(
        (
            line.strip()
            for line in current_result.stdout.splitlines()
            if line.strip() and not line.startswith("INFO")
        ),
        "INACCESSIBLE",
    )

    if len(head_lines) == 1:
        ok(f"Heads (repo) : {head_lines[0]}")
    elif len(head_lines) == 0:
        stop("ALC1", "alembic heads = 0 lignes")
    else:
        stop("ALC2", f"alembic heads = {len(head_lines)} tetes : {head_lines}")

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
        err("DATABASE_URL absente -- skip probe DB")
        return result

    try:
        import psycopg
    except ImportError:
        err("psycopg non installe -- pip install psycopg[binary]")
        return result

    conn_url = _normalize_db_url(db_url)

    try:
        conn = psycopg.connect(conn_url, connect_timeout=5)
        cur = conn.cursor()
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
            warn(f"alembic_version : ERREUR -- {e}")

        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name NOT IN (
                'information_schema','pg_catalog','pg_toast','pg_temp_1'
            )
            ORDER BY schema_name
        """)
        result["schemas"] = [r[0] for r in cur.fetchall()]
        ok(f"Schemas : {result['schemas']}")

        if "couche_b" in result["schemas"]:
            for label, q in [
                (
                    "dict_items_actifs",
                    "SELECT COUNT(*) FROM couche_b.procurement_dict_items WHERE active=TRUE",
                ),
                (
                    "dict_items_total",
                    "SELECT COUNT(*) FROM couche_b.procurement_dict_items",
                ),
                ("aliases", "SELECT COUNT(*) FROM couche_b.procurement_dict_aliases"),
                (
                    "seeds_human_validated",
                    (
                        "SELECT COUNT(*) FROM couche_b.procurement_dict_items "
                        "WHERE human_validated=TRUE AND active=TRUE"
                    ),
                ),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:35} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR -- {e}")

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
            found = set(result["triggers"])
            missing = expected - found
            if missing:
                stop("TRG", f"Triggers manquants : {missing}")
            else:
                ok("Triggers critiques : tous presents")

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
                stop("CAS", f"CASCADE FK detectee : {result['cascades']}")
            else:
                ok("CASCADE FK : aucune")

        if "public" in result["schemas"]:
            for label, q in [
                ("vendors", "SELECT COUNT(*) FROM public.vendors"),
                ("mercurials", "SELECT COUNT(*) FROM public.mercurials"),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:35} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR -- {e}")

        conn.close()

    except Exception as e:
        stop("DB", f"DB inaccessible : {e}")
        err("Verifier que PostgreSQL local est demarre")
        err("Verifier DATABASE_URL dans .env")

    return result


# ── S4 : Database Railway (optionnel) ─────────────────────────────────────
def check_railway_db(railway_db_url: str) -> dict:
    head("DATABASE RAILWAY")
    result = {"accessible": False, "alembic_version": None, "counts": {}}

    if not railway_db_url:
        warn("RAILWAY_DATABASE_URL absente -- skip probe Railway")
        return result

    try:
        import psycopg

        conn = psycopg.connect(railway_db_url, connect_timeout=15)
        cur = conn.cursor()
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
            warn(f"Railway alembic_version : ERREUR -- {e}")

        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema','pg_catalog','pg_toast')
            ORDER BY schema_name
        """)
        schemas = [r[0] for r in cur.fetchall()]
        ok(f"Railway schemas : {schemas}")

        if "couche_b" in schemas:
            for label, q in [
                (
                    "railway_dict_items_actifs",
                    "SELECT COUNT(*) FROM couche_b.procurement_dict_items WHERE active=TRUE",
                ),
                (
                    "railway_aliases",
                    "SELECT COUNT(*) FROM couche_b.procurement_dict_aliases",
                ),
                (
                    "railway_seeds_human_validated",
                    (
                        "SELECT COUNT(*) FROM couche_b.procurement_dict_items "
                        "WHERE human_validated=TRUE AND active=TRUE"
                    ),
                ),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:40} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR -- {e}")

        if "public" in schemas:
            for label, q in [
                ("railway_vendors", "SELECT COUNT(*) FROM public.vendors"),
                ("railway_mercurials", "SELECT COUNT(*) FROM public.mercurials"),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                    result["counts"][label] = val
                    ok(f"{label:40} : {val}")
                except Exception as e:
                    warn(f"{label} : ERREUR -- {e}")

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
# Chaine ordonnee connue — synchronisee manuellement avec alembic/versions/
_KNOWN_MIGRATION_CHAIN: list[str] = [
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
]


def _compute_migration_delta(db_versions: list[str]) -> list[str]:
    """Retourne la liste ordonnee des migrations manquantes entre db_versions et le head."""
    if not db_versions:
        return _KNOWN_MIGRATION_CHAIN[:]
    current_idx = None
    for v in db_versions:
        if v in _KNOWN_MIGRATION_CHAIN:
            idx = _KNOWN_MIGRATION_CHAIN.index(v)
            if current_idx is None or idx > current_idx:
                current_idx = idx
    if current_idx is None:
        return _KNOWN_MIGRATION_CHAIN[:]
    return _KNOWN_MIGRATION_CHAIN[current_idx + 1 :]


def check_alignment(head_lines: list, db_result: dict, railway_result: dict):
    head("ALIGNEMENT REPO <-> LOCAL <-> RAILWAY")
    repo_head = head_lines[0] if head_lines else None
    local_ver = db_result.get("alembic_version", [])
    rail_ver = railway_result.get("alembic_version", [])

    if repo_head and local_ver:
        if repo_head in local_ver:
            ok(f"REPO <-> LOCAL  : ALIGNE   ({repo_head})")
        else:
            delta = _compute_migration_delta(local_ver)
            stop("ALN-LOCAL", f"DESALIGNE repo={repo_head} local={local_ver}")
            if delta:
                info(f"  Migrations pending LOCAL ({len(delta)}) :")
                for m in delta:
                    info(f"    -> {m}")
    else:
        warn("REPO <-> LOCAL  : non verifiable")

    if repo_head and rail_ver:
        if repo_head in rail_ver:
            ok(f"REPO <-> RAILWAY: ALIGNE   ({repo_head})")
        else:
            delta = _compute_migration_delta(rail_ver)
            stop("ALN-RAIL", f"DESALIGNE repo={repo_head} railway={rail_ver}")
            if delta:
                info(f"  Migrations pending RAILWAY ({len(delta)}) :")
                for m in delta:
                    info(f"    -> {m}")
                info("  Runbook : docs/ops/RAILWAY_MIGRATION_RUNBOOK.md")
                info("  Flag requis : DMS_ALLOW_RAILWAY_MIGRATE=1 (GO CTO obligatoire)")
    elif not rail_ver:
        warn(
            "REPO <-> RAILWAY: non verifiable "
            "(Railway inaccessible ou RAILWAY_DATABASE_URL absente)"
        )


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  DMS -- VALIDATE MRD STATE v2{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")

    # CONTRACT CHECK EN PREMIER -- avant tout
    contracts_ok = check_system_contract()
    if not contracts_ok:
        print(f"\n{RED}{BOLD}CONTRACTS VIOLES -- arret immediat{RESET}")
        print(f"{RED}Poster ce resultat au CTO{RESET}")
        sys.exit(1)

    # Suite normale
    db_url, railway_db_url, env, is_railway = check_env()
    check_git()
    head_lines, current = check_alembic()
    db_result = check_db(db_url)
    check_mrd_state()

    railway_result: dict = {}
    if "--railway" in sys.argv or railway_db_url:
        railway_result = check_railway_db(railway_db_url)

    check_alignment(head_lines, db_result, railway_result)

    head("VÉRIFICATION FREEZE HASHES")
    if not check_freeze_hashes():
        print("FREEZE HASHES : FAIL")
        sys.exit(1)
    print("FREEZE HASHES : PASS")

    head("VERDICT FINAL")
    if STOPS_DETECTED:
        print(f"\n{RED}{BOLD}STOPS DETECTES -- NE PAS COMMENCER DE MILESTONE{RESET}")
        for s in STOPS_DETECTED:
            err(s)
        print(f"\n{RED}Poster au CTO. Zero action.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}{BOLD}SYSTEME OK -- PRET POUR MANDAT{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
