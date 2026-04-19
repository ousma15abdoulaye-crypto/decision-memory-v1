"""
P3.4 E2 — Projection moteur (M14 + gate P3.1B) vers ``MatrixRow`` / ``MatrixSummary``.

Lit ``OfferEvaluation`` et ``GateOutput`` sans couplage structurel sur les modèles
M14 (mandat A2). Les scores famille hors M14 utilisent des conventions de flags
documentées dans ``decisions/p34_e2_matrix_builder.md``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid5

from src.core.models import DAOCriterion
from src.procurement.eligibility_models import GateOutput
from src.procurement.m14_evaluation_models import OfferEvaluation
from src.procurement.matrix_models import (
    CohortComparabilityStatus,
    ComparabilityStatus,
    EligibilityStatus,
    MatrixRow,
    MatrixRowExplainability,
    MatrixSummary,
    RankStatus,
    StatusOrigin,
    TechnicalThresholdMode,
)

_STATUS_CHAIN: list[str] = [
    "eligibility.P3.1B",
    "technical.P3.2",
    "commercial.P3.3",
    "sustainability.P3.2",
    "rank.P3.4",
]

_NS_BUNDLE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_NS_WORKSPACE = UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

_FLAG_COMMERCIAL = "DMS_MATRIX_COMMERCIAL_SCORE="
_FLAG_SUSTAINABILITY = "DMS_MATRIX_SUSTAINABILITY_SCORE="
_FLAG_DEFAULT_TECH = "TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED"
_FLAG_COHORT_COMM = "COHORT_ASYMMETRIC_COMMERCIAL"
_FLAG_COHORT_SUST = "COHORT_PARTIAL_SUSTAINABILITY"
_FLAG_NO_COMP = "NO_COMPARABLE_CANDIDATE"
_FLAG_INFORMATIVE_BELOW = "TECHNICAL_INFORMATIVE_BELOW_THRESHOLD"

_PRICE_AMBIGUOUS_MARKERS = frozenset(
    {
        "p33_price_ambiguous",
        "P33_PRICE_AMBIGUOUS",
        "PRICE_AMBIGUOUS",
    }
)

_COMMERCIAL_SCORE_RE = re.compile(
    rf"^{re.escape(_FLAG_COMMERCIAL)}(?P<val>.+)$", re.IGNORECASE
)
_SUST_SCORE_RE = re.compile(
    rf"^{re.escape(_FLAG_SUSTAINABILITY)}(?P<val>.+)$", re.IGNORECASE
)


def _workspace_uuid(raw: str) -> UUID:
    s = (raw or "").strip()
    try:
        return UUID(s)
    except ValueError:
        return uuid5(_NS_WORKSPACE, f"dms:workspace:{s}")


def _bundle_uuid(offer_document_id: str) -> UUID:
    s = (offer_document_id or "").strip()
    try:
        return UUID(s)
    except ValueError:
        return uuid5(_NS_BUNDLE, f"dms:bundle:{s}")


def _price_ambiguous(oe: OfferEvaluation) -> bool:
    return any(fl in _PRICE_AMBIGUOUS_MARKERS for fl in oe.flags)


def _parse_flag_value(flags: list[str], pattern: re.Pattern[str]) -> float | None:
    for fl in flags:
        m = pattern.match(fl.strip())
        if not m:
            continue
        raw = (m.group("val") or "").strip()
        if raw.upper() in ("NULL", "NONE", ""):
            return None
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _commercial_score_system(oe: OfferEvaluation) -> float | None:
    if _price_ambiguous(oe):
        return None
    v = _parse_flag_value(oe.flags, _COMMERCIAL_SCORE_RE)
    if v is not None:
        return v
    return None


def _sustainability_score_system(oe: OfferEvaluation) -> float | None:
    return _parse_flag_value(oe.flags, _SUST_SCORE_RE)


def _technical_score_system(oe: OfferEvaluation) -> float | None:
    ts = oe.technical_score
    if ts is None:
        return None
    return ts.total_weighted_score


def _technical_threshold_value(
    oe: OfferEvaluation, cfg: dict | None
) -> float | None:
    ts = oe.technical_score
    if ts is not None and ts.technical_threshold is not None:
        return ts.technical_threshold
    if cfg:
        v = cfg.get("default_threshold_value")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
    return None


def _technical_mode_and_warnings(
    technical_threshold_config: dict | None,
) -> tuple[TechnicalThresholdMode, list[str], StatusOrigin]:
    if not technical_threshold_config:
        return TechnicalThresholdMode.MANDATORY, [_FLAG_DEFAULT_TECH], StatusOrigin.DEFAULT_APPLIED
    raw = technical_threshold_config.get("threshold_mode")
    if raw is None:
        raw = technical_threshold_config.get("mode")
    if raw is None:
        return TechnicalThresholdMode.MANDATORY, [_FLAG_DEFAULT_TECH], StatusOrigin.DEFAULT_APPLIED
    try:
        return TechnicalThresholdMode(str(raw).upper()), [], StatusOrigin.PIPELINE_SYSTEM
    except ValueError:
        return TechnicalThresholdMode.MANDATORY, [_FLAG_DEFAULT_TECH], StatusOrigin.DEFAULT_APPLIED


def _eligibility_status(vendor_id: str, gate: GateOutput) -> EligibilityStatus:
    if vendor_id in gate.excluded_vendor_ids:
        return EligibilityStatus.INELIGIBLE
    if vendor_id in gate.eligible_vendor_ids:
        return EligibilityStatus.ELIGIBLE
    if vendor_id in gate.pending_vendor_ids:
        ver = gate.verdicts.get(vendor_id)
        if ver is not None and ver.dominant_cause == "PENDING_REGULARIZATION_OR_REVIEW":
            return EligibilityStatus.REGULARIZATION_PENDING
        return EligibilityStatus.PENDING
    return EligibilityStatus.PENDING


def _total_comparability(
    elig: EligibilityStatus,
    tech: float | None,
    comm: float | None,
    sust: float | None,
) -> ComparabilityStatus:
    if elig == EligibilityStatus.INELIGIBLE:
        return ComparabilityStatus.NON_COMPARABLE
    if tech is None or comm is None:
        return ComparabilityStatus.NON_COMPARABLE
    if sust is None:
        return ComparabilityStatus.INCOMPLETE
    return ComparabilityStatus.COMPARABLE


def _total_score_system(
    elig: EligibilityStatus,
    tech: float | None,
    comm: float | None,
    sust: float | None,
) -> float | None:
    if elig == EligibilityStatus.INELIGIBLE:
        return None
    if tech is None or comm is None or sust is None:
        return None
    return tech + comm + sust


def _is_rankable(row: MatrixRow) -> bool:
    if row.eligibility_status != EligibilityStatus.ELIGIBLE:
        return False
    if row.technical_threshold_mode == TechnicalThresholdMode.MANDATORY:
        return bool(row.technical_qualified)
    return True


def _explainability_for(
    *,
    elig: EligibilityStatus,
    rank_status: RankStatus,
    tech: float | None,
    comm: float | None,
    sust: float | None,
    exclusion_codes: list[str],
    warning_flags: list[str],
) -> MatrixRowExplainability:
    chain = list(_STATUS_CHAIN)
    primary = "P3.4:RANKED"
    if elig == EligibilityStatus.INELIGIBLE:
        primary = "P3.1B:INELIGIBLE"
    elif elig in (EligibilityStatus.PENDING, EligibilityStatus.REGULARIZATION_PENDING):
        primary = "P3.1B:PENDING"
    elif rank_status == RankStatus.EXCLUDED and elig == EligibilityStatus.ELIGIBLE:
        primary = "P3.2:UNQUALIFIED_TECHNICAL"
    elif _FLAG_COHORT_COMM in warning_flags:
        primary = "P3.4:COHORT_ASYMMETRIC_COMMERCIAL"
    elif rank_status == RankStatus.NOT_COMPARABLE:
        primary = "P3.3:NOT_COMPARABLE"
    elif rank_status == RankStatus.INCOMPLETE:
        primary = "P3.2:SUSTAINABILITY_INCOMPLETE"
    elif rank_status == RankStatus.RANKED:
        primary = "P3.4:RANKED"

    score_breakdown: dict[str, object] = {
        "technical": {"system": tech},
        "commercial": {"system": comm},
        "sustainability": {"system": sust},
    }
    exclusion_path: list[str] | None
    if rank_status in (RankStatus.EXCLUDED, RankStatus.NOT_COMPARABLE, RankStatus.INCOMPLETE):
        exclusion_path = list(exclusion_codes) if exclusion_codes else [primary]
    elif elig == EligibilityStatus.INELIGIBLE:
        exclusion_path = list(exclusion_codes) if exclusion_codes else [primary]
    else:
        exclusion_path = None

    return MatrixRowExplainability(
        status_chain=chain,
        primary_status_source=primary,
        score_breakdown=score_breakdown,
        exclusion_path=exclusion_path,
    )


def _apply_ranking(rows: list[MatrixRow]) -> list[MatrixRow]:
    """Applique P5.3 (R1–R9) sur une copie défensive des lignes."""
    out: list[MatrixRow] = []
    for base in rows:
        wf = list(base.warning_flags)
        elig = base.eligibility_status
        if elig == EligibilityStatus.INELIGIBLE:
            out.append(
                base.model_copy(
                    update={
                        "rank": None,
                        "rank_status": RankStatus.EXCLUDED,
                        "warning_flags": wf,
                    }
                )
            )
            continue
        if elig in (EligibilityStatus.PENDING, EligibilityStatus.REGULARIZATION_PENDING):
            out.append(
                base.model_copy(
                    update={
                        "rank": None,
                        "rank_status": RankStatus.PENDING,
                        "warning_flags": wf,
                    }
                )
            )
            continue
        if (
            base.technical_threshold_mode == TechnicalThresholdMode.MANDATORY
            and base.technical_qualified is False
        ):
            out.append(
                base.model_copy(
                    update={
                        "rank": None,
                        "rank_status": RankStatus.EXCLUDED,
                        "warning_flags": wf,
                    }
                )
            )
            continue
        out.append(base.model_copy(update={"warning_flags": wf}))

    rankable_idx = [i for i, r in enumerate(out) if _is_rankable(r)]
    rankable = [out[i] for i in rankable_idx]

    has_comm_null = any(r.commercial_score_system is None for r in rankable)
    has_comm_ok = any(r.commercial_score_system is not None for r in rankable)
    asymmetric_commercial = has_comm_null and has_comm_ok

    has_sust_null = any(r.sustainability_score_system is None for r in rankable)
    has_sust_ok = any(r.sustainability_score_system is not None for r in rankable)
    partial_sustainability = has_sust_null and has_sust_ok

    if asymmetric_commercial:
        for i in rankable_idx:
            r = out[i]
            w = list(r.warning_flags)
            if _FLAG_COHORT_COMM not in w:
                w.append(_FLAG_COHORT_COMM)
            out[i] = r.model_copy(
                update={"rank": None, "rank_status": RankStatus.NOT_COMPARABLE, "warning_flags": w}
            )
        return out

    if partial_sustainability:
        wflag = _FLAG_COHORT_SUST
        for i in rankable_idx:
            r = out[i]
            w = list(r.warning_flags)
            if wflag not in w:
                w.append(wflag)
            if r.sustainability_score_system is None:
                out[i] = r.model_copy(
                    update={"rank": None, "rank_status": RankStatus.INCOMPLETE, "warning_flags": w}
                )
            else:
                out[i] = r.model_copy(update={"warning_flags": w})
        ranked_sub = [
            (i, out[i])
            for i in rankable_idx
            if out[i].sustainability_score_system is not None
            and out[i].total_score_system is not None
        ]
        ranked_sub.sort(key=lambda t: t[1].total_score_system or 0.0, reverse=True)
        for place, (i, _) in enumerate(ranked_sub, start=1):
            r = out[i]
            w = list(r.warning_flags)
            out[i] = r.model_copy(
                update={"rank": place, "rank_status": RankStatus.RANKED, "warning_flags": w}
            )
        return out

    if any(r.commercial_score_system is None for r in rankable):
        for i in rankable_idx:
            r = out[i]
            out[i] = r.model_copy(update={"rank": None, "rank_status": RankStatus.NOT_COMPARABLE})
        return out

    if any(r.sustainability_score_system is None for r in rankable):
        for i in rankable_idx:
            r = out[i]
            out[i] = r.model_copy(update={"rank": None, "rank_status": RankStatus.INCOMPLETE})
        return out

    ranked_sub = sorted(
        rankable_idx,
        key=lambda i: out[i].total_score_system or 0.0,
        reverse=True,
    )
    for place, i in enumerate(ranked_sub, start=1):
        r = out[i]
        out[i] = r.model_copy(update={"rank": place, "rank_status": RankStatus.RANKED})
    return out


def _attach_explainability(rows: list[MatrixRow]) -> list[MatrixRow]:
    rebuilt: list[MatrixRow] = []
    for r in rows:
        ex = _explainability_for(
            elig=r.eligibility_status,
            rank_status=r.rank_status,
            tech=r.technical_score_system,
            comm=r.commercial_score_system,
            sust=r.sustainability_score_system,
            exclusion_codes=r.exclusion_reason_codes,
            warning_flags=r.warning_flags,
        )
        rebuilt.append(r.model_copy(update={"explainability": ex}))
    return rebuilt


def build_matrix_rows(
    workspace_id: UUID,
    pipeline_run_id: UUID,
    offer_evaluations: list[OfferEvaluation],
    gate_output: GateOutput,
    dao_criteria: list[DAOCriterion],
    technical_threshold_config: dict | None = None,
) -> list[MatrixRow]:
    _ = sum((c.ponderation for c in dao_criteria), 0.0)
    mode, mode_warnings, mode_origin = _technical_mode_and_warnings(technical_threshold_config)
    rows: list[MatrixRow] = []

    for oe in offer_evaluations:
        vid = str(oe.offer_document_id).strip()
        bundle_id = _bundle_uuid(vid)
        elig = _eligibility_status(vid, gate_output)
        tech = _technical_score_system(oe)
        comm = _commercial_score_system(oe)
        sust = _sustainability_score_system(oe)
        tcomp = _total_comparability(elig, tech, comm, sust)
        total = _total_score_system(elig, tech, comm, sust)

        ts = oe.technical_score
        tech_qualified = ts.passes_threshold if ts is not None else None
        thr_val = _technical_threshold_value(oe, technical_threshold_config)

        if (
            elig == EligibilityStatus.ELIGIBLE
            and mode == TechnicalThresholdMode.MANDATORY
            and tech_qualified is False
        ):
            tcomp = ComparabilityStatus.NON_COMPARABLE

        wf: list[str] = list(mode_warnings)
        origin = mode_origin if mode_warnings else StatusOrigin.PIPELINE_SYSTEM

        elig_codes: list[str] = []
        if elig == EligibilityStatus.INELIGIBLE:
            ver = gate_output.verdicts.get(vid)
            if ver is not None and ver.failing_criteria:
                elig_codes = [f"P3.1B:FAIL:{c}" for c in ver.failing_criteria]
            else:
                elig_codes = ["P3.1B:INELIGIBLE"]

        if elig == EligibilityStatus.INELIGIBLE:
            row_mode = TechnicalThresholdMode.MANDATORY
            row_thr = None
            row_qualified = None
        else:
            row_mode = mode
            row_thr = thr_val
            row_qualified = tech_qualified

        human_rev = bool(oe.flags) and any(
            fl.upper().startswith("HUMAN_REVIEW") for fl in oe.flags
        )

        if (
            elig == EligibilityStatus.ELIGIBLE
            and mode == TechnicalThresholdMode.INFORMATIVE
            and tech_qualified is False
        ):
            if _FLAG_INFORMATIVE_BELOW not in wf:
                wf.append(_FLAG_INFORMATIVE_BELOW)

        if elig == EligibilityStatus.INELIGIBLE:
            init_rank_status = RankStatus.EXCLUDED
        elif elig in (EligibilityStatus.PENDING, EligibilityStatus.REGULARIZATION_PENDING):
            init_rank_status = RankStatus.PENDING
        elif (
            row_mode == TechnicalThresholdMode.MANDATORY
            and row_qualified is False
            and elig == EligibilityStatus.ELIGIBLE
        ):
            init_rank_status = RankStatus.EXCLUDED
        else:
            init_rank_status = RankStatus.PENDING

        row = MatrixRow(
            workspace_id=workspace_id,
            bundle_id=bundle_id,
            supplier_name=(oe.supplier_name or vid).strip() or vid,
            pipeline_run_id=pipeline_run_id,
            eligibility_status=elig,
            eligibility_reason_codes=elig_codes,
            technical_threshold_mode=row_mode,
            technical_threshold_value=row_thr,
            technical_qualified=row_qualified,
            technical_score_system=None if elig == EligibilityStatus.INELIGIBLE else tech,
            commercial_score_system=None if elig == EligibilityStatus.INELIGIBLE else comm,
            sustainability_score_system=None if elig == EligibilityStatus.INELIGIBLE else sust,
            total_score_system=None if elig == EligibilityStatus.INELIGIBLE else total,
            total_comparability_status=tcomp,
            rank=None,
            rank_status=init_rank_status,
            exclusion_reason_codes=list(elig_codes),
            warning_flags=wf,
            human_review_required=human_rev,
            status_origin=origin,
        )
        rows.append(row)

    ranked = _apply_ranking(rows)
    return _attach_explainability(ranked)


def _cohort_comparability(rows: list[MatrixRow]) -> tuple[CohortComparabilityStatus, list[str]]:
    ce = sum(1 for r in rows if r.eligibility_status == EligibilityStatus.ELIGIBLE)
    ci = sum(1 for r in rows if r.eligibility_status == EligibilityStatus.INELIGIBLE)
    cp = sum(1 for r in rows if r.eligibility_status == EligibilityStatus.PENDING)
    cr = sum(1 for r in rows if r.eligibility_status == EligibilityStatus.REGULARIZATION_PENDING)

    cc_e = sum(
        1
        for r in rows
        if r.eligibility_status == EligibilityStatus.ELIGIBLE
        and r.total_comparability_status == ComparabilityStatus.COMPARABLE
    )
    nc_e = sum(
        1
        for r in rows
        if r.eligibility_status == EligibilityStatus.ELIGIBLE
        and r.total_comparability_status == ComparabilityStatus.NON_COMPARABLE
    )
    inc_e = sum(
        1
        for r in rows
        if r.eligibility_status == EligibilityStatus.ELIGIBLE
        and r.total_comparability_status == ComparabilityStatus.INCOMPLETE
    )

    if ce == 0:
        return CohortComparabilityStatus.NOT_COMPARABLE, [_FLAG_NO_COMP]

    fully_eligible_cohort = (ce == len(rows)) and cp == 0 and cr == 0 and ci == 0
    if fully_eligible_cohort and cc_e == ce and nc_e == 0 and inc_e == 0:
        return CohortComparabilityStatus.FULLY_COMPARABLE, []

    if cc_e >= 1 and (nc_e >= 1 or inc_e >= 1 or not fully_eligible_cohort):
        return CohortComparabilityStatus.PARTIALLY_COMPARABLE, []

    if cc_e == 0 and nc_e >= 1:
        return CohortComparabilityStatus.NOT_COMPARABLE, []

    if inc_e >= 1:
        return CohortComparabilityStatus.PARTIALLY_COMPARABLE, []

    return CohortComparabilityStatus.NOT_COMPARABLE, [_FLAG_NO_COMP]


def build_matrix_summary(
    matrix_rows: list[MatrixRow],
    workspace_id: UUID,
    pipeline_run_id: UUID,
) -> MatrixSummary:
    rev_id = matrix_rows[0].matrix_revision_id if matrix_rows else pipeline_run_id
    now = datetime.now(UTC)

    total_bundles = len(matrix_rows)
    count_eligible = sum(1 for r in matrix_rows if r.eligibility_status == EligibilityStatus.ELIGIBLE)
    count_ineligible = sum(
        1 for r in matrix_rows if r.eligibility_status == EligibilityStatus.INELIGIBLE
    )
    count_pending = sum(1 for r in matrix_rows if r.eligibility_status == EligibilityStatus.PENDING)
    count_regularization_pending = sum(
        1 for r in matrix_rows if r.eligibility_status == EligibilityStatus.REGULARIZATION_PENDING
    )

    count_comparable = sum(
        1 for r in matrix_rows if r.total_comparability_status == ComparabilityStatus.COMPARABLE
    )
    count_non_comparable = sum(
        1 for r in matrix_rows if r.total_comparability_status == ComparabilityStatus.NON_COMPARABLE
    )
    count_incomplete = sum(
        1 for r in matrix_rows if r.total_comparability_status == ComparabilityStatus.INCOMPLETE
    )

    count_ranked = sum(1 for r in matrix_rows if r.rank_status == RankStatus.RANKED)
    count_excluded = sum(1 for r in matrix_rows if r.rank_status == RankStatus.EXCLUDED)
    count_pending_rank = sum(1 for r in matrix_rows if r.rank_status == RankStatus.PENDING)
    count_not_comparable_rank = sum(
        1 for r in matrix_rows if r.rank_status == RankStatus.NOT_COMPARABLE
    )
    count_incomplete_rank = sum(1 for r in matrix_rows if r.rank_status == RankStatus.INCOMPLETE)

    cohort_status, cohort_flags = _cohort_comparability(matrix_rows)

    crit_flags: dict[str, int] = {}
    for r in matrix_rows:
        for fl in r.warning_flags:
            crit_flags[fl] = crit_flags.get(fl, 0) + 1
    for fl in cohort_flags:
        crit_flags[fl] = crit_flags.get(fl, 0) + 1

    human_n = sum(1 for r in matrix_rows if r.human_review_required)

    essential_criteria_total = 0
    essential_criteria_passed = 0
    essential_criteria_failed = 0
    essential_criteria_pending = 0

    return MatrixSummary(
        workspace_id=workspace_id,
        pipeline_run_id=pipeline_run_id,
        matrix_revision_id=rev_id,
        computed_at=now,
        total_bundles=total_bundles,
        count_eligible=count_eligible,
        count_ineligible=count_ineligible,
        count_pending=count_pending,
        count_regularization_pending=count_regularization_pending,
        count_comparable=count_comparable,
        count_non_comparable=count_non_comparable,
        count_incomplete=count_incomplete,
        count_ranked=count_ranked,
        count_excluded=count_excluded,
        count_pending_rank=count_pending_rank,
        count_not_comparable_rank=count_not_comparable_rank,
        count_incomplete_rank=count_incomplete_rank,
        cohort_comparability_status=cohort_status,
        has_any_critical_flag=bool(crit_flags),
        critical_flags_overview=crit_flags,
        human_review_required_count=human_n,
        count_rows_with_override=sum(1 for r in matrix_rows if r.has_any_override),
        override_summary_by_reason={},
        essential_criteria_total=essential_criteria_total,
        essential_criteria_passed=essential_criteria_passed,
        essential_criteria_failed=essential_criteria_failed,
        essential_criteria_pending=essential_criteria_pending,
    )


__all__ = ["build_matrix_rows", "build_matrix_summary"]
