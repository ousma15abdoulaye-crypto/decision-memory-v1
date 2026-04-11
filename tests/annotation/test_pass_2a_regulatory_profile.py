"""Pass 2A — regulatory profile (M13)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_2a_regulatory_profile import (
    run_pass_2a_regulatory_profile,
)
from tests.procurement.m13_test_fixtures import (
    minimal_m12_output_with_h1,
    pass_output_dicts_from_m12,
)

ALLOWED_CONFIDENCES = {0.6, 0.8, 1.0}


def _collect_confidences(obj: object) -> list[float]:
    """Walk a nested dict/list and collect all values keyed 'confidence'."""
    found: list[float] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "confidence" and isinstance(v, int | float):
                found.append(float(v))
            else:
                found.extend(_collect_confidences(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_confidences(item))
    return found


class TestPass2ARegulatoryProfile:
    def test_skipped_without_h1_skeleton(self) -> None:
        m12 = minimal_m12_output_with_h1()
        p1a, p1b, p1c, p1d = pass_output_dicts_from_m12(m12)
        p1c_no_h1 = {
            "m12_conformity": p1c["m12_conformity"],
            "m12_handoffs": {"regulatory_profile_skeleton": None},
        }
        out = run_pass_2a_regulatory_profile(
            case_id="c1",
            document_id="d1",
            run_id=uuid.uuid4(),
            pass_1a_output_data=p1a,
            pass_1b_output_data=p1b,
            pass_1c_output_data=p1c_no_h1,
            pass_1d_output_data=p1d,
        )
        assert out.status == PassRunStatus.SKIPPED

    def test_success_with_h1(self) -> None:
        m12 = minimal_m12_output_with_h1()
        p1a, p1b, p1c, p1d = pass_output_dicts_from_m12(m12)
        out = run_pass_2a_regulatory_profile(
            case_id="c1",
            document_id="d1",
            run_id=uuid.uuid4(),
            pass_1a_output_data=p1a,
            pass_1b_output_data=p1b,
            pass_1c_output_data=p1c,
            pass_1d_output_data=p1d,
        )
        assert out.status == PassRunStatus.SUCCESS
        assert "m13_output" in out.output_data
        assert "legacy_compliance_report" in out.output_data

    def test_failed_on_invalid_m12(self) -> None:
        """Corrupted pass_1a triggers ValidationError -> FAILED."""
        m12 = minimal_m12_output_with_h1()
        _, p1b, p1c, p1d = pass_output_dicts_from_m12(m12)
        p1a_bad = {"m12_recognition": "NOT_A_DICT"}
        out = run_pass_2a_regulatory_profile(
            case_id="c1",
            document_id="d1",
            run_id=uuid.uuid4(),
            pass_1a_output_data=p1a_bad,
            pass_1b_output_data=p1b,
            pass_1c_output_data=p1c,
            pass_1d_output_data=p1d,
        )
        assert out.status == PassRunStatus.FAILED
        assert len(out.errors) >= 1
        assert out.errors[0].code == "PASS_2A_M12_INVALID"
        assert out.output_data == {}

    def test_degraded_on_engine_error(self) -> None:
        """Runtime engine failure -> DEGRADED with structured output."""
        m12 = minimal_m12_output_with_h1()
        p1a, p1b, p1c, p1d = pass_output_dicts_from_m12(m12)
        with patch(
            "src.annotation.passes.pass_2a_regulatory_profile.RegulatoryComplianceEngine"
        ) as mock_cls:
            mock_cls.return_value.process_m12.side_effect = RuntimeError("yaml broken")
            out = run_pass_2a_regulatory_profile(
                case_id="c1",
                document_id="d1",
                run_id=uuid.uuid4(),
                pass_1a_output_data=p1a,
                pass_1b_output_data=p1b,
                pass_1c_output_data=p1c,
                pass_1d_output_data=p1d,
            )
        assert out.status == PassRunStatus.DEGRADED
        assert out.output_data.get("pass_2a_degraded") is True
        assert "degraded_reason" in out.output_data
        assert len(out.errors) >= 1
        assert out.errors[0].code == "PASS_2A_DEGRADED"

    def test_confidence_values_in_allowed_set(self) -> None:
        """All confidence values in SUCCESS output must be in {0.6, 0.8, 1.0}."""
        m12 = minimal_m12_output_with_h1()
        p1a, p1b, p1c, p1d = pass_output_dicts_from_m12(m12)
        out = run_pass_2a_regulatory_profile(
            case_id="c1",
            document_id="d1",
            run_id=uuid.uuid4(),
            pass_1a_output_data=p1a,
            pass_1b_output_data=p1b,
            pass_1c_output_data=p1c,
            pass_1d_output_data=p1d,
        )
        assert out.status == PassRunStatus.SUCCESS
        m13_payload = out.output_data.get("m13_output", {})
        confs = _collect_confidences(m13_payload)
        assert len(confs) > 0, "Expected at least one confidence value in M13 output"
        bad = [c for c in confs if c not in ALLOWED_CONFIDENCES]
        assert bad == [], f"Confidence values outside {{0.6, 0.8, 1.0}}: {bad}"
