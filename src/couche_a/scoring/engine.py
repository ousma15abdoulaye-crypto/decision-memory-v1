"""
M3B Scoring Engine - Constitution V3 Compliant.

Non-prescriptive: Scores are factual calculations to assist decision-making.
Human validation required (is_validated=False by default).
No automatic vendor ranking or recommendations.
"""

import json
import re
from datetime import datetime

from sqlalchemy import text

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.models import EliminationResult, ScoreResult
from src.db import get_connection
from src.db.connection import get_db_cursor

__all__ = ["ScoringEngine"]

_DEFAULT_WEIGHTS: dict[str, float] = {
    "commercial": 0.50,
    "capacity": 0.30,
    "sustainability": 0.10,
    "essentials": 0.10,
}

_SCORING_VERSION = "V3.3.2"


def _get_case_currency(conn, case_id: str | None) -> tuple[str, bool, str | None]:
    """Read cases.currency from DB (ADR-0010 D2).

    Returns (currency, is_fallback, fallback_reason).
    Fallback 'XOF' only if case_id absent or row not found.
    Caller MUST record is_fallback + fallback_reason in scoring_meta.
    """
    if not case_id:
        return "XOF", True, "case_id absent"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT currency FROM public.cases WHERE id = %s",
            (case_id,),
        )
        row = cur.fetchone()
    if not row:
        return "XOF", True, f"case '{case_id}' not found in public.cases"
    return row["currency"], False, None


def _load_weights(conn, profile_code: str | None) -> tuple[dict[str, float], bool]:
    """Load scoring weights from scoring_configs (ADR-0010 D2).

    Returns (weights_dict, is_fallback).
    is_fallback=True means profile absent -> caller MUST trace in scoring_meta.
    """
    if not profile_code:
        return _DEFAULT_WEIGHTS.copy(), True

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT commercial_weight, capacity_weight,
                   sustainability_weight, essentials_weight
            FROM public.scoring_configs
            WHERE profile_code = %s
            LIMIT 1
            """,
            (profile_code,),
        )
        row = cur.fetchone()

    if not row:
        return _DEFAULT_WEIGHTS.copy(), True

    return {
        "commercial": float(row["commercial_weight"]),
        "capacity": float(row["capacity_weight"]),
        "sustainability": float(row["sustainability_weight"]),
        "essentials": float(row["essentials_weight"]),
    }, False


class ScoringEngine:
    """
    Scoring engine for supplier evaluation.

    Constitution V3 §5 Invariant 4: Non-prescriptive.
    Scores = factual calculations, not decisions.
    """

    def __init__(
        self,
        commercial_method: str = "price_lowest_100",
        capacity_method: str = "capacity_experience",
        sustainability_method: str = "sustainability_certifications",
    ):
        self.commercial_method = commercial_method
        self.capacity_method = capacity_method
        self.sustainability_method = sustainability_method

    def calculate_scores_for_case(
        self,
        case_id: str,
        suppliers: list[SupplierPackage],
        criteria: list[DAOCriterion],
        profile_code: str = "GENERIC",
    ) -> tuple[list[ScoreResult], list[EliminationResult]]:
        """
        Calculate scores for all suppliers in a case.

        Returns:
            (scores, eliminations) tuple
        """
        # 0. Read currency + weights from DB (ADR-0010 D2 -- no hardcode)
        with get_db_cursor() as cur:
            conn = cur.connection
            currency, currency_is_fallback, currency_fallback_reason = (
                _get_case_currency(conn, case_id)
            )
            weights, is_fallback = _load_weights(conn, profile_code)

        scoring_meta = {
            "fallback": is_fallback,
            "fallback_reason": (
                f"profile '{profile_code}' not found in scoring_configs"
                if is_fallback
                else None
            ),
            "fallback_weights": _DEFAULT_WEIGHTS if is_fallback else None,
            "profile_used": "hardcoded" if is_fallback else profile_code,
            "scoring_version": _SCORING_VERSION,
            "currency": currency,
            "currency_is_fallback": currency_is_fallback,
            "currency_fallback_reason": currency_fallback_reason,
        }

        # 1. Check eliminatory criteria first
        eliminations = self._check_eliminatory_criteria(suppliers, criteria)

        # Filter eliminated suppliers
        eliminated_names = {e.supplier_name for e in eliminations}
        active_suppliers = [
            s for s in suppliers if s.supplier_name not in eliminated_names
        ]

        if not active_suppliers:
            return ([], eliminations)

        # 2. Calculate profile from criteria
        profile = self._build_evaluation_profile(criteria)

        # 3. Calculate category scores
        commercial_scores = self._calculate_commercial_scores(
            active_suppliers, profile, currency=currency
        )
        capacity_scores = self._calculate_capacity_scores(active_suppliers, profile)
        sustainability_scores = self._calculate_sustainability_scores(
            active_suppliers, profile
        )
        essentials_scores = self._calculate_essentials_scores(active_suppliers, profile)

        # 4. Calculate total weighted scores
        all_category_scores = (
            commercial_scores
            + capacity_scores
            + sustainability_scores
            + essentials_scores
        )
        total_scores = self._calculate_total_scores(
            active_suppliers,
            all_category_scores,
            profile,
            weights=weights,
            scoring_meta=scoring_meta,
        )

        # 5. Combine all scores
        all_scores = all_category_scores + total_scores

        # 6. Save to database
        self._save_scores_to_db(case_id, all_scores)
        self.save_eliminations_to_db(case_id, eliminations)

        return (all_scores, eliminations)

    def _build_evaluation_profile(self, criteria: list[DAOCriterion]) -> dict:
        """Build evaluation profile from criteria."""
        profile = {"criteria": []}

        for criterion in criteria:
            profile["criteria"].append(
                {
                    "category": criterion.categorie,
                    "weight": (
                        criterion.ponderation / 100.0 if criterion.ponderation else 0.0
                    ),
                    "eliminatory": criterion.seuil_elimination is not None,
                }
            )

        return profile

    def _calculate_commercial_scores(
        self,
        suppliers: list[SupplierPackage],
        profile: dict,
        currency: str | None = None,
    ) -> list[ScoreResult]:
        """Calculate commercial scores (price-based).

        currency must come from cases.currency (ADR-0010 D2) -- never hardcoded.
        If not provided, falls back to _get_case_currency(None, None) -> 'XOF'.
        """
        effective_currency = (
            currency if currency is not None else _get_case_currency(None, None)[0]
        )
        scores = []

        # Extract prices
        prices = []
        for supplier in suppliers:
            price_str = supplier.extracted_data.get("total_price", "")
            match = re.search(r"(\d+(?:\.\d+)?)", price_str)
            if match:
                prices.append((supplier.supplier_name, float(match.group(1))))

        if not prices:
            # No prices available
            for supplier in suppliers:
                scores.append(
                    ScoreResult(
                        supplier_name=supplier.supplier_name,
                        category="commercial",
                        score_value=0.0,
                        calculation_method=self.commercial_method,
                        calculation_details={
                            "error": "Aucun prix disponible",
                            "currency": effective_currency,
                        },
                    )
                )
            return scores

        # Find lowest price
        lowest_price = min(price for _, price in prices)

        # Calculate scores: (lowest_price / supplier_price) * 100
        for supplier_name, price in prices:
            score_value = (lowest_price / price) * 100.0
            scores.append(
                ScoreResult(
                    supplier_name=supplier_name,
                    category="commercial",
                    score_value=round(score_value, 2),
                    calculation_method=self.commercial_method,
                    calculation_details={
                        "price": price,
                        "lowest_price": lowest_price,
                        "currency": effective_currency,
                    },
                )
            )

        return scores

    def _calculate_capacity_scores(
        self, suppliers: list[SupplierPackage], profile: dict
    ) -> list[ScoreResult]:
        """Calculate capacity scores (experience-based)."""
        scores = []

        for supplier in suppliers:
            refs = supplier.extracted_data.get("technical_refs", [])
            refs_count = len(refs) if isinstance(refs, list) else 0

            # Score: 20 points per reference, max 100
            score_value = min(refs_count * 20.0, 100.0)

            scores.append(
                ScoreResult(
                    supplier_name=supplier.supplier_name,
                    category="capacity",
                    score_value=score_value,
                    calculation_method=self.capacity_method,
                    calculation_details={
                        "technical_references_count": refs_count,
                        "references": refs[:5] if isinstance(refs, list) else [],
                    },
                )
            )

        return scores

    def _calculate_sustainability_scores(
        self, suppliers: list[SupplierPackage], profile: dict
    ) -> list[ScoreResult]:
        """Calculate sustainability scores (certifications/keywords)."""
        scores = []

        keywords = [
            "environnement",
            "rse",
            "iso 14001",
            "durable",
            "écologique",
            "responsabilité sociale",
            "certification",
            "engagement",
        ]

        for supplier in suppliers:
            # Search in documents
            found_keywords = []
            for doc in supplier.documents:
                doc_lower = doc.lower()
                for keyword in keywords:
                    if keyword in doc_lower and keyword not in found_keywords:
                        found_keywords.append(keyword)

            # Score: 10 points per keyword found, max 100
            score_value = min(len(found_keywords) * 10.0, 100.0)

            scores.append(
                ScoreResult(
                    supplier_name=supplier.supplier_name,
                    category="sustainability",
                    score_value=score_value,
                    calculation_method=self.sustainability_method,
                    calculation_details={
                        "found_keywords": found_keywords,
                        "keywords_count": len(found_keywords),
                    },
                )
            )

        return scores

    def _calculate_essentials_scores(
        self, suppliers: list[SupplierPackage], profile: dict
    ) -> list[ScoreResult]:
        """Calculate essentials scores (completeness check)."""
        scores = []

        for supplier in suppliers:
            # Score based on package completeness
            score_value = 100.0 if supplier.package_status == "COMPLETE" else 0.0

            scores.append(
                ScoreResult(
                    supplier_name=supplier.supplier_name,
                    category="essentials",
                    score_value=score_value,
                    calculation_method="elimination_check",
                    calculation_details={
                        "package_status": supplier.package_status,
                        "missing_fields": supplier.missing_fields,
                    },
                )
            )

        return scores

    def _calculate_total_scores(
        self,
        suppliers: list[SupplierPackage],
        category_scores: list[ScoreResult],
        profile: dict,
        weights: dict[str, float] | None = None,
        scoring_meta: dict | None = None,
    ) -> list[ScoreResult]:
        """Calculate weighted total scores.

        weights and scoring_meta come from _load_weights() via calculate_scores_for_case.
        scoring_meta is always present in calculation_details (INV-9 traceability).
        """
        total_scores = []

        # Use weights from DB (via _load_weights) or fall back to defaults
        effective_weights = weights if weights is not None else _DEFAULT_WEIGHTS.copy()

        # Per-criterion profile overrides apply only when no DB weights provided (legacy path)
        if weights is None:
            for criterion in profile.get("criteria", []):
                category = criterion.get("category")
                weight = criterion.get("weight", 0.0)
                if category and category in effective_weights:
                    effective_weights[category] = weight

        # Calculate for each supplier
        for supplier in suppliers:
            supplier_scores = {
                s.category: s.score_value
                for s in category_scores
                if s.supplier_name == supplier.supplier_name
            }

            # Weighted sum
            total = sum(
                supplier_scores.get(cat, 0.0) * weight
                for cat, weight in effective_weights.items()
            )

            total_scores.append(
                ScoreResult(
                    supplier_name=supplier.supplier_name,
                    category="total",
                    score_value=round(total, 2),
                    calculation_method="weighted_sum",
                    calculation_details={
                        "weights": effective_weights,
                        "category_scores": supplier_scores,
                        "scoring_meta": scoring_meta or {},
                    },
                )
            )

        return total_scores

    def _check_eliminatory_criteria(
        self, suppliers: list[SupplierPackage], criteria: list[DAOCriterion]
    ) -> list[EliminationResult]:
        """Check eliminatory criteria and return eliminations."""
        eliminations = []

        eliminatory_criteria = [c for c in criteria if c.seuil_elimination is not None]

        for supplier in suppliers:
            for criterion in eliminatory_criteria:
                # Check if supplier meets criterion
                if not self._meets_criterion(supplier, criterion):
                    eliminations.append(
                        EliminationResult(
                            supplier_name=supplier.supplier_name,
                            criterion_id=f"crit_{criterion.ordre_affichage}",
                            criterion_name=criterion.critere_nom,
                            criterion_category=criterion.categorie,
                            failure_reason=f"Ne satisfait pas: {criterion.description}",
                            eliminated_at=datetime.utcnow(),
                        )
                    )

        return eliminations

    def _meets_criterion(
        self, supplier: SupplierPackage, criterion: DAOCriterion
    ) -> bool:
        """Check if supplier meets an eliminatory criterion.

        Called only for criteria where seuil_elimination is not None.
        Logic is based on proven SupplierPackage fields (documents availability).
        Defensive: missing data yields False (elimination).
        """
        cat = (criterion.categorie or "").lower()

        if cat == "commercial":
            return supplier.has_financial
        if cat in ("capacity", "capacite", "technique"):
            return supplier.has_technical
        if cat in ("admin", "administratif"):
            return supplier.has_admin
        if cat == "essentials":
            return supplier.package_status == "COMPLETE"
        # Unknown category: eliminate if any required fields are missing
        return not bool(supplier.missing_fields)

    def _save_scores_to_db(self, case_id: str, scores: list[ScoreResult]) -> None:
        """Save scores to database (append-only via score_runs — ADR-0006/INV-6)."""
        with get_connection() as conn:
            for score in scores:
                details_json = (
                    json.dumps(score.calculation_details)
                    if isinstance(score.calculation_details, dict)
                    else str(score.calculation_details)
                )
                conn.execute(
                    text("""
                        INSERT INTO public.score_runs (
                            case_id, supplier_name, category,
                            score_value, calculation_details
                        ) VALUES (
                            :case_id, :supplier_name, :category,
                            :score_value, CAST(:details AS jsonb)
                        )
                    """),
                    {
                        "case_id": case_id,
                        "supplier_name": score.supplier_name,
                        "category": score.category,
                        "score_value": float(score.score_value),
                        "details": details_json,
                    },
                )
            conn.commit()

    def save_eliminations_to_db(
        self, case_id: str, eliminations: list[EliminationResult]
    ) -> None:
        """Save eliminations to database (grouped by supplier, JSONB)."""
        if not eliminations:
            return

        by_supplier: dict = {}
        for elim in eliminations:
            sn = elim.supplier_name
            if sn not in by_supplier:
                by_supplier[sn] = []
            by_supplier[sn].append(elim)

        with get_connection() as conn:
            for supplier_name, group in by_supplier.items():
                reason_codes = [
                    {
                        "criterion_id": e.criterion_id,
                        "criterion_name": e.criterion_name,
                        "category": e.criterion_category,
                    }
                    for e in group
                ]
                details = {
                    "eliminations": [
                        {
                            "criterion_id": e.criterion_id,
                            "failure_reason": e.failure_reason,
                            "eliminated_at": (
                                e.eliminated_at.isoformat()
                                if hasattr(e.eliminated_at, "isoformat")
                                else str(e.eliminated_at)
                            ),
                        }
                        for e in group
                    ]
                }
                conn.execute(
                    text("""
                        INSERT INTO supplier_eliminations (case_id, supplier_name, reason_codes, details)
                        VALUES (:case_id, :supplier_name, CAST(:reason_codes AS jsonb), CAST(:details AS jsonb))
                    """),
                    {
                        "case_id": case_id,
                        "supplier_name": supplier_name,
                        "reason_codes": json.dumps(reason_codes),
                        "details": json.dumps(details),
                    },
                )
            conn.commit()
