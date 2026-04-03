"""
eval_against_golden.py — Evaluate DMS agent tools against golden dataset.

Usage: python scripts/eval_against_golden.py [--cases-dir data/golden/cases]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.agents.tools.regulatory_tools import build_default_manifest


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case: dict, expected: dict, manifest) -> dict:
    """Run tools on case and compare to expected. Returns result dict."""
    case_id = case["case_id"]
    results: dict = {"case_id": case_id, "checks": [], "passed": 0, "failed": 0}

    # 1. resolve_regime
    regime = manifest.invoke(
        "resolve_regime",
        framework=case["framework"],
        procurement_family=case["procurement_family"],
        estimated_value=case.get("estimated_value"),
        currency=case.get("currency", "XOF"),
    )

    # Check framework
    expected_fw = expected.get("expected_framework")
    if expected_fw:
        ok = regime["framework"] == expected_fw
        results["checks"].append(
            {"check": "framework", "expected": expected_fw, "got": regime["framework"], "pass": ok}
        )
        results["passed" if ok else "failed"] += 1

    # Check procedure type
    expected_proc = expected.get("expected_procedure_type_in")
    if expected_proc:
        ok = regime["procedure_type"] in expected_proc
        results["checks"].append(
            {
                "check": "procedure_type",
                "expected_in": expected_proc,
                "got": regime["procedure_type"],
                "pass": ok,
            }
        )
        results["passed" if ok else "failed"] += 1

    # 2. map_principles (needs instantiate_requirements first)
    try:
        reqs = manifest.invoke("instantiate_requirements", regime_dict=regime)
        principles = manifest.invoke(
            "map_principles", regime_dict=regime, requirements_dict=reqs
        )

        expected_count = expected.get("expected_principles_count")
        if expected_count:
            count = len(principles.get("principles", []))
            ok = count == expected_count
            results["checks"].append(
                {"check": "principles_count", "expected": expected_count, "got": count, "pass": ok}
            )
            results["passed" if ok else "failed"] += 1

        expected_sus = expected.get("expected_sustainability_present")
        if expected_sus is not None:
            names = [p["principle"] for p in principles.get("principles", [])]
            has_sus = "sustainability" in names
            ok = has_sus == expected_sus
            results["checks"].append(
                {"check": "sustainability_present", "expected": expected_sus, "got": has_sus, "pass": ok}
            )
            results["passed" if ok else "failed"] += 1
    except Exception as e:
        results["checks"].append(
            {"check": "principles_pipeline", "error": str(e), "pass": False}
        )
        results["failed"] += 1

    # 3. Benchmark status
    try:
        bench = manifest.invoke("get_benchmark_status")
        ok = "status" in bench and "transition_proposal" in bench
        results["checks"].append({"check": "benchmark_status", "pass": ok})
        results["passed" if ok else "failed"] += 1
    except Exception as e:
        results["checks"].append(
            {"check": "benchmark_status", "error": str(e), "pass": False}
        )
        results["failed"] += 1

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate golden dataset")
    parser.add_argument("--cases-dir", default="data/golden/cases")
    parser.add_argument("--expected-dir", default="data/golden/expected")
    args = parser.parse_args()

    cases_dir = REPO_ROOT / args.cases_dir
    expected_dir = REPO_ROOT / args.expected_dir

    if not cases_dir.exists():
        print(f"STOP: {cases_dir} not found")
        sys.exit(1)

    manifest = build_default_manifest()
    print(f"Tool manifest: {manifest.count()} tools registered")
    print(f"Cases directory: {cases_dir}")
    print()

    case_files = sorted(cases_dir.glob("case_*.json"))
    total_pass = 0
    total_fail = 0
    total_cases = 0

    for cf in case_files:
        case = load_json(cf)
        case_id = case["case_id"]
        expected_file = expected_dir / f"{cf.stem}_expected.json"
        if not expected_file.exists():
            print(f"  SKIP {case_id} — no expected file")
            continue

        expected = load_json(expected_file)
        result = evaluate_case(case, expected, manifest)
        total_cases += 1
        total_pass += result["passed"]
        total_fail += result["failed"]

        status = "PASS" if result["failed"] == 0 else "FAIL"
        print(f"  [{status}] {case_id}: {result['passed']} pass, {result['failed']} fail")
        for c in result["checks"]:
            marker = "v" if c["pass"] else "X"
            detail = ""
            if "expected" in c:
                detail = f" expected={c['expected']} got={c.get('got', '?')}"
            elif "expected_in" in c:
                detail = f" expected_in={c['expected_in']} got={c.get('got', '?')}"
            elif "error" in c:
                detail = f" error={c['error']}"
            print(f"    [{marker}] {c['check']}{detail}")

    print()
    print(f"=== SUMMARY: {total_cases} cases, {total_pass} pass, {total_fail} fail ===")
    accuracy = total_pass / (total_pass + total_fail) if (total_pass + total_fail) > 0 else 0
    print(f"Accuracy: {accuracy:.1%}")
    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
