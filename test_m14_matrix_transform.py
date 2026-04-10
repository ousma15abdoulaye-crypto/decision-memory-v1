"""Test transformation EvaluationReport → assessment_matrix."""

from src.procurement.m14_evaluation_repository import _build_assessment_matrix_from_report

# Mock EvaluationReport payload
mock_payload = {
    "case_id": "test-case-123",
    "evaluation_method": "mieux_disant",
    "offer_evaluations": [
        {
            "offer_document_id": "bundle-uuid-001",
            "supplier_name": "Supplier A",
            "is_eligible": True,
            "technical_score": {
                "criteria_scores": [
                    {
                        "criteria_name": "criterion_tech_1",
                        "awarded_score": 18.5,
                        "max_score": 20.0,
                        "justification": "Bonne qualité technique",
                        "confidence": 0.8,
                    },
                    {
                        "criteria_name": "criterion_tech_2",
                        "awarded_score": 15.0,
                        "max_score": 20.0,
                        "justification": "Conforme aux spécifications",
                        "confidence": 0.6,
                    },
                ],
                "total_weighted_score": 33.5,
                "confidence": 0.8,
            },
            "eligibility_results": [
                {
                    "check_id": "eligibility_financial",
                    "check_name": "Capacité financière",
                    "result": "PASS",
                    "is_eliminatory": True,
                    "confidence": 1.0,
                }
            ],
            "price_analysis": {
                "total_price_declared": 125000.0,
                "currency": "XOF",
                "confidence": 0.8,
            },
        },
        {
            "offer_document_id": "bundle-uuid-002",
            "supplier_name": "Supplier B",
            "is_eligible": False,
            "technical_score": {
                "criteria_scores": [
                    {
                        "criteria_name": "criterion_tech_1",
                        "awarded_score": 12.0,
                        "max_score": 20.0,
                        "justification": "Qualité insuffisante",
                        "confidence": 0.6,
                    },
                ],
            },
            "eligibility_results": [
                {
                    "check_id": "eligibility_financial",
                    "check_name": "Capacité financière",
                    "result": "FAIL",
                    "is_eliminatory": True,
                    "confidence": 1.0,
                }
            ],
        },
    ],
}

# Test transformation
print("=== TEST TRANSFORMATION M14 -> ASSESSMENT MATRIX ===\n")

matrix = _build_assessment_matrix_from_report(mock_payload)

print(f"Bundles détectés: {len(matrix)}")
print(f"IDs bundles: {list(matrix.keys())}\n")

for bundle_id, criteria in matrix.items():
    print(f"[{bundle_id}] - {len(criteria)} critères")
    for crit_key, cell_data in criteria.items():
        score = cell_data.get("score")
        max_score = cell_data.get("max_score")
        conf = cell_data.get("confidence")
        source = cell_data.get("source")
        print(f"  • {crit_key}: score={score}/{max_score}, confidence={conf}, source={source}")
    print()

# Vérifications
assert len(matrix) == 2, f"Expected 2 bundles, got {len(matrix)}"
assert "bundle-uuid-001" in matrix, "bundle-uuid-001 missing"
assert "bundle-uuid-002" in matrix, "bundle-uuid-002 missing"

bundle1 = matrix["bundle-uuid-001"]
assert "criterion_tech_1" in bundle1, "criterion_tech_1 missing in bundle1"
assert bundle1["criterion_tech_1"]["score"] == 18.5, "Wrong score for criterion_tech_1"
assert bundle1["criterion_tech_1"]["source"] == "m14", "Wrong source"
assert "eligibility_financial" in bundle1, "eligibility check missing"
assert bundle1["eligibility_financial"]["score"] == 1.0, "PASS should be 1.0"
assert "price_total" in bundle1, "price_total missing"

bundle2 = matrix["bundle-uuid-002"]
assert "eligibility_financial" in bundle2, "eligibility check missing in bundle2"
assert bundle2["eligibility_financial"]["score"] == 0.0, "FAIL should be 0.0"

print("[OK] TOUS LES TESTS PASSES\n")
print("[OK] MATRICE COMPATIBLE M16 BRIDGE")
