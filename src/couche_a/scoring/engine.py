"""
M3B Scoring Engine - Constitution V3 Compliant.

Non-prescriptive: Scores are factual calculations to assist decision-making.
Human validation required (is_validated=False by default).
No automatic vendor ranking or recommendations.
"""

from typing import List, Tuple
from datetime import datetime
import json
import re

from sqlalchemy import text

from src.couche_a.scoring.models import EliminationResult, ScoreResult
from src.core.models import DAOCriterion, SupplierPackage
from src.db import get_connection

__all__ = ["ScoringEngine"]


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
        suppliers: List[SupplierPackage],
        criteria: List[DAOCriterion],
    ) -> Tuple[List[ScoreResult], List[EliminationResult]]:
        """
        Calculate scores for all suppliers in a case.

        Returns:
            (scores, eliminations) tuple
        """
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
        commercial_scores = self._calculate_commercial_scores(active_suppliers, profile)
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
            active_suppliers, all_category_scores, profile
        )

        # 5. Combine all scores
        all_scores = all_category_scores + total_scores

        # 6. Save to database
        self._save_scores_to_db(case_id, all_scores)
        self.save_eliminations_to_db(case_id, eliminations)

        return (all_scores, eliminations)

    def _build_evaluation_profile(self, criteria: List[DAOCriterion]) -> dict:
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
        self, suppliers: List[SupplierPackage], profile: dict
    ) -> List[ScoreResult]:
        """Calculate commercial scores (price-based)."""
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
                        calculation_details={"error": "Aucun prix disponible"},
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
                        "currency": "XOF",
                    },
                )
            )

        return scores

    def _calculate_capacity_scores(
        self, suppliers: List[SupplierPackage], profile: dict
    ) -> List[ScoreResult]:
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
        self, suppliers: List[SupplierPackage], profile: dict
    ) -> List[ScoreResult]:
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
        self, suppliers: List[SupplierPackage], profile: dict
    ) -> List[ScoreResult]:
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
        suppliers: List[SupplierPackage],
        category_scores: List[ScoreResult],
        profile: dict,
    ) -> List[ScoreResult]:
        """Calculate weighted total scores."""
        total_scores = []

        # Get weights from profile
        weights = {
            "commercial": 0.50,
            "capacity": 0.30,
            "sustainability": 0.10,
            "essentials": 0.10,
        }

        # Override with profile if available
        for criterion in profile.get("criteria", []):
            category = criterion.get("category")
            weight = criterion.get("weight", 0.0)
            if category and category in weights:
                weights[category] = weight

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
                for cat, weight in weights.items()
            )

            total_scores.append(
                ScoreResult(
                    supplier_name=supplier.supplier_name,
                    category="total",
                    score_value=round(total, 2),
                    calculation_method="weighted_sum",
                    calculation_details={
                        "weights": weights,
                        "category_scores": supplier_scores,
                    },
                )
            )

        return total_scores

    def _check_eliminatory_criteria(
        self, suppliers: List[SupplierPackage], criteria: List[DAOCriterion]
    ) -> List[EliminationResult]:
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
        """Check if supplier meets a criterion (stub for now)."""
        # TODO: Implement actual criterion checking logic
        # For now, assume all suppliers meet criteria (no eliminations)
        return True

    def _save_scores_to_db(self, case_id: str, scores: List[ScoreResult]) -> None:
        """Save scores to database."""
        with get_connection() as conn:
            for score in scores:
                conn.execute(
                    text("""
                        INSERT INTO supplier_scores (
                            case_id, supplier_name, category, score_value,
                            calculation_method, calculation_details, is_validated
                        ) VALUES (
                            :case_id, :supplier_name, :category, :score_value,
                            :method, CAST(:details AS jsonb), :validated
                        )
                        ON CONFLICT (case_id, supplier_name, category)
                        DO UPDATE SET
                            score_value = EXCLUDED.score_value,
                            calculation_details = EXCLUDED.calculation_details,
                            created_at = NOW()
                    """),
                    {
                        "case_id": case_id,
                        "supplier_name": score.supplier_name,
                        "category": score.category,
                        "score_value": float(score.score_value),
                        "method": score.calculation_method,
                        "details": json.dumps(score.calculation_details) if isinstance(score.calculation_details, dict) else str(score.calculation_details),
                        "validated": bool(score.is_validated),
                    },
                )
            conn.commit()

    def save_eliminations_to_db(
        self, case_id: str, eliminations: List[EliminationResult]
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
                    {"criterion_id": e.criterion_id, "criterion_name": e.criterion_name, "category": e.criterion_category}
                    for e in group
                ]
                details = {
                    "eliminations": [
                        {"criterion_id": e.criterion_id, "failure_reason": e.failure_reason, "eliminated_at": (e.eliminated_at.isoformat() if hasattr(e.eliminated_at, "isoformat") else str(e.eliminated_at))}
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
