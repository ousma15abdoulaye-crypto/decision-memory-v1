"""Script investigation DB — INV-1 à INV-12."""
import os
import sys
from src.db import get_connection, db_fetchall, db_execute_one

def main():
    # INV-1: Tables M13
    print("=== INV-1: Tables M13 ===")
    with get_connection() as conn:
        tables = db_fetchall(conn, """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE '%m13%'
            ORDER BY table_name
        """, {})
        for t in tables:
            print(f"  - {t['table_name']}")

    # INV-2: M13 profile versions count
    print("\n=== INV-2: M13 Regulatory Profiles ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as count, MAX(created_at) as latest
            FROM m13_regulatory_profile_versions
        """, {})
        print(f"  Count: {row['count']}, Latest: {row['latest']}")

    # INV-3: Recent offer extractions
    print("\n=== INV-3: Recent Offer Extractions ===")
    with get_connection() as conn:
        rows = db_fetchall(conn, """
            SELECT id::text, workspace_id::text, bundle_id::text, supplier_name, created_at
            FROM offer_extractions
            ORDER BY created_at DESC LIMIT 5
        """, {})
        for r in rows:
            print(f"  {r['id'][:8]} | ws={r['workspace_id'][:8]} | bundle={r['bundle_id'][:8]} | {r['supplier_name']}")

    # INV-4: Evaluation documents
    print("\n=== INV-4: Evaluation Documents (M14) ===")
    with get_connection() as conn:
        rows = db_fetchall(conn, """
            SELECT id::text, workspace_id::text, created_at,
                   (scores_matrix IS NOT NULL) as has_scores
            FROM evaluation_documents
            ORDER BY created_at DESC LIMIT 5
        """, {})
        for r in rows:
            print(f"  {r['id'][:8]} | ws={r['workspace_id'][:8]} | scores={r['has_scores']}")

    # INV-5: Supplier bundles
    print("\n=== INV-5: Supplier Bundles ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT workspace_id) as workspaces,
                   COUNT(CASE WHEN bundle_status = 'assembled' THEN 1 END) as assembled
            FROM supplier_bundles
        """, {})
        print(f"  Total: {row['total']}, Workspaces: {row['workspaces']}, Assembled: {row['assembled']}")

    # INV-6: Bundle documents with OCR
    print("\n=== INV-6: Bundle Documents with OCR ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN raw_text IS NOT NULL AND trim(raw_text) <> '' THEN 1 END) as with_ocr
            FROM bundle_documents
        """, {})
        print(f"  Total: {row['total']}, With OCR: {row['with_ocr']}")

    # INV-7: Workspaces status distribution
    print("\n=== INV-7: Workspaces Status ===")
    with get_connection() as conn:
        rows = db_fetchall(conn, """
            SELECT status, COUNT(*) as count
            FROM process_workspaces
            GROUP BY status
            ORDER BY count DESC
        """, {})
        for r in rows:
            print(f"  {r['status']}: {r['count']}")

    # INV-8: DAO criteria
    print("\n=== INV-8: DAO Criteria ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT workspace_id) as workspaces
            FROM dao_criteria
        """, {})
        print(f"  Total criteria: {row['total']}, Workspaces: {row['workspaces']}")

    # INV-9: Committees
    print("\n=== INV-9: Committees ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT case_id) as cases
            FROM committees
        """, {})
        print(f"  Total committees: {row['total']}, Cases: {row['cases']}")

    # INV-10: Assessment grids
    print("\n=== INV-10: Assessment Grids (M16) ===")
    with get_connection() as conn:
        row = db_execute_one(conn, """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT workspace_id) as workspaces
            FROM assessment_grids
        """, {})
        print(f"  Total grids: {row['total']}, Workspaces: {row['workspaces']}")

    # INV-11: Check alembic versions
    print("\n=== INV-11: Alembic Migrations ===")
    with get_connection() as conn:
        rows = db_fetchall(conn, """
            SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 5
        """, {})
        for r in rows:
            print(f"  {r['version_num']}")

    # INV-12: Pipeline V5 test workspace
    print("\n=== INV-12: Test Workspace f1a6edfb ===")
    wid = "f1a6edfb-ac50-4301-a1a9-7a80053c632a"
    with get_connection() as conn:
        ws = db_execute_one(conn, """
            SELECT status, legacy_case_id::text FROM process_workspaces WHERE id = :wid
        """, {"wid": wid})
        if ws:
            print(f"  Status: {ws['status']}, Case: {ws['legacy_case_id']}")

            bundles = db_execute_one(conn, """
                SELECT COUNT(*) as count FROM supplier_bundles WHERE workspace_id = :wid
            """, {"wid": wid})
            print(f"  Bundles: {bundles['count']}")

            docs = db_execute_one(conn, """
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN raw_text IS NOT NULL THEN 1 END) as with_ocr
                FROM bundle_documents WHERE workspace_id = :wid
            """, {"wid": wid})
            print(f"  Documents: {docs['total']}, OCR: {docs['with_ocr']}")

            offers = db_execute_one(conn, """
                SELECT COUNT(*) as count FROM offer_extractions WHERE workspace_id = :wid
            """, {"wid": wid})
            print(f"  Offers extracted: {offers['count']}")

            eval_doc = db_execute_one(conn, """
                SELECT COUNT(*) as count FROM evaluation_documents WHERE workspace_id = :wid
            """, {"wid": wid})
            print(f"  Evaluation docs: {eval_doc['count']}")

if __name__ == "__main__":
    main()
