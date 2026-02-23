# src/couche_a/committee/router.py
# Endpoints FastAPI — Couche A strictement (zéro Couche B).
from __future__ import annotations

import os
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.rows import dict_row

from . import service
from .models import (
    AddMemberRequest,
    CommitteeNotFoundError,
    CommitteeStateError,
    CommitteeValidationError,
    CreateCommitteeRequest,
    SealRequest,
    SetDecisionRequest,
)

router = APIRouter(prefix="/committee", tags=["committee"])


def _get_conn():
    """Dependency FastAPI : connexion psycopg autocommit=True (dict_row)."""
    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    conn = psycopg.connect(url, row_factory=dict_row, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------ comité


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_committee(
    req: CreateCommitteeRequest, conn=Depends(_get_conn)
) -> dict[str, Any]:
    try:
        committee_id = service.create_committee(req, conn)
        return {"committee_id": committee_id}
    except CommitteeValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{committee_id}")
def get_committee(committee_id: str, conn=Depends(_get_conn)) -> dict[str, Any]:
    try:
        return service.get_committee(committee_id, conn)
    except CommitteeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{committee_id}/open", status_code=status.HTTP_200_OK)
def open_session(committee_id: str, by: str, conn=Depends(_get_conn)) -> dict[str, Any]:
    try:
        service.open_session(committee_id, by, conn)
        return {"status": "ok"}
    except (CommitteeNotFoundError, CommitteeStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{committee_id}/review", status_code=status.HTTP_200_OK)
def set_in_review(
    committee_id: str, by: str, conn=Depends(_get_conn)
) -> dict[str, Any]:
    try:
        service.set_in_review(committee_id, by, conn)
        return {"status": "ok"}
    except (CommitteeNotFoundError, CommitteeStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ------------------------------------------------------------------ membres


@router.post("/{committee_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    committee_id: str,
    req: AddMemberRequest,
    by: str,
    conn=Depends(_get_conn),
) -> dict[str, Any]:
    try:
        member_id = service.add_member(committee_id, req, by, conn)
        return {"member_id": member_id}
    except (
        CommitteeNotFoundError,
        CommitteeStateError,
        CommitteeValidationError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{committee_id}/members/{member_id}", status_code=status.HTTP_200_OK)
def remove_member(
    committee_id: str, member_id: str, by: str, conn=Depends(_get_conn)
) -> dict[str, Any]:
    try:
        service.remove_member(committee_id, member_id, by, conn)
        return {"status": "ok"}
    except (CommitteeNotFoundError, CommitteeStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{committee_id}/members")
def list_members(committee_id: str, conn=Depends(_get_conn)) -> list[dict[str, Any]]:
    try:
        return service.list_members(committee_id, conn)
    except CommitteeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------ décision


@router.post("/{committee_id}/decision", status_code=status.HTTP_201_CREATED)
def set_decision(
    committee_id: str,
    req: SetDecisionRequest,
    by: str,
    conn=Depends(_get_conn),
) -> dict[str, Any]:
    try:
        decision_id = service.set_decision_candidate(committee_id, req, by, conn)
        return {"decision_id": decision_id}
    except (CommitteeNotFoundError, CommitteeStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{committee_id}/readiness")
def validate_readiness(committee_id: str, conn=Depends(_get_conn)) -> dict[str, Any]:
    try:
        return service.validate_readiness(committee_id, conn)
    except CommitteeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------ seal (CRITIQUE)


@router.post("/{committee_id}/seal", status_code=status.HTTP_200_OK)
def seal(
    committee_id: str,
    req: SealRequest,
    conn=Depends(_get_conn),
) -> dict[str, Any]:
    try:
        result = service.seal_committee_decision(committee_id, req, conn)
        return {"seal_id": result.seal_id, "snapshot_hash": result.snapshot_hash}
    except (
        CommitteeNotFoundError,
        CommitteeStateError,
        CommitteeValidationError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ------------------------------------------------------------------ cancel / events / snapshot


@router.post("/{committee_id}/cancel", status_code=status.HTTP_200_OK)
def cancel(
    committee_id: str, reason: str, by: str, conn=Depends(_get_conn)
) -> dict[str, Any]:
    try:
        service.cancel_committee(committee_id, reason, by, conn)
        return {"status": "ok"}
    except (CommitteeNotFoundError, CommitteeStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{committee_id}/events")
def get_events(committee_id: str, conn=Depends(_get_conn)) -> list[dict[str, Any]]:
    try:
        return service.get_events(committee_id, conn)
    except CommitteeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{committee_id}/snapshot")
def get_snapshot(committee_id: str, conn=Depends(_get_conn)) -> dict[str, Any] | None:
    try:
        snap = service.get_decision_snapshot(committee_id, conn)
        if snap is None:
            raise HTTPException(status_code=404, detail="snapshot non trouvé")
        return snap
    except CommitteeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
