"""Validation pré-pilote SCI Mali V4.2.0.

Vérifie les STOP SIGNALS SS-1 à SS-6 et SS-9 avant démarrage du pilote.
Les performance gates (PG-1 à PG-5) nécessitent un pilote en cours.

Usage:
    python scripts/validate_v420_pilote_gates.py [--tenant sci_mali]

Exit code:
    0 = tous les checks passent (GO)
    1 = au moins un STOP SIGNAL déclenché (NO-GO)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass


@dataclass
class CheckResult:
    signal: str
    label: str
    ok: bool
    detail: str = ""


def _get_conn():
    import os

    import psycopg

    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    if not url:
        raise RuntimeError("DATABASE_URL non défini.")
    return psycopg.connect(url, autocommit=True)


def check_ss1_alembic_heads(conn) -> CheckResult:
    """SS-1 : alembic heads > 1."""
    try:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
        n = len(rows)
        heads = [r[0] for r in rows]
        ok = n == 1
        return CheckResult(
            signal="SS-1",
            label="alembic heads == 1",
            ok=ok,
            detail=f"heads={heads}" if not ok else f"head={heads[0]}",
        )
    except Exception as exc:
        return CheckResult("SS-1", "alembic heads == 1", False, str(exc))


def check_ss3_users_id_type(conn) -> CheckResult:
    """SS-3 : users.id doit être INTEGER (pas UUID)."""
    try:
        row = conn.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'id'
            """).fetchone()
        if not row:
            return CheckResult(
                "SS-3", "users.id type INTEGER", False, "Table users non trouvée."
            )
        dtype = row[0].lower()
        ok = "int" in dtype
        return CheckResult(
            "SS-3",
            "users.id type INTEGER",
            ok,
            f"type={dtype}",
        )
    except Exception as exc:
        return CheckResult("SS-3", "users.id type INTEGER", False, str(exc))


def check_ss4_case_id_absent_after_074(conn) -> CheckResult:
    """SS-4 : case_id absent de documents et offer_extractions (migration 074 appliquée)."""
    tables_to_check = ["documents", "offer_extractions"]
    found = []
    try:
        for table in tables_to_check:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'case_id'
                """,
                (table,),
            ).fetchone()
            if row and row[0] > 0:
                found.append(table)

        # Check if migration 074 has been applied
        row074 = conn.execute(
            "SELECT version_num FROM alembic_version WHERE version_num LIKE '074%'"
        ).fetchone()

        if row074 and found:
            return CheckResult(
                "SS-4",
                "case_id absent après 074",
                False,
                f"case_id encore présent dans : {found}",
            )
        if not row074:
            return CheckResult(
                "SS-4",
                "case_id absent après 074",
                True,
                "Migration 074 non encore appliquée — SS-4 non applicable.",
            )
        return CheckResult(
            "SS-4", "case_id absent après 074", True, "OK — case_id supprimé."
        )
    except Exception as exc:
        return CheckResult("SS-4", "case_id absent après 074", False, str(exc))


def check_ss5_workspace_events_append_only(conn) -> CheckResult:
    """SS-5 : workspace_events append-only (UPDATE/DELETE rejetés)."""
    try:
        # Check trigger exists
        row = conn.execute("""
            SELECT COUNT(*) FROM information_schema.triggers
            WHERE event_object_table = 'workspace_events'
              AND trigger_name LIKE '%append_only%'
            """).fetchone()
        trigger_exists = row and row[0] > 0

        if not trigger_exists:
            # Also accept deny_updates naming
            row2 = conn.execute("""
                SELECT COUNT(*) FROM information_schema.triggers
                WHERE event_object_table = 'workspace_events'
                  AND (trigger_name LIKE '%deny%' OR trigger_name LIKE '%immutable%')
                """).fetchone()
            trigger_exists = row2 and row2[0] > 0

        return CheckResult(
            "SS-5",
            "workspace_events append-only trigger",
            trigger_exists,
            (
                "Trigger présent."
                if trigger_exists
                else "AUCUN trigger append-only trouvé."
            ),
        )
    except Exception as exc:
        return CheckResult(
            "SS-5", "workspace_events append-only trigger", False, str(exc)
        )


def check_ss6_confidence_values(conn) -> CheckResult:
    """SS-6 : confidence dans {0.6, 0.8, 1.0} uniquement."""
    try:
        # Check if table exists
        row_exists = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'dms_extraction_results'
            """).fetchone()

        if not row_exists or row_exists[0] == 0:
            return CheckResult(
                "SS-6",
                "confidence valeurs canoniques",
                True,
                "Table dms_extraction_results absente — SS-6 non applicable.",
            )

        row = conn.execute("""
            SELECT DISTINCT confidence FROM dms_extraction_results
            WHERE confidence NOT IN (0.6, 0.8, 1.0)
            LIMIT 5
            """).fetchall()
        bad_values = [r[0] for r in row]
        ok = len(bad_values) == 0
        return CheckResult(
            "SS-6",
            "confidence valeurs canoniques {0.6, 0.8, 1.0}",
            ok,
            f"Valeurs illégales : {bad_values}" if not ok else "OK.",
        )
    except Exception as exc:
        return CheckResult("SS-6", "confidence valeurs canoniques", False, str(exc))


def check_ss9_arq_projector_registered() -> CheckResult:
    """SS-9 : project_workspace_events_to_couche_b enregistré dans WorkerSettings."""
    try:
        from src.workers.arq_config import WorkerSettings

        fn_names = [fn.__name__ for fn in WorkerSettings.functions]
        ok = "project_workspace_events_to_couche_b" in fn_names
        return CheckResult(
            "SS-9",
            "ARQ projector Couche B enregistré",
            ok,
            f"Functions: {fn_names}" if not ok else "OK.",
        )
    except Exception as exc:
        return CheckResult("SS-9", "ARQ projector Couche B enregistré", False, str(exc))


def check_tenant_exists(conn, tenant_code: str) -> CheckResult:
    """Vérifie que le tenant pilote existe."""
    try:
        row_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'tenants'"
        ).fetchone()
        if not row_exists or row_exists[0] == 0:
            return CheckResult(
                "TENANT",
                f"Tenant {tenant_code!r} présent",
                False,
                "Table tenants absente (migrations 068+ non appliquées).",
            )

        row = conn.execute(
            "SELECT id FROM tenants WHERE code = %s",
            (tenant_code,),
        ).fetchone()
        ok = row is not None
        return CheckResult(
            "TENANT",
            f"Tenant {tenant_code!r} présent",
            ok,
            f"id={row[0]}" if ok else f"Tenant {tenant_code!r} absent.",
        )
    except Exception as exc:
        return CheckResult("TENANT", f"Tenant {tenant_code!r} présent", False, str(exc))


def check_v420_tables_created(conn) -> CheckResult:
    """Vérifie que les tables V4.2.0 clés sont présentes."""
    required = [
        "tenants",
        "process_workspaces",
        "workspace_events",
        "supplier_bundles",
        "bundle_documents",
        "committee_sessions",
        "rbac_permissions",
        "rbac_roles",
        "user_tenant_roles",
    ]
    missing = []
    try:
        for table in required:
            row = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                (table,),
            ).fetchone()
            if not row or row[0] == 0:
                missing.append(table)
        ok = len(missing) == 0
        return CheckResult(
            "TABLES",
            "Tables V4.2.0 créées",
            ok,
            (
                f"Manquantes : {missing}"
                if not ok
                else f"Toutes les {len(required)} tables présentes."
            ),
        )
    except Exception as exc:
        return CheckResult("TABLES", "Tables V4.2.0 créées", False, str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validation pré-pilote V4.2.0")
    parser.add_argument("--tenant", default="sci_mali", help="Code tenant pilote")
    args = parser.parse_args()

    print("=" * 60)
    print(f"DMS V4.2.0 — Validation pré-pilote (tenant={args.tenant!r})")
    print("=" * 60)

    try:
        conn = _get_conn()
    except RuntimeError as exc:
        print(f"\n[ERREUR] Connexion DB impossible : {exc}")
        return 1

    checks: list[CheckResult] = [
        check_ss1_alembic_heads(conn),
        check_ss3_users_id_type(conn),
        check_ss4_case_id_absent_after_074(conn),
        check_ss5_workspace_events_append_only(conn),
        check_ss6_confidence_values(conn),
        check_ss9_arq_projector_registered(),
        check_tenant_exists(conn, args.tenant),
        check_v420_tables_created(conn),
    ]

    conn.close()

    all_ok = True
    print()
    for result in checks:
        status = "OK  " if result.ok else "FAIL"
        marker = "✓" if result.ok else "✗"
        print(f"  [{status}] {marker} {result.signal:8s} — {result.label}")
        if result.detail:
            print(f"           {result.detail}")
        if not result.ok:
            all_ok = False

    print()
    if all_ok:
        print("GO — Tous les checks passent. Pilote peut démarrer.")
        return 0
    else:
        print("NO-GO — STOP SIGNAL(S) détecté(s). Corriger avant pilote.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
