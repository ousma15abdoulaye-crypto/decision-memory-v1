"""Pass 2A — regulatory profile (M13)."""

from __future__ import annotations

import uuid

from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_2a_regulatory_profile import (
    run_pass_2a_regulatory_profile,
)
from tests.procurement.m13_test_fixtures import (
    minimal_m12_output_with_h1,
    pass_output_dicts_from_m12,
)


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
