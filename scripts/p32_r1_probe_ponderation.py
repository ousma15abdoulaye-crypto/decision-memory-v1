"""P3.2 R1 — Probe ponderation : sommes globales + par famille

Exécute les 3 queries SQL requises pour déterminer si dao_criteria.ponderation
est globale (somme 100% tous critères) ou intra-famille (somme 100% par famille).
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    """Get database URL from environment."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Convert postgresql+psycopg:// to postgresql://
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    return db_url


def probe_ponderation_sums():
    """Execute R1 probes and report results."""
    db_url = get_db_url()

    print("=" * 80)
    print("P3.2 R1 — PROBE PONDERATION")
    print("=" * 80)
    print()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # Query 1 : sommes globales par workspace
        print("QUERY 1 — Sommes globales par workspace (sci_mali)")
        print("-" * 80)

        query1 = """
        SELECT
            pw.id AS workspace_id,
            pw.reference_code,
            SUM(dc.ponderation) AS sum_global,
            COUNT(dc.id) AS count_criteria
        FROM dao_criteria dc
        JOIN process_workspaces pw ON dc.workspace_id = pw.id
        WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
        AND dc.ponderation IS NOT NULL
        GROUP BY pw.id, pw.reference_code
        ORDER BY pw.reference_code
        LIMIT 20;
        """

        cursor1 = conn.execute(query1)
        rows1 = cursor1.fetchall()

        if not rows1:
            print("⚠️  Aucune row dao_criteria avec ponderation (sci_mali)")
        else:
            print(f"✅ {len(rows1)} workspaces avec critères pondérés")
            print()
            for row in rows1:
                ref = row["reference_code"] or "NO_REF"
                sum_g = row["sum_global"] or 0.0
                count = row["count_criteria"] or 0
                coherence = "✓ OK" if abs(sum_g - 100.0) <= 0.01 else f"✗ {sum_g:.2f}%"
                print(
                    f"  {ref[:30]:<30} | sum={sum_g:6.2f}% | count={count:3d} | {coherence}"
                )

        print()
        print()

        # Query 2a : vérifier colonnes famille
        print(
            "QUERY 2A — Colonnes disponibles (famille, criterion_category, categorie)"
        )
        print("-" * 80)

        query2a = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'dao_criteria'
        AND column_name IN ('famille', 'criterion_category', 'categorie')
        ORDER BY column_name;
        """

        cursor2a = conn.execute(query2a)
        rows2a = cursor2a.fetchall()

        available_columns = {row["column_name"] for row in rows2a}
        print(f"Colonnes trouvées : {available_columns or 'AUCUNE'}")
        print()

        # Query 2b : sommes par famille (si colonne existe)
        if "famille" in available_columns:
            print("QUERY 2B — Sommes par famille (colonne 'famille' existe)")
            print("-" * 80)

            query2b = """
            SELECT
                pw.reference_code,
                dc.famille,
                SUM(dc.ponderation) AS sum_famille,
                COUNT(dc.id) AS count_criteria
            FROM dao_criteria dc
            JOIN process_workspaces pw ON dc.workspace_id = pw.id
            WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
            AND dc.famille IS NOT NULL
            AND dc.ponderation IS NOT NULL
            GROUP BY pw.reference_code, dc.famille
            ORDER BY pw.reference_code, dc.famille
            LIMIT 50;
            """

            cursor2b = conn.execute(query2b)
            rows2b = cursor2b.fetchall()

            if not rows2b:
                print(
                    "⚠️  Colonne 'famille' existe mais aucune row avec famille + ponderation"
                )
            else:
                print(f"✅ {len(rows2b)} combinaisons (workspace × famille)")
                print()
                current_ws = None
                ws_total = 0.0
                for row in rows2b:
                    ref = row["reference_code"] or "NO_REF"
                    fam = row["famille"] or "NO_FAMILLE"
                    sum_f = row["sum_famille"] or 0.0
                    count = row["count_criteria"] or 0

                    if current_ws != ref:
                        if current_ws is not None:
                            coherence_ws = (
                                "✓ OK"
                                if abs(ws_total - 100.0) <= 0.01
                                else f"✗ {ws_total:.2f}%"
                            )
                            print(
                                f"    TOTAL {current_ws[:20]:<20} : {ws_total:6.2f}% | {coherence_ws}"
                            )
                            print()
                        current_ws = ref
                        ws_total = 0.0
                        print(f"  {ref[:30]}")

                    ws_total += sum_f
                    print(f"    {fam[:20]:<20} | sum={sum_f:6.2f}% | count={count:3d}")

                # Dernière workspace
                if current_ws is not None:
                    coherence_ws = (
                        "✓ OK"
                        if abs(ws_total - 100.0) <= 0.01
                        else f"✗ {ws_total:.2f}%"
                    )
                    print(
                        f"    TOTAL {current_ws[:20]:<20} : {ws_total:6.2f}% | {coherence_ws}"
                    )

        elif "criterion_category" in available_columns:
            print(
                "QUERY 2B — Sommes par criterion_category (colonne 'famille' absente)"
            )
            print("-" * 80)

            query2b_alt = """
            SELECT
                pw.reference_code,
                dc.criterion_category,
                SUM(dc.ponderation) AS sum_category,
                COUNT(dc.id) AS count_criteria
            FROM dao_criteria dc
            JOIN process_workspaces pw ON dc.workspace_id = pw.id
            WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
            AND dc.criterion_category IS NOT NULL
            AND dc.ponderation IS NOT NULL
            GROUP BY pw.reference_code, dc.criterion_category
            ORDER BY pw.reference_code, dc.criterion_category
            LIMIT 50;
            """

            cursor2b_alt = conn.execute(query2b_alt)
            rows2b_alt = cursor2b_alt.fetchall()

            if not rows2b_alt:
                print("⚠️  Colonne 'criterion_category' existe mais aucune row remplie")
            else:
                print(f"✅ {len(rows2b_alt)} combinaisons (workspace × category)")
                print()
                for row in rows2b_alt:
                    ref = row["reference_code"] or "NO_REF"
                    cat = row["criterion_category"] or "NO_CAT"
                    sum_c = row["sum_category"] or 0.0
                    count = row["count_criteria"] or 0
                    print(
                        f"  {ref[:30]:<30} | {cat[:20]:<20} | sum={sum_c:6.2f}% | count={count:3d}"
                    )

        else:
            print("⚠️  AUCUNE colonne famille/criterion_category trouvée")

        print()
        print()

        # Query 3 : échantillon critères
        print("QUERY 3 — Échantillon 20 critères récents (sci_mali)")
        print("-" * 80)

        famille_col = "famille" if "famille" in available_columns else "NULL"
        cat_col = (
            "criterion_category"
            if "criterion_category" in available_columns
            else "NULL"
        )

        query3 = f"""
        SELECT
            dc.id,
            SUBSTRING(dc.critere_nom FROM 1 FOR 50) AS critere_nom,
            dc.ponderation,
            dc.{famille_col} AS famille,
            dc.{cat_col} AS criterion_category,
            dc.categorie
        FROM dao_criteria dc
        JOIN process_workspaces pw ON dc.workspace_id = pw.id
        WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
        AND dc.ponderation IS NOT NULL
        ORDER BY dc.created_at DESC
        LIMIT 20;
        """

        cursor3 = conn.execute(query3)
        rows3 = cursor3.fetchall()

        if not rows3:
            print("⚠️  Aucun critère trouvé")
        else:
            print(f"✅ {len(rows3)} critères")
            print()
            for row in rows3:
                nom = (row["critere_nom"] or "NO_NAME")[:40]
                pond = row["ponderation"] or 0.0
                fam = row["famille"] or "-"
                cat = row["criterion_category"] or "-"
                print(
                    f"  {nom:<40} | pond={pond:5.1f}% | fam={fam:<15} | cat={cat:<15}"
                )

    print()
    print("=" * 80)
    print("PROBE R1 TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    try:
        probe_ponderation_sums()
    except Exception as e:
        print(f"❌ ERREUR : {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
