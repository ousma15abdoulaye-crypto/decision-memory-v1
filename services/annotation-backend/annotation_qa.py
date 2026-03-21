"""
QA partagée — annotations DMS v3.0.1d
Réconciliation financière élargie + contrôle evidence vs texte source.
Utilisé par backend /predict, export JSONL, scripts/validate_annotation.py
"""

from __future__ import annotations

import re
from typing import Any

# Rôles / taxonomies déclenchant une réconciliation totaux vs lignes
MONETARY_DOCUMENT_ROLES = frozenset(
    {
        "financial_proposal",
        "offer_financial",
        "financial_offer",
        "annex_pricing",
        "financial_proforma",
        "pricing_annex",
    }
)

MONETARY_TAXONOMY_CORE = frozenset(
    {
        "offer_financial",
        "financial_offer",
        "annex_pricing",
    }
)

VALUE_SKIP = frozenset({None, "", "ABSENT", "NOT_APPLICABLE", "AMBIGUOUS"})
EVIDENCE_SKIP = frozenset({None, "", "ABSENT", "NOT_APPLICABLE"})


def _norm_spot(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _digits_compact(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def should_run_financial_reconciliation(annotation: dict) -> bool:
    """True si le document est monétaire ou porte des montants/lignes."""
    routing = annotation.get("couche_1_routing", {})
    if not isinstance(routing, dict):
        return False
    role = routing.get("document_role", "") or ""
    tax = routing.get("taxonomy_core", "") or ""
    if role in MONETARY_DOCUMENT_ROLES or tax in MONETARY_TAXONOMY_CORE:
        return True

    financier = (
        annotation.get("couche_4_atomic", {}) or {}
    ).get("financier", {})
    if not isinstance(financier, dict):
        return False

    items = financier.get("line_items") or []
    if isinstance(items, list) and len(items) > 0:
        return True

    total_raw = financier.get("total_price", {})
    if isinstance(total_raw, dict):
        val = total_raw.get("value")
        if val in (None, "", "ABSENT", "NOT_APPLICABLE"):
            return False
        try:
            float(str(val).replace(" ", "").replace("\u202f", ""))
            return True
        except (ValueError, TypeError):
            return False
    if isinstance(total_raw, int | float):
        return True
    return False


def financial_coherence_warnings(annotation: dict, task_id: int = 0) -> list[str]:
    """
    Compare total_price déclaré à la somme des line_total.
    Retourne une liste de codes ANOMALY (vide si OK ou non applicable).
    """
    warnings: list[str] = []
    if not should_run_financial_reconciliation(annotation):
        return warnings

    financier = annotation.get("couche_4_atomic", {}).get("financier", {})
    if not isinstance(financier, dict):
        return warnings

    total_raw = financier.get("total_price", {})
    line_items = financier.get("line_items", [])

    total_declared: float | None = None
    if isinstance(total_raw, dict):
        try:
            val = total_raw.get("value", 0)
            if val in (None, "", "ABSENT", "NOT_APPLICABLE"):
                return warnings
            s = str(val).replace(" ", "").replace("\u202f", "")
            total_declared = float(s)
        except (ValueError, TypeError):
            return warnings
    elif isinstance(total_raw, int | float):
        total_declared = float(total_raw)

    if not total_declared or not line_items:
        return warnings

    total_computed = sum(
        float(li.get("line_total", 0) or 0) for li in line_items if isinstance(li, dict)
    )

    if total_computed == 0:
        return warnings

    ecart = abs(total_declared - total_computed) / max(total_computed, 1)
    if ecart > 0.01:
        msg = (
            f"ANOMALY_total_price_{int(total_declared)}"
            f"_vs_sum_items_{int(total_computed)}"
        )
        warnings.append(msg)
    return warnings


def _is_fieldvalue_block(d: dict) -> bool:
    return (
        isinstance(d, dict)
        and "value" in d
        and "confidence" in d
        and "evidence" in d
        and "item_line_no" not in d
    )


def _fieldvalue_evidence_violation(fv: dict, source_norm: str, src_digits: str) -> str | None:
    val = fv.get("value")
    ev = fv.get("evidence")

    if isinstance(val, list) and len(val) == 0:
        return None
    if val in VALUE_SKIP:
        return None
    if ev in EVIDENCE_SKIP or (isinstance(ev, str) and not str(ev).strip()):
        if val not in VALUE_SKIP:
            return "evidence_missing_for_non_absent_value"
        return None

    ev_s = str(ev).strip()
    if len(ev_s) < 2:
        return "evidence_too_short"

    en = _norm_spot(ev_s)
    if len(en) >= 3 and en in source_norm:
        return None

    # Montants : au minimum les chiffres du value doivent apparaître dans la source
    str_val = str(val).strip()
    td = _digits_compact(str_val)
    if len(td) >= 3 and td in src_digits:
        return None

    return "evidence_not_substring"


def _line_item_evidence_violation(li: dict, source_norm: str, src_digits: str) -> str | None:
    if not isinstance(li, dict):
        return None
    ev = li.get("evidence", "")
    if ev in EVIDENCE_SKIP or not str(ev).strip():
        return "line_item_evidence_missing"
    en = _norm_spot(str(ev))
    if len(en) >= 3 and en in source_norm:
        return None
    qty = li.get("quantity")
    up = li.get("unit_price")
    lt = li.get("line_total")
    for x in (qty, up, lt):
        if x is not None:
            td = _digits_compact(str(x))
            if len(td) >= 2 and td in src_digits:
                return None
    return "line_item_evidence_not_substring"


def evidence_substring_violations(annotation: dict, source_text: str) -> list[str]:
    """
    Exige que evidence (FieldValue) soit retrouvable dans le texte source normalisé,
    ou pour les nombres que la séquence de chiffres soit présente dans la source.
    """
    violations: list[str] = []
    source_norm = _norm_spot(source_text)
    src_digits = _digits_compact(source_text)

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            if _is_fieldvalue_block(obj):
                v = _fieldvalue_evidence_violation(obj, source_norm, src_digits)
                if v:
                    violations.append(f"{path or 'root'}:{v}")
                return
            if "item_line_no" in obj and "line_total" in obj:
                v = _line_item_evidence_violation(obj, source_norm, src_digits)
                if v:
                    violations.append(f"{path}:line_item:{v}")
                return
            for k, val in obj.items():
                if k == "_meta":
                    continue
                walk(val, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(annotation, "")
    return violations


def apply_financial_warnings_to_annotation(
    annotation: dict, warnings: list[str]
) -> dict:
    """Mutate annotation: append ambiguites + review_required si warnings."""
    if not warnings:
        return annotation
    annotation.setdefault("ambiguites", [])
    for w in warnings:
        if w not in annotation["ambiguites"]:
            annotation["ambiguites"].append(w)
    annotation.setdefault("_meta", {})
    annotation["_meta"]["review_required"] = True
    return annotation
