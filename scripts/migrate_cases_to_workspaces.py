"""Migration des cases existants vers process_workspaces.

Execute manuellement en maintenance window (Phase 3, Semaine 3, Jour 1).
Idempotent -- peut etre relance sans risque.

BLOC-01 : whitelist frozenset + assertion avant interpolation.
BLOC-02 : map_status avec exception explicite (pas de default silencieux).

Usage :
    python scripts/migrate_cases_to_workspaces.py --tenant-code sci_mali [--dry-run]

Pre-conditions :
    - Migrations 068-073 appliquees (workspace_id nullable sur tables canon)
    - RAILWAY_DATABASE_URL ou DATABASE_URL disponible
    - Au moins 1 tenant presente dans la table tenants

Reference : docs/freeze/DMS_V4.2.0_MIGRATION_PLAN.md -- Script BLOC-01 + BLOC-02
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_TABLES: frozenset = frozenset(
    [
        "documents",
        "evaluation_criteria",
        "offer_extractions",
        "extraction_review_queue",
        "score_history",
        "elimination_log",
        "evaluation_documents",
        "decision_history",
        "dict_proposals",
        "market_surveys",
    ]
)


def map_procedure_type(canon_type: str) -> str:
    mapping = {
        "DAO": "appel_offres_ouvert",
        "RFQ": "devis_formel",
        "devis_unique": "devis_unique",
        "devis_simple": "devis_simple",
        "devis_formel": "devis_formel",
        "appel_offres_ouvert": "appel_offres_ouvert",
    }
    if canon_type not in mapping:
        raise ValueError(
            f"Procedure type non mappe : '{canon_type}'. "
            f"Ajouter au mapping avant de continuer. "
            f"Valeurs connues : {sorted(mapping.keys())}"
        )
    return mapping[canon_type]


def map_status(canon_status: str) -> str:
    mapping = {
        "draft": "draft",
        "open": "assembling",
        "evaluation": "in_analysis",
        "committee": "in_deliberation",
        "sealed": "sealed",
        "awarded": "closed",
        "cancelled": "cancelled",
        "closed": "closed",
    }
    if canon_status not in mapping:
        raise ValueError(
            f"Statut non mappe : '{canon_status}'. "
            f"Ajouter au mapping avant de continuer. "
            f"Valeurs connues : {sorted(mapping.keys())}"
        )
    return mapping[canon_status]


async def migrate_cases_to_workspaces(
    conn,
    tenant_id: str,
    dry_run: bool = False,
) -> int:
    cases = await conn.fetch("""
        SELECT * FROM cases
        WHERE id NOT IN (
            SELECT pw.legacy_case_id::TEXT
            FROM process_workspaces pw
            WHERE pw.legacy_case_id IS NOT NULL
        )
        """)

    logger.info("[MIGRATE] %d cases a migrer vers process_workspaces.", len(cases))
    migrated = 0

    for case in cases:
        case_id = case["id"]
        try:
            process_type = map_procedure_type(case.get("case_type") or "devis_formel")
            status = map_status(case.get("status") or "draft")
        except ValueError as exc:
            logger.error("[MIGRATE] Case %s -- %s -- SKIP.", case_id, exc)
            continue

        if dry_run:
            logger.info(
                "[DRY-RUN] Case %s -> workspace type=%s status=%s",
                case_id,
                process_type,
                status,
            )
            migrated += 1
            continue

        ws_id = await conn.fetchval(
            """
            INSERT INTO process_workspaces (
                tenant_id, created_by, reference_code, title,
                process_type, status, legacy_case_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            tenant_id,
            case.get("owner_id") or 1,
            case.get("reference") or f"CASE-{case_id[:8]}",
            case.get("title") or f"Migrated case {case_id[:8]}",
            process_type,
            status,
            str(case_id),
        )

        for table in ALLOWED_TABLES:
            assert table in ALLOWED_TABLES, f"Table non autorisee : {table}"
            updated = await conn.fetchval(
                f"""
                UPDATE {table}
                SET workspace_id = $1
                WHERE case_id = $2
                  AND workspace_id IS NULL
                """,
                ws_id,
                case_id,
            )
            if updated:
                logger.debug(
                    "[MIGRATE] %s : %s lignes pointent vers workspace %s",
                    table,
                    updated,
                    ws_id,
                )

        migrated += 1
        logger.info(
            "[MIGRATE] Case %s -> workspace %s (type=%s status=%s)",
            case_id,
            ws_id,
            process_type,
            status,
        )

    return migrated


async def verify_migration(conn) -> dict:
    """Retourne le nombre de lignes sans workspace_id pour chaque table.

    Un dictionnaire avec 0 partout = migration complete.
    """
    results = {}
    for table in ALLOWED_TABLES:
        assert table in ALLOWED_TABLES
        count = await conn.fetchval(f"""
            SELECT count(*) FROM {table}
            WHERE workspace_id IS NULL
              AND case_id IS NOT NULL
            """)
        results[table] = count
    return results


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migre les cases vers process_workspaces (V4.2.0)"
    )
    parser.add_argument(
        "--tenant-code",
        default="sci_mali",
        help="Code du tenant cible (default: sci_mali)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule la migration sans ecrire en base",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verifie uniquement l'etat sans migrer",
    )
    args = parser.parse_args()

    db_url = os.environ.get("RAILWAY_DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    if not db_url:
        logger.error("RAILWAY_DATABASE_URL ou DATABASE_URL requis.")
        return 1

    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://") :]
    if "postgresql+psycopg://" in db_url:
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg requis : pip install asyncpg")
        return 1

    conn = await asyncpg.connect(db_url)
    try:
        tenant_row = await conn.fetchrow(
            "SELECT id FROM tenants WHERE code = $1", args.tenant_code
        )
        if not tenant_row:
            logger.error(
                "Tenant '%s' absent -- executer migration 068 d'abord.",
                args.tenant_code,
            )
            return 1

        tenant_id = str(tenant_row["id"])

        if args.verify_only:
            results = await verify_migration(conn)
            all_ok = all(v == 0 for v in results.values())
            for table, count in results.items():
                status = "OK" if count == 0 else f"ATTENTION: {count} orphelins"
                logger.info("  %-35s : %s", table, status)
            return 0 if all_ok else 2

        migrated = await migrate_cases_to_workspaces(conn, tenant_id, args.dry_run)
        logger.info("[MIGRATE] %d cases traites.", migrated)

        if not args.dry_run:
            results = await verify_migration(conn)
            orphans = sum(results.values())
            if orphans > 0:
                logger.error(
                    "[VERIFY] %d artefacts sans workspace_id -- verifier les logs.",
                    orphans,
                )
                for table, count in results.items():
                    if count > 0:
                        logger.error("  %-35s : %d orphelins", table, count)
                return 2
            logger.info("[VERIFY] Tous les artefacts ont workspace_id. Migration OK.")

    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
