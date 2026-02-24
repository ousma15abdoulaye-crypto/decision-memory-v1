# tests/pipeline/conftest.py
"""
Fixtures pipeline — réutilise db_conn + case_factory de la racine (tests/conftest.py).

pipeline_case_with_dao_and_offers : case minimal avec DAO (2 critères) + 2 offres.
  Utilisé pour les tests preflight OK et les tests de statuts complets.
  Cleanup via DELETE sur dao_criteria et offers (pas d'append-only sur ces tables).
  pipeline_runs étant append-only, les lignes insérées restent en DB (by design).
"""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def pipeline_case_with_dao_and_offers(db_conn, case_factory):
    """
    Crée un case avec :
      - 2 critères DAO dans public.dao_criteria
      - 2 offres dans public.offers

    Retourne case_id (TEXT).
    Cleanup : DELETE dao_criteria + offers (pas de CASCADE automatique).
    pipeline_runs reste en DB (append-only by design — Zéro DELETE de cleanup).
    """
    case_id = case_factory()

    criteria_ids: list[str] = []
    offer_ids: list[str] = []

    with db_conn.cursor() as cur:
        for i in range(2):
            cid = str(uuid.uuid4())
            criteria_ids.append(cid)
            cur.execute(
                """
                INSERT INTO public.dao_criteria
                    (id, case_id, categorie, critere_nom, description,
                     ponderation, type_reponse, seuil_elimination,
                     ordre_affichage, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, NOW()::text)
                """,
                (
                    cid,
                    case_id,
                    "commercial",
                    f"Critère test {i}",
                    f"Description test {i}",
                    0.5,
                    "quantitatif",
                    i,
                ),
            )

        for i in range(2):
            oid = str(uuid.uuid4())
            offer_ids.append(oid)
            cur.execute(
                """
                INSERT INTO public.offers
                    (id, case_id, supplier_name, offer_type,
                     file_hash, submitted_at, created_at)
                VALUES (%s, %s, %s, 'financial', %s, NOW()::text, NOW()::text)
                """,
                (
                    oid,
                    case_id,
                    f"Fournisseur-{i+1}",
                    f"hash-{uuid.uuid4().hex[:16]}",
                ),
            )

    yield case_id

    with db_conn.cursor() as cur:
        if criteria_ids:
            cur.execute(
                "DELETE FROM public.dao_criteria WHERE id = ANY(%s)",
                (criteria_ids,),
            )
        if offer_ids:
            cur.execute(
                "DELETE FROM public.offers WHERE id = ANY(%s)",
                (offer_ids,),
            )
