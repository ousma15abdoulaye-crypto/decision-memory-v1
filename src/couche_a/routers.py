"""FastAPI router for Couche A endpoints."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import request

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    analyses_table,
    cases_table,
    deserialize_json,
    documents_table,
    ensure_schema,
    extractions_table,
    get_engine,
    lots_table,
    offers_table,
)
from .services.analysis import analyze_offer
from .services.cba import export_cba, upload_cba_review
from .services.depot import save_depot
from .services.extraction import extract_and_store
from .services.pv import generate_pv_analyse, generate_pv_ouverture

router = APIRouter()


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


@router.post("/api/depot")
async def post_depot(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    lot_id: str = Form(...),
    document_type: Optional[str] = Form(None),
    offer_id: Optional[str] = Form(None),
    sender_email: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    received_at: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Handle a new document deposit."""
    try:
        result = await save_depot(
            upload=file,
            case_id=case_id,
            lot_id=lot_id,
            document_type=document_type,
            offer_id=offer_id,
            sender_email=sender_email,
            subject=subject,
            received_at=received_at,
        )
        await extract_and_store(result["document_id"])
        await analyze_offer(result["offer_id"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/dashboard")
async def get_dashboard(
    lot_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Return dashboard data with filters."""
    def _fetch() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                query = (
                    select(
                        offers_table,
                        cases_table.c.buyer_name,
                        lots_table.c.name.label("lot_name"),
                        analyses_table.c.status.label("analysis_status"),
                        analyses_table.c.total_score,
                    )
                    .select_from(
                        offers_table.join(cases_table, offers_table.c.case_id == cases_table.c.id)
                        .join(lots_table, offers_table.c.lot_id == lots_table.c.id)
                        .outerjoin(analyses_table, analyses_table.c.offer_id == offers_table.c.id)
                    )
                )
                if lot_id:
                    query = query.where(offers_table.c.lot_id == lot_id)
                if status:
                    query = query.where(analyses_table.c.status == status)
                start_dt = _parse_date(start_date)
                end_dt = _parse_date(end_date)
                if start_dt:
                    query = query.where(offers_table.c.created_at >= start_dt)
                if end_dt:
                    query = query.where(offers_table.c.created_at <= end_dt)

                rows = conn.execute(query).mappings().all()
                items: List[Dict[str, Any]] = []
                status_counts: Dict[str, int] = {}
                for row in rows:
                    item_status = row.get("analysis_status") or row["status"]
                    status_counts[item_status] = status_counts.get(item_status, 0) + 1
                    items.append(
                        {
                            "id": row["id"],
                            "acheteur": row["buyer_name"],
                            "fournisseur": row["supplier_name"],
                            "date": row["created_at"].isoformat() if row["created_at"] else None,
                            "type": row["offer_type"],
                            "montant": row["amount"],
                            "score": row.get("total_score"),
                            "statut": item_status,
                            "lot": row["lot_name"],
                        }
                    )
                return {"items": items, "status_counts": status_counts}
        except SQLAlchemyError as exc:
            raise RuntimeError("Erreur lors du chargement du dashboard.") from exc

    try:
        return await asyncio.to_thread(_fetch)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/offres/{offer_id}")
async def get_offre_detail(offer_id: str) -> Dict[str, Any]:
    """Return a detailed offer view."""
    def _fetch() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                offer = conn.execute(
                    select(offers_table).where(offers_table.c.id == offer_id)
                ).mappings().first()
                if not offer:
                    raise ValueError("Offre introuvable.")
                docs = conn.execute(
                    select(documents_table)
                    .where(documents_table.c.offer_id == offer_id)
                    .order_by(documents_table.c.created_at.desc())
                ).mappings().all()
                extraction = conn.execute(
                    select(extractions_table)
                    .where(extractions_table.c.offer_id == offer_id)
                    .order_by(extractions_table.c.created_at.desc())
                ).mappings().first()
                analysis = conn.execute(
                    select(analyses_table)
                    .where(analyses_table.c.offer_id == offer_id)
                    .order_by(analyses_table.c.created_at.desc())
                ).mappings().first()

                return {
                    "offer": dict(offer),
                    "documents": [dict(doc) for doc in docs],
                    "extraction": dict(extraction) if extraction else None,
                    "analysis": dict(analysis) if analysis else None,
                    "missing_fields": deserialize_json(extraction["missing_json"]) if extraction else [],
                }
        except SQLAlchemyError as exc:
            raise RuntimeError("Erreur lors du chargement de l'offre.") from exc

    try:
        return await asyncio.to_thread(_fetch)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/export-cba")
async def post_export_cba(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a CBA export."""
    offer_id = payload.get("offer_id")
    actor = payload.get("actor")
    if not offer_id:
        raise HTTPException(status_code=400, detail="offer_id requis.")
    try:
        return await export_cba(offer_id=offer_id, actor=actor)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/cba-review/upload")
async def post_cba_review(
    offer_id: str = Form(...),
    reviewer: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Upload a completed CBA file for committee review."""
    try:
        return await upload_cba_review(offer_id, file, reviewer)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/pv/ouverture")
async def post_pv_ouverture(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate PV d'ouverture."""
    lot_id = payload.get("lot_id")
    actor = payload.get("actor")
    if not lot_id:
        raise HTTPException(status_code=400, detail="lot_id requis.")
    try:
        return await generate_pv_ouverture(lot_id, actor)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/pv/analyse")
async def post_pv_analyse(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate PV d'analyse."""
    lot_id = payload.get("lot_id")
    actor = payload.get("actor")
    if not lot_id:
        raise HTTPException(status_code=400, detail="lot_id requis.")
    try:
        return await generate_pv_analyse(lot_id, actor)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _post_market_signal(base_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    def _send() -> Dict[str, Any]:
        endpoint = f"{base_url.rstrip('/')}/api/market-signals"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return {"status": response.status, "body": body}

    return await asyncio.to_thread(_send)


@router.post("/api/sync-market")
async def post_sync_market(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sync market signals to Couche B after committee validation."""
    approved = payload.get("approved")
    if not approved:
        raise HTTPException(status_code=400, detail="Validation comité requise.")
    base_url = payload.get("base_url", "http://localhost:8001")
    try:
        result = await _post_market_signal(base_url, payload.get("signal", {}))
        return {"result": result}
    except Exception as exc:  # noqa: BLE001 - surface connection errors
        raise HTTPException(status_code=502, detail="Erreur de synchronisation.") from exc
