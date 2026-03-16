"""Pre-analysis and scoring services for Couche A."""

from __future__ import annotations

import asyncio
from typing import Any

from ..models import (
    deserialize_json,
    ensure_schema,
    generate_id,
    get_connection,
    serialize_json,
)

STATUS_CONFORME = "CONFORME"
STATUS_NON_CONFORME = "NON_CONFORME"
STATUS_PARTIEL = "PARTIEL"
STATUS_REVUE = "REVUE_MANUELLE"


def _compute_scores(missing_fields: list[str]) -> dict[str, float]:
    """Compute placeholder scores based on missing fields."""
    base = 25.0
    penalty = 5.0 * len(missing_fields)
    essentials = max(base - penalty, 0.0)
    capacity = max(base - penalty / 2, 0.0)
    sustainability = max(base - penalty / 3, 0.0)
    commercial = max(base - penalty / 1.5, 0.0)
    total = essentials + capacity + sustainability + commercial
    return {
        "essentials_score": essentials,
        "capacity_score": capacity,
        "sustainability_score": sustainability,
        "commercial_score": commercial,
        "total_score": total,
    }


def _derive_status(missing_fields: list[str]) -> str:
    if not missing_fields:
        return STATUS_CONFORME
    if "fournisseur" in missing_fields or "montant" in missing_fields:
        return STATUS_NON_CONFORME
    return STATUS_PARTIEL


async def analyze_offer(offer_id: str) -> dict[str, Any]:
    """Run the pre-analysis rules engine for an offer."""

    def _process() -> dict[str, Any]:
        ensure_schema()
        with get_connection() as conn:
            conn.execute(
                "SELECT * FROM offers WHERE id = %(offer_id)s",
                {"offer_id": offer_id},
            )
            offer_row = conn.fetchone()
            if not offer_row:
                raise ValueError("Offre introuvable.")

            conn.execute(
                """
                SELECT * FROM extractions
                WHERE offer_id = %(offer_id)s
                ORDER BY created_at DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                {"offer_id": offer_id},
            )
            extraction_row = conn.fetchone()

            if not extraction_row:
                status = STATUS_REVUE
                scores = _compute_scores(["fournisseur", "montant"])
                missing_fields = ["fournisseur", "montant"]
            else:
                missing_fields = deserialize_json(extraction_row.get("missing_json"))
                if not isinstance(missing_fields, list):
                    missing_fields = []
                status = _derive_status(missing_fields)
                scores = _compute_scores(missing_fields)

            analysis_id = generate_id()
            conn.execute(
                """
                INSERT INTO analyses (
                    id, offer_id, case_id, status,
                    essentials_score, capacity_score, sustainability_score,
                    commercial_score, total_score, analysis_type, result_json, created_at
                )
                VALUES (
                    %(id)s, %(offer_id)s, %(case_id)s, %(status)s,
                    %(essentials_score)s, %(capacity_score)s, %(sustainability_score)s,
                    %(commercial_score)s, %(total_score)s, 'PRE_ANALYSE', %(result_json)s, NOW()::TEXT
                )
                """,
                {
                    "id": analysis_id,
                    "offer_id": offer_id,
                    "case_id": offer_row["case_id"],
                    "status": status,
                    "essentials_score": scores["essentials_score"],
                    "capacity_score": scores["capacity_score"],
                    "sustainability_score": scores["sustainability_score"],
                    "commercial_score": scores["commercial_score"],
                    "total_score": scores["total_score"],
                    "result_json": serialize_json(
                        {"status": status, "missing_fields": missing_fields}
                    ),
                },
            )
            conn.execute(
                """
                INSERT INTO audits (
                    id, case_id, entity_type, entity_id, action, actor, details_json, created_at
                )
                VALUES (
                    %(id)s, %(case_id)s, 'analysis', %(entity_id)s, 'PRE_ANALYSE', %(actor)s, %(details_json)s, NOW()::TEXT
                )
                """,
                {
                    "id": generate_id(),
                    "case_id": offer_row["case_id"],
                    "entity_id": analysis_id,
                    "actor": None,
                    "details_json": serialize_json(
                        {"status": status, "missing_fields": missing_fields}
                    ),
                },
            )

        return {
            "analysis_id": analysis_id,
            "offer_id": offer_id,
            "status": status,
            "scores": scores,
            "missing_fields": missing_fields,
        }

    return await asyncio.to_thread(_process)
