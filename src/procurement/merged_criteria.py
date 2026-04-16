"""D-005 — vue canonique additive des critères DAO (regroupement métier).

Ne substitue pas les UUID du scoring path (D-003 / D-004). Voir mandat D-005A–K.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.procurement.m14_evaluation_models import DAO_CRITERION_ID_UUID_RE

_COMMERCIAL_FAMILIES = frozenset({"commercial", "financier", "financial", "finance"})


def _norm_spaces_lower(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _norm_famille(row: dict[str, Any]) -> str:
    return _norm_spaces_lower(str(row.get("famille") or "general"))


def _parse_created_at(row: dict[str, Any]) -> datetime | None:
    raw = row.get("created_at")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, str) and raw.strip():
        try:
            t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return t if t.tzinfo else t.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _normalize_tax_basis(raw: str | None) -> str:
    if not raw:
        return "UNKNOWN"
    u = str(raw).strip().upper()
    if u in ("HT", "TTC"):
        return u
    if u in ("UNKNOWN", ""):
        return "UNKNOWN"
    return "UNKNOWN"


def _normalize_amount_scope(raw: str | None) -> str:
    if not raw:
        return "UNKNOWN"
    u = str(raw).strip().upper()
    if u in ("UNIT", "LINE_TOTAL", "OFFER_TOTAL"):
        return u
    if u in ("UNKNOWN", ""):
        return "UNKNOWN"
    # alias explicites mandat / dépôt (sans inférence libre)
    aliases = {
        "PRIX_UNITAIRE": "UNIT",
        "PRIX_UNITAIRE_HT": "UNIT",
        "PRIX_UNITAIRE_TTC": "UNIT",
        "UNIT_PRICE": "UNIT",
        "PRIX_TOTAL_LIGNE": "LINE_TOTAL",
        "LINE_TOTAL": "LINE_TOTAL",
        "MONTANT_GLOBAL": "OFFER_TOTAL",
        "OFFER_TOTAL": "OFFER_TOTAL",
    }
    return aliases.get(u, "UNKNOWN")


def _row_tax_basis(row: dict[str, Any], hint: Mapping[str, Any] | None) -> str:
    if hint and hint.get("tax_basis") is not None:
        return _normalize_tax_basis(str(hint.get("tax_basis")))
    for key in ("tax_basis", "price_basis", "fiscal_basis"):
        if row.get(key) is not None:
            return _normalize_tax_basis(str(row.get(key)))
    return "UNKNOWN"


def _row_amount_scope(row: dict[str, Any], hint: Mapping[str, Any] | None) -> str:
    if hint and hint.get("amount_scope") is not None:
        return _normalize_amount_scope(str(hint.get("amount_scope")))
    for key in ("amount_scope", "commercial_amount_scope", "pricing_grain"):
        if row.get(key) is not None:
            return _normalize_amount_scope(str(row.get(key)))
    return "UNKNOWN"


def _is_commercial_family(fam: str) -> bool:
    return fam in _COMMERCIAL_FAMILIES or any(
        x in fam for x in ("commercial", "financier", "financial")
    )


def _gold_hints_by_dao_id(
    gold_hints: Sequence[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if not gold_hints:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for h in gold_hints:
        rid = str(h.get("dao_criterion_id") or h.get("id") or "").strip()
        if rid and DAO_CRITERION_ID_UUID_RE.match(rid):
            out[rid] = dict(h)
    return out


@dataclass
class MergedCriterion:
    canonical_id: str
    canonical_name: str
    famille: str
    weight_aggregated: float
    is_eliminatory: bool
    source_ids: list[str]
    tax_basis: str = "UNKNOWN"
    amount_scope: str = "UNKNOWN"
    currency: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MergedCriteriaBuildResult:
    merged: list[MergedCriterion]
    warnings: list[str] = field(default_factory=list)

    def to_serializable(self) -> dict[str, Any]:
        return {
            "merged": [m.as_dict() for m in self.merged],
            "warnings": list(self.warnings),
        }


def _eligible_uuid_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if rid and DAO_CRITERION_ID_UUID_RE.match(rid):
            out.append(row)
    return out


def _pick_canonical_id(rows: list[dict[str, Any]]) -> str:
    dated: list[tuple[datetime, str]] = []
    no_date: list[str] = []
    for r in rows:
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        ts = _parse_created_at(r)
        if ts is not None:
            dated.append((ts, rid))
        else:
            no_date.append(rid)
    if dated:
        dated.sort(key=lambda x: (x[0], x[1]))
        return dated[0][1]
    if no_date:
        return min(no_date)
    return str(rows[0].get("id") or "").strip()


def _preflight_commercial_ht_ttc_label_warnings(
    eligible: list[dict[str, Any]],
    hints_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Signale un même libellé commercial avec bases fiscales HT et TTC explicites."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for row in eligible:
        if not _is_commercial_family(_norm_famille(row)):
            continue
        nk = _norm_spaces_lower(str(row.get("critere_nom") or ""))
        if not nk:
            continue
        rid = str(row.get("id") or "").strip()
        tb = _row_tax_basis(row, hints_by_id.get(rid))
        if tb in ("HT", "TTC"):
            by_name[nk].add(tb)
    out: list[str] = []
    for nk, tset in sorted(by_name.items()):
        if "HT" in tset and "TTC" in tset:
            out.append(f"d005_commercial_ht_ttc_same_label:{nk!r}")
    return out


def build_merged_criteria(
    dao_criteria_rows: list[dict[str, Any]],
    gold_hints: Sequence[Mapping[str, Any]] | None = None,
) -> MergedCriteriaBuildResult:
    """Construit la vue D-005 (conservatrice) sans muter ``dao_criteria_rows``."""
    hints_by_id = _gold_hints_by_dao_id(gold_hints)
    eligible = _eligible_uuid_rows(dao_criteria_rows)
    warnings = _preflight_commercial_ht_ttc_label_warnings(eligible, hints_by_id)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}

    for row in eligible:
        fam = _norm_famille(row)
        label = str(row.get("critere_nom") or "").strip()
        name_key = (
            _norm_spaces_lower(label) or f"__unnamed__:{str(row.get('id') or '')}"
        )
        rid = str(row.get("id") or "").strip()
        hint = hints_by_id.get(rid)
        tb = _row_tax_basis(row, hint)
        sc = _row_amount_scope(row, hint)
        if _is_commercial_family(fam):
            key = ("COMMERCIAL", fam, name_key, tb, sc)
        else:
            key = ("OTHER", fam, name_key)
        groups.setdefault(key, []).append(row)

    merged: list[MergedCriterion] = []
    for _key, members in sorted(groups.items(), key=lambda kv: kv[0]):
        if len(members) == 1:
            merged.append(_singleton_from_row(members[0], hints_by_id))
            continue
        fams = {_norm_famille(m) for m in members}
        names = {_norm_spaces_lower(str(m.get("critere_nom") or "")) for m in members}
        names.discard("")
        if len(fams) > 1 or len(names) > 1:
            warnings.append(
                "d005_defensive_split heterogeneous_group "
                f"ids={[str(m.get('id')) for m in members]}"
            )
            for m in members:
                merged.append(_singleton_from_row(m, hints_by_id))
            continue
        merged.append(_merged_group(members, hints_by_id))

    merged.sort(key=lambda m: m.canonical_id)
    return MergedCriteriaBuildResult(merged=merged, warnings=list(warnings))


def _singleton_from_row(
    row: dict[str, Any],
    hints_by_id: dict[str, dict[str, Any]],
) -> MergedCriterion:
    rid = str(row.get("id") or "").strip()
    hint = hints_by_id.get(rid)
    fam = _norm_famille(row)
    label = str(row.get("critere_nom") or "").strip() or rid
    w = float(row.get("ponderation") or 0.0)
    elim = bool(row.get("is_eliminatory"))
    tb = _row_tax_basis(row, hint)
    sc = _row_amount_scope(row, hint)
    cur = row.get("currency")
    cur_s = str(cur).strip() if cur is not None and str(cur).strip() else None
    return MergedCriterion(
        canonical_id=rid,
        canonical_name=label,
        famille=fam,
        weight_aggregated=w,
        is_eliminatory=elim,
        source_ids=[rid],
        tax_basis=tb,
        amount_scope=sc,
        currency=cur_s,
    )


def _merged_group(
    members: list[dict[str, Any]],
    hints_by_id: dict[str, dict[str, Any]],
) -> MergedCriterion:
    cid = _pick_canonical_id(members)
    canon_row = next(
        (m for m in members if str(m.get("id") or "").strip() == cid), members[0]
    )
    label = str(canon_row.get("critere_nom") or "").strip() or cid
    fam = _norm_famille(canon_row)
    wsum = sum(float(m.get("ponderation") or 0.0) for m in members)
    elim = any(bool(m.get("is_eliminatory")) for m in members)
    sids = sorted(
        {str(m.get("id") or "").strip() for m in members},
        key=lambda x: x.lower(),
    )
    rid0 = str(canon_row.get("id") or "").strip()
    hint0 = hints_by_id.get(rid0)
    tb = _row_tax_basis(canon_row, hint0)
    sc = _row_amount_scope(canon_row, hint0)
    cur_s: str | None = None
    for m in members:
        cur = m.get("currency")
        if cur is not None and str(cur).strip():
            cur_s = str(cur).strip()
            break
    return MergedCriterion(
        canonical_id=cid,
        canonical_name=label,
        famille=fam,
        weight_aggregated=wsum,
        is_eliminatory=elim,
        source_ids=sids,
        tax_basis=tb,
        amount_scope=sc,
        currency=cur_s,
    )


def build_merged_criteria_result(
    dao_criteria_rows: list[dict[str, Any]],
    gold_hints: Sequence[Mapping[str, Any]] | None = None,
) -> MergedCriteriaBuildResult:
    """API stable pour le pipeline — copie défensive des lignes."""
    rows_copy = [dict(r) for r in dao_criteria_rows]
    return build_merged_criteria(rows_copy, gold_hints=gold_hints)
