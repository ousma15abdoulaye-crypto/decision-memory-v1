"""P3.3 — Normalisation commerciale (HT/TTC, niveaux de prix, cohérence)."""

from __future__ import annotations

import re
from typing import Any

from src.core.models import SupplierPackage

from .qualified_price import (
    PriceAmbiguousError,
    PriceLevel,
    QualificationConfidence,
    QualifiedPrice,
    TaxBasis,
)

__all__ = ["qualify_supplier_commercial_price"]

_HT_MARKERS = re.compile(
    r"(?i)\bHT\b|hors\s+taxe|h\.t\.|HTVA|EXCL\.\s*TAX|EXCL\s*TAX|NET\s+HT"
)
_TTC_MARKERS = re.compile(
    r"(?i)\bTTC\b|toutes\s+taxes|t\.t\.c\.|ATI|TVA\s+incluse|taxes\s+comprises"
)
_AMOUNT_RE = re.compile(r"(\d+(?:[\s.,]\d{3})*(?:[.,]\d+)?|\d+(?:\.\d+)?)")


def _normalize_currency(s: str) -> str:
    return s.strip().upper()


def _parse_amount(text: str) -> float | None:
    """Extrait le premier montant positif d'une chaîne prix (legacy M3B)."""
    if not text or not str(text).strip():
        return None
    m = _AMOUNT_RE.search(str(text).replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(",", ".")
    if raw.count(".") > 1:
        parts = raw.split(".")
        raw = "".join(parts[:-1]) + "." + parts[-1]
    try:
        v = float(raw)
    except ValueError:
        return None
    return v


def _detect_tax_basis(text: str) -> TaxBasis | None:
    """Retourne HT, TTC, ou None si aucun signal fiable (pas de devinette)."""
    if not text:
        return None
    ht = bool(_HT_MARKERS.search(text))
    ttc = bool(_TTC_MARKERS.search(text))
    if ht and ttc:
        raise PriceAmbiguousError(
            "Base HT et TTC détectées simultanément sur le même libellé.",
            codes=["HT_TTC_AMBIGUOUS"],
        )
    if ht:
        return TaxBasis.HT
    if ttc:
        return TaxBasis.TTC
    return None


def _line_items_from_extracted(ext: dict[str, Any]) -> list[dict[str, Any]]:
    raw = ext.get("line_items")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _sum_line_totals_ok(lines: list[dict[str, Any]]) -> tuple[float | None, list[str]]:
    """Somme des line_total pour lignes avec line_total_check == OK uniquement."""
    flags: list[str] = []
    total = 0.0
    any_ok = False
    any_anomaly = False
    for li in lines:
        chk = str(li.get("line_total_check") or "")
        lt = li.get("line_total")
        if chk == "ANOMALY":
            any_anomaly = True
        if chk != "OK":
            continue
        if lt is None:
            continue
        try:
            total += float(lt)
            any_ok = True
        except (TypeError, ValueError):
            flags.append("LINE_TOTAL_PARSE_ERROR")
    if any_anomaly and any_ok:
        flags.append("LINE_ITEMS_MIXED_ANOMALY_AND_OK")
    if not any_ok:
        return (None, flags)
    return (total, flags)


def qualify_supplier_commercial_price(
    supplier: SupplierPackage,
    *,
    case_currency: str | None,
) -> QualifiedPrice | None:
    """
    Qualifie un prix « offre » pour le comparatif lowest-price.

    - Pas de fallback HT/TTC implicite : absence de signal explicite → None.
    - Contradictions internes → PriceAmbiguousError.
    - amount <= 0 → None (pas de QualifiedPrice ; pas de zéro cosmétique).
    """
    ext = supplier.extracted_data or {}
    total_price = ext.get("total_price")
    total_src = ext.get("total_price_source") or ""
    text_probe = f"{total_price} {total_src}"

    tax = _detect_tax_basis(text_probe)
    if tax is None:
        return None

    doc_currency = ext.get("currency")
    cur: str | None = None
    flags: list[str] = []
    if doc_currency and str(doc_currency).strip():
        cur = _normalize_currency(str(doc_currency))
    elif case_currency and str(case_currency).strip():
        cur = _normalize_currency(str(case_currency))
        flags.append("CURRENCY_FROM_CASE_DMS")
    else:
        raise PriceAmbiguousError(
            "Devise documentaire absente et devise dossier absente.",
            codes=["CURRENCY_MISSING"],
        )

    if (
        case_currency
        and str(case_currency).strip()
        and doc_currency
        and str(doc_currency).strip()
        and _normalize_currency(str(doc_currency))
        != _normalize_currency(str(case_currency))
    ):
        raise PriceAmbiguousError(
            f"Conflit devise offre ({doc_currency}) vs dossier ({case_currency}).",
            codes=["CURRENCY_MISMATCH"],
        )

    lines = _line_items_from_extracted(ext)
    amount_str = str(total_price) if total_price is not None else ""
    parsed_total = _parse_amount(amount_str) if amount_str else None
    sum_ok, line_flags = _sum_line_totals_ok(lines)
    flags.extend(line_flags)

    chosen: float | None = None
    level = PriceLevel.OFFER_TOTAL

    if sum_ok is not None and parsed_total is not None:
        if sum_ok <= 0 or parsed_total <= 0:
            return None
        rel = abs(sum_ok - parsed_total) / max(parsed_total, 1e-9)
        if rel > 0.01:
            raise PriceAmbiguousError(
                "Somme des lignes OK incompatible avec le total déclaré (>1%).",
                codes=["OFFER_TOTAL_LINE_SUM_MISMATCH"],
            )
        chosen = parsed_total
    elif sum_ok is not None:
        if sum_ok <= 0:
            return None
        chosen = sum_ok
        flags.append("OFFER_TOTAL_FROM_LINE_ITEMS_SUM")
    elif parsed_total is not None:
        if parsed_total <= 0:
            return None
        chosen = parsed_total
    else:
        return None

    src_id: str | None = None
    if supplier.offer_ids:
        src_id = str(supplier.offer_ids[0])

    return QualifiedPrice(
        amount=chosen,
        currency=cur,
        tax_basis=tax,
        price_level=level,
        quantity=None,
        source_document_id=src_id,
        evidence_refs=[str(total_src)] if total_src else [],
        confidence=(
            QualificationConfidence.HIGH
            if not line_flags
            else QualificationConfidence.MEDIUM
        ),
        human_review_required=bool(line_flags),
        flags=flags,
    )
