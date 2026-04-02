"""M14 — EvaluationEngine (déterministe, ADR-M14-001).

Consomme H2 (AtomicCapabilitySkeleton), H3 (MarketContextSignal),
RH1 (ComplianceChecklist), RH2 (EvaluationBlueprint) et ProcessLinking
pour produire un EvaluationReport par dossier (case).

RÈGLE-09 : aucun winner / rank / recommendation / offre_retenue.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.procurement.m14_evaluation_models import (
    CompletionAnalysis,
    EligibilityCheckResult,
    EvaluationMeta,
    EvaluationReport,
    M14EvaluationInput,
    OfferEvaluation,
    PriceAnalysis,
    TechnicalCriterionScore,
    TechnicalScore,
)

logger = logging.getLogger(__name__)


def _discretize_m14(raw: float) -> float:
    if raw >= 0.9:
        return 1.0
    if raw >= 0.7:
        return 0.8
    return 0.6


class EvaluationEngine:
    """Moteur d'évaluation comparative M14 — déterministe."""

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository

    def evaluate(self, inp: M14EvaluationInput) -> EvaluationReport:
        blueprint = inp.rh2_evaluation_blueprint or {}
        checklist = inp.rh1_compliance_checklist or {}
        h2 = inp.h2_capability_skeleton or {}
        h3 = inp.h3_market_context or {}

        eval_method = blueprint.get("evaluation_method", "unknown")
        if eval_method not in (
            "lowest_price",
            "mieux_disant",
            "quality_cost_based",
            "fixed_budget",
            "consultant_qualification",
            "unknown",
        ):
            eval_method = "unknown"

        review_reasons: list[str] = []
        scoring_review = False

        offer_evals: list[OfferEvaluation] = []
        for offer in inp.offers:
            oe = self._evaluate_offer(offer, h2, h3, checklist, blueprint)
            offer_evals.append(oe)

        case_checks = self._run_case_level_checks(checklist)

        eligible_count = sum(1 for o in offer_evals if o.is_eligible is True)

        if h2.get("scoring_structure") and isinstance(h2["scoring_structure"], dict):
            pc = h2["scoring_structure"].get("ponderation_coherence", "NOT_FOUND")
            if pc not in ("OK",):
                scoring_review = True
                review_reasons.append(f"scoring_structure.ponderation_coherence={pc}")

        if not inp.offers:
            review_reasons.append("no_offers_provided")

        report = EvaluationReport(
            case_id=inp.case_id,
            evaluation_method=eval_method,
            source_rules_document_id=inp.source_rules_document_id,
            offer_evaluations=offer_evals,
            case_level_checks=case_checks,
            total_offers_evaluated=len(offer_evals),
            eligible_offers_count=eligible_count,
            blueprint_ref=blueprint.get("procedure_requirements_ref"),
            m14_meta=EvaluationMeta(
                processing_timestamp=datetime.now(UTC).isoformat(),
                evaluation_method=eval_method,
                scoring_review_required=scoring_review,
                review_reasons=review_reasons,
            ),
        )

        if self.repository is not None:
            self.repository.save_evaluation(
                case_id=inp.case_id,
                payload=report.model_dump(mode="json"),
            )

        return report

    def _evaluate_offer(
        self,
        offer: dict[str, Any],
        h2: dict[str, Any],
        h3: dict[str, Any],
        checklist: dict[str, Any],
        blueprint: dict[str, Any],
    ) -> OfferEvaluation:
        doc_id = offer.get("document_id", "unknown")
        supplier = offer.get("supplier_name")
        role = offer.get("process_role")

        eligibility = self._run_eligibility_checks(offer, checklist)
        is_eligible = (
            all(
                r.result in ("PASS", "NOT_APPLICABLE", "INDETERMINATE")
                for r in eligibility
            )
            if eligibility
            else None
        )

        completion = self._check_completion(offer, h2)
        tech_score = self._compute_technical_score(offer, h2, blueprint)
        price = self._analyze_price(offer, h3)

        per_offer_compliance = self._run_per_offer_compliance(offer, checklist)

        flags: list[str] = []
        if price and price.currency_mismatch_alert:
            flags.append("CURRENCY_MISMATCH")
        if tech_score and tech_score.ponderation_coherence != "OK":
            flags.append(f"PONDERATION_{tech_score.ponderation_coherence}")
        if completion and completion.completeness_ratio < 0.5:
            flags.append("LOW_COMPLETENESS")

        return OfferEvaluation(
            offer_document_id=doc_id,
            supplier_name=supplier,
            process_role=role,
            eligibility_results=eligibility,
            is_eligible=is_eligible,
            completion_analysis=completion,
            technical_score=tech_score,
            price_analysis=price,
            compliance_results=per_offer_compliance,
            flags=flags,
            overall_confidence=_discretize_m14(0.6),
        )

    def _run_eligibility_checks(
        self, offer: dict[str, Any], checklist: dict[str, Any]
    ) -> list[EligibilityCheckResult]:
        results: list[EligibilityCheckResult] = []
        per_offer = checklist.get("per_offer_checks", [])
        for check in per_offer:
            if not isinstance(check, dict):
                continue
            if not check.get("is_eliminatory", False):
                continue
            result = self._execute_single_check(check, offer)
            results.append(result)
        return results

    def _run_per_offer_compliance(
        self, offer: dict[str, Any], checklist: dict[str, Any]
    ) -> list[EligibilityCheckResult]:
        results: list[EligibilityCheckResult] = []
        per_offer = checklist.get("per_offer_checks", [])
        for check in per_offer:
            if not isinstance(check, dict):
                continue
            if check.get("is_eliminatory", False):
                continue
            result = self._execute_single_check(check, offer)
            results.append(result)
        return results

    def _run_case_level_checks(
        self, checklist: dict[str, Any]
    ) -> list[EligibilityCheckResult]:
        results: list[EligibilityCheckResult] = []
        case_checks = checklist.get("case_level_checks", [])
        for check in case_checks:
            if not isinstance(check, dict):
                continue
            results.append(
                EligibilityCheckResult(
                    check_id=check.get("check_id", ""),
                    check_name=check.get("check_name", ""),
                    result="INDETERMINATE",
                    is_eliminatory=check.get("is_eliminatory", False),
                    evidence=["case_level_check_requires_human_review"],
                    confidence=0.6,
                )
            )
        return results

    def _execute_single_check(
        self, check: dict[str, Any], offer: dict[str, Any]
    ) -> EligibilityCheckResult:
        method = check.get("verification_method", "manual_review")
        check_id = check.get("check_id", "")
        check_name = check.get("check_name", "")
        is_elim = check.get("is_eliminatory", False)

        if method == "document_presence":
            expected = check.get("expected_admin_subtype", "")
            present_docs = offer.get("present_admin_subtypes", [])
            if expected and expected in present_docs:
                return EligibilityCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    result="PASS",
                    is_eliminatory=is_elim,
                    evidence=[f"document_{expected}_present"],
                    confidence=0.8,
                )
            if expected:
                return EligibilityCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    result="FAIL" if is_elim else "INDETERMINATE",
                    is_eliminatory=is_elim,
                    evidence=[f"document_{expected}_missing"],
                    confidence=0.8,
                )

        return EligibilityCheckResult(
            check_id=check_id,
            check_name=check_name,
            result="INDETERMINATE",
            is_eliminatory=is_elim,
            evidence=[f"verification_method_{method}_not_automated"],
            confidence=0.6,
        )

    def _check_completion(
        self, offer: dict[str, Any], h2: dict[str, Any]
    ) -> CompletionAnalysis | None:
        active = h2.get("active_capability_sections", [])
        if not active:
            return None

        present_raw = offer.get("capability_sections_present", [])
        active_set = set(active)
        present_in_active = list(
            dict.fromkeys(s for s in present_raw if s in active_set)
        )
        missing = [s for s in active if s not in present_in_active]
        ratio = len(present_in_active) / len(active) if active else 0.0

        return CompletionAnalysis(
            expected_sections=active,
            present_sections=present_in_active,
            missing_sections=missing,
            completeness_ratio=round(ratio, 3),
            confidence=_discretize_m14(0.7),
        )

    def _compute_technical_score(
        self,
        offer: dict[str, Any],
        h2: dict[str, Any],
        blueprint: dict[str, Any],
    ) -> TechnicalScore | None:
        scoring = h2.get("scoring_structure")
        if not scoring or not isinstance(scoring, dict):
            return None

        criteria = scoring.get("criteria", [])
        if not criteria:
            return None

        pc = scoring.get("ponderation_coherence", "NOT_FOUND")
        threshold_raw = blueprint.get("technical_threshold") or scoring.get(
            "technical_threshold"
        )
        threshold = None
        if threshold_raw is not None:
            try:
                threshold = float(threshold_raw)
            except (ValueError, TypeError):
                pass

        scores: list[TechnicalCriterionScore] = []
        total_weighted_score: float | None = None
        for c in criteria:
            if not isinstance(c, dict):
                continue
            name = c.get("criteria_name", "")
            weight = c.get("weight_percent")
            max_s = c.get("max_score")
            awarded = c.get("awarded_score")
            scores.append(
                TechnicalCriterionScore(
                    criteria_name=name,
                    weight_percent=weight,
                    max_score=max_s,
                    awarded_score=awarded,
                    justification="scoring_requires_human_evaluation",
                    confidence=0.6,
                )
            )
            try:
                awarded_val = float(awarded)
            except (ValueError, TypeError):
                continue
            if total_weighted_score is None:
                total_weighted_score = 0.0
            try:
                weight_val = float(weight)
            except (ValueError, TypeError):
                total_weighted_score += awarded_val
            else:
                total_weighted_score += awarded_val * (weight_val / 100.0)

        passes = None
        if threshold is not None and total_weighted_score is not None:
            passes = total_weighted_score >= threshold

        return TechnicalScore(
            criteria_scores=scores,
            total_weighted_score=total_weighted_score,
            technical_threshold=threshold,
            passes_threshold=passes,
            ponderation_coherence=(
                pc
                if pc in ("OK", "INCOHERENT", "INCOMPLETE", "NOT_FOUND")
                else "NOT_FOUND"
            ),
            confidence=0.6,
        )

    def _analyze_price(
        self, offer: dict[str, Any], h3: dict[str, Any]
    ) -> PriceAnalysis | None:
        if not h3:
            return None

        h3_currency = h3.get("currency_detected")
        offer_currency = offer.get("currency")
        mismatch = False
        if h3_currency and offer_currency and h3_currency != offer_currency:
            mismatch = True

        anomalies: list[str] = []
        if h3.get("material_price_index_applicable"):
            anomalies.append("MERCURIALE_CHECK_REQUIRED")

        return PriceAnalysis(
            total_price_declared=offer.get("total_price"),
            currency=offer_currency,
            price_basis=h3.get("price_basis_detected"),
            currency_mismatch_alert=mismatch,
            mercuriale_comparison_available=h3.get(
                "material_price_index_applicable", False
            ),
            material_categories_checked=h3.get("material_categories_detected", []),
            price_anomaly_flags=anomalies,
            zone_for_reference=h3.get("zone_for_price_reference", []),
            confidence=_discretize_m14(0.7),
        )
