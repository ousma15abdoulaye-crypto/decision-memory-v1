"""Couche A – SQLAlchemy models for procurement case management."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.system.db import Base

__all__ = [
    "Case",
    "Lot",
    "Submission",
    "SubmissionDocument",
    "PreanalysisResult",
    "CBAExport",
    "MinutesPV",
    "OutboxEvent",
    "PVType",
    "OutboxStatus",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- Enums ------------------------------------------------------------------

class PVType(str, enum.Enum):
    opening = "opening"
    analysis = "analysis"


class OutboxStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"


# ---- Models -----------------------------------------------------------------

class Case(Base):
    __tablename__ = "cases"

    reference: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    buyer_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    lots: Mapped[list["Lot"]] = relationship(back_populates="case", lazy="selectin")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="case", lazy="selectin")


class Lot(Base):
    __tablename__ = "lots"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    case: Mapped["Case"] = relationship(back_populates="lots")


class Submission(Base):
    __tablename__ = "submissions"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    declared_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), default="upload")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    case: Mapped["Case"] = relationship(back_populates="submissions")
    documents: Mapped[list["SubmissionDocument"]] = relationship(back_populates="submission", lazy="selectin")

    __table_args__ = (
        Index("ix_submissions_case_lot", "case_id", "lot_id"),
    )


class SubmissionDocument(Base):
    __tablename__ = "submission_documents"

    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    doc_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(default=_utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="documents")


class PreanalysisResult(Base):
    __tablename__ = "preanalysis_results"

    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("submission_documents.id"), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submission_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detected_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    doc_checklist: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class CBAExport(Base):
    __tablename__ = "cba_exports"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(1000))
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class MinutesPV(Base):
    __tablename__ = "minutes_pv"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    pv_type: Mapped[PVType] = mapped_column(Enum(PVType))
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(1000))
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus), default=OutboxStatus.pending, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
