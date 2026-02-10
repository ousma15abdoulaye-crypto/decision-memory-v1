"""Couche B – SQLAlchemy models for market intelligence & referential data."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.system.db import Base

__all__ = [
    "Vendor",
    "VendorAlias",
    "VendorEvent",
    "Item",
    "ItemAlias",
    "Unit",
    "UnitAlias",
    "GeoMaster",
    "GeoAlias",
    "MarketSignal",
    "GeoType",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- Enums ------------------------------------------------------------------

class GeoType(str, enum.Enum):
    country = "country"
    region = "region"
    city = "city"


# ---- Vendor -----------------------------------------------------------------

class Vendor(Base):
    __tablename__ = "vendors"

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    aliases: Mapped[list["VendorAlias"]] = relationship(back_populates="vendor", lazy="selectin")
    events: Mapped[list["VendorEvent"]] = relationship(back_populates="vendor", lazy="selectin")


class VendorAlias(Base):
    __tablename__ = "vendor_aliases"

    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    vendor: Mapped["Vendor"] = relationship(back_populates="aliases")


class VendorEvent(Base):
    __tablename__ = "vendor_events"

    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    vendor: Mapped["Vendor"] = relationship(back_populates="events")


# ---- Item -------------------------------------------------------------------

class Item(Base):
    __tablename__ = "items"

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    aliases: Mapped[list["ItemAlias"]] = relationship(back_populates="item", lazy="selectin")


class ItemAlias(Base):
    __tablename__ = "item_aliases"

    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    item: Mapped["Item"] = relationship(back_populates="aliases")


# ---- Unit -------------------------------------------------------------------

class Unit(Base):
    __tablename__ = "units"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    aliases: Mapped[list["UnitAlias"]] = relationship(back_populates="unit", lazy="selectin")


class UnitAlias(Base):
    __tablename__ = "unit_aliases"

    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"), index=True)
    alias: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    unit: Mapped["Unit"] = relationship(back_populates="aliases")


# ---- Geography --------------------------------------------------------------

class GeoMaster(Base):
    __tablename__ = "geo_master"

    name: Mapped[str] = mapped_column(String(255), index=True)
    geo_type: Mapped[GeoType] = mapped_column(Enum(GeoType), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("geo_master.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    aliases: Mapped[list["GeoAlias"]] = relationship(back_populates="geo", lazy="selectin")


class GeoAlias(Base):
    __tablename__ = "geo_aliases"

    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_master.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    geo: Mapped["GeoMaster"] = relationship(back_populates="aliases")


# ---- Market Signal (append-only) --------------------------------------------

class MarketSignal(Base):
    __tablename__ = "market_signals"

    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    geo_id: Mapped[str | None] = mapped_column(ForeignKey("geo_master.id"), nullable=True, index=True)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="XOF")
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    case_reference: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    superseded_by: Mapped[str | None] = mapped_column(
        ForeignKey("market_signals.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    __table_args__ = (
        Index("ix_market_signals_item_geo", "item_id", "geo_id"),
        Index("ix_market_signals_vendor_item", "vendor_id", "item_id"),
    )
