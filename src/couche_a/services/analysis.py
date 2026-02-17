"""Pre-analysis and scoring services for Couche A."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    analyses_table,
    audits_table,
    deserialize_json,
    ensure_schema,
    extractions_table,
    generate_id,
    get_engine,
    offers_table,
    serialize_json,
)

STATUS_CONFORME = "CONFORME"
STATUS_NON_CONFORME = "NON_CONFORME"
STATUS_PARTIEL = "PARTIEL"
STATUS_REVUE = "REVUE_MANUELLE"


def _compute_scores(missing_fields: List[str]) -> Dict[str, float]:
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


def _derive_status(missing_fields: List[str]) -> str:
    if not missing_fields:
        return STATUS_CONFORME
    if "fournisseur" in missing_fields or "montant" in missing_fields:
        return STATUS_NON_CONFORME
    return STATUS_PARTIEL


async def analyze_offer(offer_id: str) -> Dict[str, Any]:
    """Run the pre-analysis rules engine for an offer."""

    def _process() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                offer_row = conn.execute(select(offers_table).where(offers_table.c.id == offer_id)).mappings().first()
                if not offer_row:
                    raise ValueError("Offre introuvable.")

                extraction_row = (
                    conn.execute(
                        select(extractions_table)
                        .where(extractions_table.c.offer_id == offer_id)
                        .order_by(extractions_table.c.created_at.desc())
                    )
                    .mappings()
                    .first()
                )

                if not extraction_row:
                    status = STATUS_REVUE
                    scores = _compute_scores(["fournisseur", "montant"])
                    missing_fields = ["fournisseur", "montant"]
                else:
                    missing_fields = deserialize_json(extraction_row["missing_json"])
                    if not isinstance(missing_fields, list):
                        missing_fields = []
                    status = _derive_status(missing_fields)
                    scores = _compute_scores(missing_fields)

                analysis_id = generate_id()
                conn.execute(
                    analyses_table.insert().values(
                        id=analysis_id,
                        offer_id=offer_id,
                        status=status,
                        **scores,
                    )
                )
                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="analysis",
                        entity_id=analysis_id,
                        action="PRE_ANALYSE",
                        actor=None,
                        details_json=serialize_json({"status": status, "missing_fields": missing_fields}),
                    )
                )

            return {
                "analysis_id": analysis_id,
                "offer_id": offer_id,
                "status": status,
                "scores": scores,
                "missing_fields": missing_fields,
            }
        except SQLAlchemyError as exc:
            raise RuntimeError("Erreur lors de la pré-analyse.") from exc

    return await asyncio.to_thread(_process)
