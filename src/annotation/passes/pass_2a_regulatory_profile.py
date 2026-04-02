"""
Pass 2A — Regulatory Profile (M13).

Contrat : docs/contracts/annotation/PASS_2A_REGULATORY_PROFILE_CONTRACT.md
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)
from src.procurement.compliance_models_m13 import legacy_compliance_report_from_m13
from src.procurement.m12_reconstruct import build_m12_output_from_pass_outputs
from src.procurement.m13_engine import RegulatoryComplianceEngine

_PASS_NAME = "pass_2a_regulatory_profile"
_PASS_VERSION = "1.0.0"


def run_pass_2a_regulatory_profile(
    *,
    case_id: str,
    document_id: str,
    run_id: uuid.UUID,
    pass_1a_output_data: dict[str, Any],
    pass_1b_output_data: dict[str, Any],
    pass_1c_output_data: dict[str, Any],
    pass_1d_output_data: dict[str, Any],
) -> AnnotationPassOutput:
    started = datetime.now(UTC)
    errors: list[PassError] = []

    mh = pass_1c_output_data.get("m12_handoffs") or {}
    if not mh.get("regulatory_profile_skeleton"):
        completed = datetime.now(UTC)
        return AnnotationPassOutput(
            pass_name=_PASS_NAME,
            pass_version=_PASS_VERSION,
            document_id=document_id,
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            status=PassRunStatus.SKIPPED,
            output_data={"m13_skip_reason": "no_regulatory_profile_skeleton"},
            errors=[],
            metadata={"duration_ms": int((completed - started).total_seconds() * 1000)},
        )

    try:
        m12 = build_m12_output_from_pass_outputs(
            pass_1a_data=pass_1a_output_data,
            pass_1b_data=pass_1b_output_data,
            pass_1c_data=pass_1c_output_data,
            pass_1d_data=pass_1d_output_data,
        )
        engine = RegulatoryComplianceEngine()
        m13_out = engine.process_m12(case_id=case_id, document_id=document_id, m12=m12)
        legacy = legacy_compliance_report_from_m13(
            document_id=document_id, m13=m13_out.report
        )
        output_data = {
            "m13_output": m13_out.model_dump(mode="json"),
            "legacy_compliance_report": legacy.model_dump(mode="json"),
        }
        status = PassRunStatus.SUCCESS
    except ValidationError as exc:
        errors.append(PassError(code="PASS_2A_M12_INVALID", message=str(exc)[:500]))
        output_data = {}
        status = PassRunStatus.FAILED
    except Exception as exc:
        # Config YAML / moteur : sortie dégradée documentée (pas FAILED binaire).
        msg = str(exc)[:500]
        errors.append(PassError(code="PASS_2A_DEGRADED", message=msg))
        output_data = {
            "pass_2a_degraded": True,
            "m13_review_required": True,
            "degraded_reason": msg,
        }
        status = PassRunStatus.DEGRADED

    completed = datetime.now(UTC)
    return AnnotationPassOutput(
        pass_name=_PASS_NAME,
        pass_version=_PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=status,
        output_data=output_data,
        errors=errors,
        metadata={
            "duration_ms": int((completed - started).total_seconds() * 1000),
        },
    )
