# src/couche_a/committee/models.py
# Pydantic DTOs — Couche A strictement (zéro import Couche B).
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ------------------------------------------------------------------ Enums (texte)

COMMITTEE_TYPES = ("achat", "technique", "mixte")
COMMITTEE_STATUSES = ("draft", "open", "in_review", "sealed", "cancelled")
MEMBER_ROLES = ("chair", "member", "secretary", "observer", "approver")
MEMBER_STATUSES = ("invited", "active", "recused", "absent", "signed")
DECISION_STATUSES = ("proposed", "validated", "sealed", "rejected", "no_award")

COMMITTEE_EVENT_TYPES = (
    "committee_created",
    "member_added",
    "member_removed",
    "meeting_opened",
    "vote_recorded",
    "recommendation_set",
    "seal_requested",
    "seal_completed",
    "seal_rejected",
    "snapshot_emitted",
    "committee_cancelled",
)


# ------------------------------------------------------------------ Input DTOs


class CreateCommitteeRequest(BaseModel):
    case_id: str
    org_id: str
    committee_type: str = "achat"
    created_by: str


class AddMemberRequest(BaseModel):
    user_ref: str
    role: str = "member"
    can_vote: bool = False
    can_seal: bool = False
    can_edit_minutes: bool = False
    is_mandatory: bool = False
    quorum_counted: bool = False


class SetDecisionRequest(BaseModel):
    case_id: str
    selected_supplier_id: str | None = None
    supplier_name_raw: str | None = None
    decision_status: str = "proposed"
    rationale: str


class SealRequest(BaseModel):
    """Requête de scellement comité.

    sealed_by : champ d'audit obligatoire — ne peut pas être vide.
    Un scellement avec sealed_by="" rendrait l'audit trail inutilisable.
    """

    sealed_by: str
    zone: str = Field(..., min_length=1)
    currency: str = "XOF"
    alias_raw: str
    quantity: float | None = None
    unit: str | None = None
    price_paid: float | None = None
    item_id: str | None = None
    supplier_id: str | None = None
    source_hashes: dict[str, Any] = Field(default_factory=dict)
    scoring_meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sealed_by")
    @classmethod
    def sealed_by_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "sealed_by ne peut pas être vide — "
                "champ d'audit obligatoire pour la traçabilité du scellement"
            )
        return v.strip()


# ------------------------------------------------------------------ Output DTOs


class CommitteeResponse(BaseModel):
    committee_id: uuid.UUID
    case_id: str
    org_id: str
    committee_type: str
    status: str
    created_at: datetime
    created_by: str
    cancelled_reason: str | None
    sealed_at: datetime | None
    sealed_by: str | None


class MemberResponse(BaseModel):
    member_id: uuid.UUID
    committee_id: uuid.UUID
    user_ref: str
    role: str
    can_vote: bool
    can_seal: bool
    can_edit_minutes: bool
    is_mandatory: bool
    quorum_counted: bool
    status: str
    joined_at: datetime


class DecisionResponse(BaseModel):
    decision_id: uuid.UUID
    committee_id: uuid.UUID
    case_id: str
    selected_supplier_id: str | None
    supplier_name_raw: str | None
    decision_status: str
    rationale: str
    decision_at: datetime | None
    sealed_by: str | None
    seal_id: uuid.UUID | None
    created_at: datetime


class SealResult(BaseModel):
    seal_id: str
    snapshot_hash: str


class ReadinessResult(BaseModel):
    sealable: bool
    errors: list[str]


class CommitteeEventResponse(BaseModel):
    event_id: uuid.UUID
    committee_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    created_by: str


class SnapshotResponse(BaseModel):
    snapshot_id: uuid.UUID
    case_id: str
    committee_id: uuid.UUID | None
    committee_seal_id: uuid.UUID | None
    decision_at: datetime
    zone: str
    currency: str
    item_id: str | None
    alias_raw: str
    quantity: float | None
    unit: str | None
    price_paid: float | None
    supplier_id: str | None
    supplier_name_raw: str
    source_hashes: dict[str, Any]
    scoring_meta: dict[str, Any]
    snapshot_hash: str
    created_at: datetime


# ------------------------------------------------------------------ Exceptions


class CommitteeNotFoundError(Exception):
    pass


class CommitteeStateError(Exception):
    pass


class CommitteeValidationError(Exception):
    pass


class SealAlreadyDoneError(Exception):
    pass
