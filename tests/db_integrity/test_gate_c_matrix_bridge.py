"""Gate C — inéligible : 0 ligne criterion_assessments (DB requise)."""

from __future__ import annotations

import uuid

import pytest
from psycopg.types.json import Jsonb

from src.db import db_execute_one, get_connection
from src.db.tenant_context import (
    reset_rls_request_context,
    set_db_tenant_id,
    set_rls_is_admin,
)
from src.services.m14_bridge import (
    _delete_stale_scoring_rows,
    populate_assessments_from_m14,
)


@pytest.mark.db_integrity
def test_gate_c_ineligible_bundle_has_no_criterion_assessments(
    db_conn, case_factory
) -> None:
    """Bridge ne persiste pas de scoring pour un bundle absent de matrix_participants."""
    case_id = case_factory()
    committee_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            """
            INSERT INTO public.committees
                (committee_id, case_id, org_id, committee_type, created_by, status)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            """,
            (committee_id, case_id, "org-test", "achat", "test-user", "draft"),
        )
    crit_id = str(uuid.uuid4())
    ba = str(uuid.uuid4())
    bb = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    sha_a = uuid.uuid4().hex
    sha_b = uuid.uuid4().hex

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "SELECT id, tenant_id FROM process_workspaces WHERE legacy_case_id = %s",
            (case_id,),
        )
        row = cur.fetchone()
        assert row
        ws_id = str(row["id"])
        tenant_id = str(row["tenant_id"])

        cur.execute(
            """
            INSERT INTO public.dao_criteria
                (id, workspace_id, categorie, critere_nom, description,
                 ponderation, type_reponse, seuil_elimination,
                 ordre_affichage, created_at)
            VALUES (%s::text, %s::uuid, 'technical', 'Note technique', 'NT',
                    10.0, 'quantitatif', NULL::real, 0, NOW()::text)
            """,
            (crit_id, ws_id),
        )

        for bid, idx, vname in (
            (ba, 0, "Fournisseur A"),
            (bb, 1, "Fournisseur B"),
        ):
            cur.execute(
                """
                INSERT INTO supplier_bundles
                    (id, workspace_id, tenant_id, vendor_name_raw, bundle_index, bundle_status)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, 'complete')
                """,
                (bid, ws_id, tenant_id, vname, idx),
            )

        for doc_id, bid, sha in ((doc_a, ba, sha_a), (doc_b, bb, sha_b)):
            cur.execute(
                """
                INSERT INTO bundle_documents
                    (id, bundle_id, workspace_id, tenant_id, doc_type, doc_role,
                     filename, sha256, file_type, storage_path, raw_text)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, 'offer_technical', 'primary',
                        'o.pdf', %s::text, 'native_pdf', %s::text, 'texte offre')
                """,
                (doc_id, bid, ws_id, tenant_id, sha, f"s3://test/{doc_id}"),
            )

        scores = {
            "case_id": case_id,
            "evaluation_method": "lowest_price",
            "matrix_participants": [
                {"bundle_id": ba, "supplier_name": "Fournisseur A", "is_eligible": True}
            ],
            "excluded_from_matrix": [
                {
                    "bundle_id": bb,
                    "supplier_name": "Fournisseur B",
                    "reason": "ineligible",
                }
            ],
            "offer_evaluations": [
                {
                    "offer_document_id": ba,
                    "supplier_name": "Fournisseur A",
                    "is_eligible": True,
                    "eligibility_results": [],
                    "compliance_results": [],
                    "flags": [],
                    "technical_score": {
                        "criteria_scores": [
                            {
                                "criteria_name": "Note technique",
                                "awarded_score": 8.0,
                                "max_score": 10.0,
                                "weight_percent": 100.0,
                                "justification": "",
                                "confidence": 0.8,
                            }
                        ],
                        "ponderation_coherence": "OK",
                        "confidence": 0.8,
                    },
                },
                {
                    "offer_document_id": bb,
                    "supplier_name": "Fournisseur B",
                    "is_eligible": False,
                    "eligibility_results": [
                        {
                            "check_id": "x",
                            "check_name": "fail",
                            "result": "FAIL",
                            "is_eliminatory": True,
                            "evidence": [],
                            "confidence": 0.8,
                        }
                    ],
                    "compliance_results": [],
                    "flags": [],
                    "technical_score": {
                        "criteria_scores": [
                            {
                                "criteria_name": "Note technique",
                                "awarded_score": 3.0,
                                "max_score": 10.0,
                                "weight_percent": 100.0,
                                "justification": "",
                                "confidence": 0.6,
                            }
                        ],
                        "ponderation_coherence": "OK",
                        "confidence": 0.6,
                    },
                },
            ],
        }

        cur.execute(
            """
            INSERT INTO evaluation_documents
                (id, workspace_id, committee_id, version, scores_matrix, status)
            VALUES (gen_random_uuid(), %s::uuid, %s::uuid, 1, %s::jsonb, 'draft')
            """,
            (ws_id, committee_id, Jsonb(scores)),
        )

    try:
        set_rls_is_admin(True)
        set_db_tenant_id(tenant_id)
        br = populate_assessments_from_m14(ws_id)
        assert br.errors == []

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*)::int AS n FROM criterion_assessments "
                "WHERE workspace_id = CAST(%s AS uuid) AND bundle_id = CAST(%s AS uuid)",
                (ws_id, bb),
            )
            n_bad = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(*)::int AS n FROM criterion_assessments "
                "WHERE workspace_id = CAST(%s AS uuid) AND bundle_id = CAST(%s AS uuid)",
                (ws_id, ba),
            )
            n_good = cur.fetchone()["n"]
        assert (
            n_bad == 0
        ), "bundle inéligible / hors matrice ne doit pas avoir de lignes CA"
        assert n_good >= 1
    finally:
        reset_rls_request_context()
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute(
                "DELETE FROM criterion_assessments WHERE workspace_id = CAST(%s AS uuid)",
                (ws_id,),
            )
            cur.execute(
                "DELETE FROM evaluation_documents WHERE workspace_id = CAST(%s AS uuid)",
                (ws_id,),
            )
            cur.execute(
                "DELETE FROM bundle_documents WHERE workspace_id = CAST(%s AS uuid)",
                (ws_id,),
            )
            cur.execute(
                "DELETE FROM supplier_bundles WHERE workspace_id = CAST(%s AS uuid)",
                (ws_id,),
            )
            cur.execute("DELETE FROM public.dao_criteria WHERE id = %s", (crit_id,))
            cur.execute(
                "DELETE FROM public.committees WHERE committee_id = CAST(%s AS uuid)",
                (committee_id,),
            )


@pytest.mark.db_integrity
def test_delete_stale_rows_no_psycopg_placeholder_error(
    case_factory,
) -> None:
    """_delete_stale_scoring_rows : pas de ProgrammingError psycopg3 sur ILIKE/LIKE."""
    case_id = case_factory()
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            "SELECT id::text AS id FROM process_workspaces WHERE legacy_case_id = :cid",
            {"cid": case_id},
        )
        assert row
        ws_id = str(row["id"])
        n = _delete_stale_scoring_rows(conn, ws_id)
    assert n >= 0
