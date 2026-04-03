"""Tests — Regulatory tool wrappers (deterministic, no LLM needed)."""

from __future__ import annotations

from src.agents.tools.regulatory_tools import (
    ANALYZE_CLAUSE_DESCRIPTOR,
    ASSEMBLE_GATES_DESCRIPTOR,
    ASSESS_COMPLEX_DEROGATION_DESCRIPTOR,
    ASSESS_DEROGATIONS_DESCRIPTOR,
    BENCHMARK_STATUS_DESCRIPTOR,
    INSTANTIATE_REQUIREMENTS_DESCRIPTOR,
    MAP_PRINCIPLES_DESCRIPTOR,
    RESOLVE_REGIME_DESCRIPTOR,
    analyze_clause,
    assess_complex_derogation,
    build_default_manifest,
    get_benchmark_status,
    resolve_regime,
)
from src.agents.tools.tool_manifest import ToolCategory

# ── Manifest build ──────────────────────────────────────────────


class TestBuildDefaultManifest:
    def test_count_at_least_6(self) -> None:
        manifest = build_default_manifest()
        assert manifest.count() >= 6

    def test_all_tools_registered(self) -> None:
        manifest = build_default_manifest()
        names = {t.name for t in manifest.list_tools()}
        expected = {
            "resolve_regime",
            "instantiate_requirements",
            "assemble_compliance_gates",
            "assess_derogations",
            "map_principles",
            "get_benchmark_status",
            "analyze_clause",
            "assess_complex_derogation",
        }
        assert expected.issubset(names)

    def test_deterministic_tools_count(self) -> None:
        manifest = build_default_manifest()
        det = manifest.list_tools(deterministic_only=True)
        assert len(det) >= 6

    def test_llm_tools_have_review_required(self) -> None:
        manifest = build_default_manifest()
        for t in manifest.list_tools():
            if not t.deterministic:
                assert t.review_required is True


# ── Descriptors ─────────────────────────────────────────────────


class TestDescriptors:
    def test_all_regulatory_category(self) -> None:
        for d in (
            RESOLVE_REGIME_DESCRIPTOR,
            INSTANTIATE_REQUIREMENTS_DESCRIPTOR,
            ASSEMBLE_GATES_DESCRIPTOR,
            ASSESS_DEROGATIONS_DESCRIPTOR,
            MAP_PRINCIPLES_DESCRIPTOR,
            BENCHMARK_STATUS_DESCRIPTOR,
            ANALYZE_CLAUSE_DESCRIPTOR,
            ASSESS_COMPLEX_DEROGATION_DESCRIPTOR,
        ):
            assert d.category == ToolCategory.REGULATORY

    def test_input_schemas_present(self) -> None:
        for d in (
            RESOLVE_REGIME_DESCRIPTOR,
            INSTANTIATE_REQUIREMENTS_DESCRIPTOR,
            ASSEMBLE_GATES_DESCRIPTOR,
        ):
            assert d.input_schema.get("type") == "object"


# ── resolve_regime (deterministic, testable) ────────────────────


class TestResolveRegime:
    def test_sci_framework(self) -> None:
        result = resolve_regime(
            framework="sci",
            procurement_family="goods",
            estimated_value=25000,
            currency="USD",
        )
        assert "framework" in result
        assert "threshold_tier" in result
        assert "procedure_type" in result

    def test_unknown_framework(self) -> None:
        result = resolve_regime(
            framework="nonexistent",
            procurement_family="goods",
        )
        assert result["framework"] == "unknown"

    def test_via_manifest_invoke(self) -> None:
        manifest = build_default_manifest()
        result = manifest.invoke(
            "resolve_regime",
            framework="sci",
            procurement_family="goods",
            estimated_value=5000,
        )
        assert isinstance(result, dict)


# ── get_benchmark_status ────────────────────────────────────────


class TestGetBenchmarkStatus:
    def test_returns_status_and_proposal(self) -> None:
        result = get_benchmark_status()
        assert "status" in result
        assert "transition_proposal" in result
        assert result["status"]["total_cases_processed"] == 0

    def test_via_manifest_invoke(self) -> None:
        manifest = build_default_manifest()
        result = manifest.invoke("get_benchmark_status")
        assert isinstance(result, dict)


# ── LLM placeholders ───────────────────────────────────────────


class TestLLMPlaceholders:
    def test_analyze_clause_placeholder(self) -> None:
        result = analyze_clause("some clause text", "sci")
        assert result["review_required"] is True
        assert result["status"] == "placeholder"

    def test_assess_complex_derogation_placeholder(self) -> None:
        result = assess_complex_derogation("complex context", "dgmp_mali")
        assert result["review_required"] is True
        assert result["status"] == "placeholder"
