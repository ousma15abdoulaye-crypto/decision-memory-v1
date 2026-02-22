"""
Router FastAPI -- PriceCheck -- DMS V3.3.2 / ADR-0009.

Couche A uniquement. READ-ONLY. Aucune écriture DB.
Prefixe : /price-check (Constitution DMS V3.3.2 -- no scoring routes).
"""

from __future__ import annotations

from fastapi import APIRouter

from src.couche_a.price_check.engine import analyze_batch
from src.couche_a.price_check.schemas import OffreInput, PriceCheckResult
from src.db.connection import get_db_cursor

router = APIRouter(prefix="/price-check", tags=["price-check"])


@router.post("/analyze", response_model=PriceCheckResult)
def analyze_one(body: OffreInput) -> PriceCheckResult:
    """Analyze a single offer against mercuriale reference prices."""
    with get_db_cursor() as cur:
        conn = cur.connection
        results = analyze_batch([body], conn)
        return results[0]


@router.post("/analyze-batch", response_model=list[PriceCheckResult])
def analyze_many(body: list[OffreInput]) -> list[PriceCheckResult]:
    """Analyze a batch of offers (1 DB round-trip per lot)."""
    if not body:
        return []
    with get_db_cursor() as cur:
        conn = cur.connection
        return analyze_batch(body, conn)
