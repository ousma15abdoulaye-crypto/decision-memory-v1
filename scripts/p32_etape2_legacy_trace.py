"""P3.2 ÉTAPE 2 — Probe traçabilité 19 workspaces LEGACY_90

Exécute queries traçabilité avec noms tables réels (probe schéma ÉTAPE 1).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    import os
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found")
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    return db_url


def probe_traceability():
    """Execute traceability probes on 19 LEGACY_90 workspaces."""
    db_url = get_db_url()

    print("=" * 80)
    print("P3.2 ÉTAPE 2 — PROBE TRAÇABILITÉ LEGACY_90")
    print("=" * 80)
    print()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:

        # QUERY 2F : Liste 19 reference_codes
        print("QUERY 2F — Liste complète 19 workspaces LEGACY_90")
        print("-" * 80)

        cursor = conn.execute("""
            SELECT
                pw.reference_code,
                pw.id AS workspace_id,
                SUM(dc.ponderation) AS sum_global,
                COUNT(dc.id) AS count_criteria
            FROM dao_criteria dc
            JOIN process_workspaces pw ON dc.workspace_id = pw.id
            WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
              AND dc.ponderation IS NOT NULL
            GROUP BY pw.id, pw.reference_code
            HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
            ORDER BY pw.reference_code;
        """)
        legacy_workspaces = cursor.fetchall()

        if not legacy_workspaces:
            print("⚠️  Aucun workspace LEGACY_90 trouvé")
            return

        print(f"✅ {len(legacy_workspaces)} workspaces LEGACY_90")
        print()
        for ws in legacy_workspaces:
            print(
                f"  {ws['reference_code']:<40} | sum={ws['sum_global']:6.2f}% | criteria={ws['count_criteria']:3d}"
            )

        print()
        print()

        # QUERY 2A : Métadonnées workspaces
        print("QUERY 2A — Métadonnées 19 workspaces LEGACY_90")
        print("-" * 80)

        cursor = conn.execute("""
            WITH workspace_legacy AS (
                SELECT pw.id, pw.reference_code
                FROM dao_criteria dc
                JOIN process_workspaces pw ON dc.workspace_id = pw.id
                WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
                  AND dc.ponderation IS NOT NULL
                GROUP BY pw.id, pw.reference_code
                HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
            )
            SELECT
                ws.reference_code,
                pw.created_at,
                pw.process_type,
                pw.status
            FROM workspace_legacy ws
            JOIN process_workspaces pw ON ws.id = pw.id
            ORDER BY pw.created_at;
        """)
        metadata_rows = cursor.fetchall()

        print()
        for row in metadata_rows:
            created = (
                row["created_at"].strftime("%Y-%m-%d")
                if row["created_at"]
                else "NO_DATE"
            )
            print(
                f"  {row['reference_code']:<40} | {created} | {row['process_type']:<10} | {row['status']}"
            )

        print()
        print()

        # QUERY 2B : Comparaison dates
        print("QUERY 2B — Dates création LEGACY_90 vs CONFORME")
        print("-" * 80)

        cursor = conn.execute("""
            WITH workspace_sums AS (
                SELECT
                    pw.created_at,
                    CASE
                        WHEN ABS(SUM(dc.ponderation) - 100.0) <= 0.01 THEN 'CONFORME'
                        WHEN ABS(SUM(dc.ponderation) - 90.0) <= 0.01 THEN 'LEGACY_90'
                        ELSE 'AUTRE'
                    END AS classification
                FROM dao_criteria dc
                JOIN process_workspaces pw ON dc.workspace_id = pw.id
                WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
                  AND dc.ponderation IS NOT NULL
                GROUP BY pw.id, pw.created_at
            )
            SELECT
                classification,
                COUNT(*) AS count_workspaces,
                MIN(created_at) AS earliest_created,
                MAX(created_at) AS latest_created
            FROM workspace_sums
            GROUP BY classification
            ORDER BY classification;
        """)
        date_comparison = cursor.fetchall()

        print()
        for row in date_comparison:
            earliest = (
                row["earliest_created"].strftime("%Y-%m-%d")
                if row["earliest_created"]
                else "N/A"
            )
            latest = (
                row["latest_created"].strftime("%Y-%m-%d")
                if row["latest_created"]
                else "N/A"
            )
            print(
                f"  {row['classification']:<15} | count={row['count_workspaces']:3d} | earliest={earliest} | latest={latest}"
            )

        print()
        print()

        # QUERY 2C : Liens tables métier
        print("QUERY 2C — Activité métier (counts tables liées)")
        print("-" * 80)

        cursor = conn.execute("""
            WITH workspace_legacy AS (
                SELECT pw.id, pw.reference_code
                FROM dao_criteria dc
                JOIN process_workspaces pw ON dc.workspace_id = pw.id
                WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
                  AND dc.ponderation IS NOT NULL
                GROUP BY pw.id, pw.reference_code
                HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
            )
            SELECT
                ws.reference_code,
                COUNT(DISTINCT doc.id) AS count_documents,
                COUNT(DISTINCT oe.id) AS count_offer_extractions,
                COUNT(DISTINCT sb.id) AS count_supplier_bundles,
                COUNT(DISTINCT ed.id) AS count_evaluation_documents,
                COUNT(DISTINCT ca.id) AS count_criterion_assessments
            FROM workspace_legacy ws
            LEFT JOIN documents doc ON ws.id = doc.workspace_id
            LEFT JOIN offer_extractions oe ON ws.id = oe.workspace_id
            LEFT JOIN supplier_bundles sb ON ws.id = sb.workspace_id
            LEFT JOIN evaluation_documents ed ON ws.id = ed.workspace_id
            LEFT JOIN criterion_assessments ca ON ws.id = ca.workspace_id
            GROUP BY ws.reference_code
            ORDER BY
                (COUNT(DISTINCT doc.id) + COUNT(DISTINCT oe.id) +
                 COUNT(DISTINCT ed.id) + COUNT(DISTINCT ca.id)) DESC;
        """)
        activity_rows = cursor.fetchall()

        print()
        print("Legend: docs | extractions | bundles | evaluations | assessments")
        print()
        for row in activity_rows:
            ref = row["reference_code"][:35]
            docs = row["count_documents"]
            extr = row["count_offer_extractions"]
            bund = row["count_supplier_bundles"]
            eval_ = row["count_evaluation_documents"]
            asse = row["count_criterion_assessments"]
            total = docs + extr + bund + eval_ + asse
            flag = "⚠️ ACTIF" if total > 0 else "✓ vide"
            print(
                f"  {ref:<35} | {docs:4d} | {extr:4d} | {bund:4d} | {eval_:4d} | {asse:4d} | {flag}"
            )

        print()
        print()

        # QUERY 2D : Tenant uniformité
        print("QUERY 2D — Tenant_id uniformité")
        print("-" * 80)

        cursor = conn.execute("""
            WITH workspace_legacy AS (
                SELECT pw.tenant_id
                FROM dao_criteria dc
                JOIN process_workspaces pw ON dc.workspace_id = pw.id
                WHERE dc.ponderation IS NOT NULL
                GROUP BY pw.id, pw.tenant_id
                HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
            )
            SELECT
                t.tenant_code,
                COUNT(*) AS count_legacy_90
            FROM workspace_legacy ws
            JOIN tenants t ON ws.tenant_id = t.id
            GROUP BY t.tenant_code
            ORDER BY count_legacy_90 DESC;
        """)
        tenant_rows = cursor.fetchall()

        print()
        for row in tenant_rows:
            print(
                f"  {row['tenant_code']:<30} | {row['count_legacy_90']:3d} workspaces LEGACY_90"
            )

        print()
        print()

        # QUERY 2E : Pattern famille échantillon
        print("QUERY 2E — Pattern famille 30/50/10 (échantillon 1 workspace)")
        print("-" * 80)

        cursor = conn.execute("""
            WITH workspace_sample AS (
                SELECT pw.id, pw.reference_code
                FROM dao_criteria dc
                JOIN process_workspaces pw ON dc.workspace_id = pw.id
                WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
                  AND dc.ponderation IS NOT NULL
                GROUP BY pw.id, pw.reference_code
                HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
                LIMIT 1
            )
            SELECT
                ws.reference_code,
                dc.famille,
                SUM(dc.ponderation) AS sum_famille,
                COUNT(dc.id) AS count_criteria
            FROM workspace_sample ws
            JOIN dao_criteria dc ON ws.id = dc.workspace_id
            WHERE dc.famille IS NOT NULL
              AND dc.ponderation IS NOT NULL
            GROUP BY ws.reference_code, dc.famille
            ORDER BY dc.famille;
        """)
        pattern_rows = cursor.fetchall()

        if not pattern_rows:
            print("⚠️  Colonne famille NULL (impossible extraire pattern)")
        else:
            ref = pattern_rows[0]["reference_code"]
            print(f"\nWorkspace échantillon : {ref}")
            print()
            total_famille = 0.0
            for row in pattern_rows:
                sum_f = row["sum_famille"]
                total_famille += sum_f
                print(
                    f"  {row['famille']:<20} | sum={sum_f:6.2f}% | criteria={row['count_criteria']:3d}"
                )
            print(f"  {'TOTAL':<20} | sum={total_famille:6.2f}%")

    print()
    print("=" * 80)
    print("PROBE TRAÇABILITÉ TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    try:
        probe_traceability()
    except Exception as e:
        print(f"❌ ERREUR : {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
