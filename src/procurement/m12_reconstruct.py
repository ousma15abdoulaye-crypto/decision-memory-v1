"""Reconstruit M12Output depuis les sorties de passes sérialisées."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    M12Handoffs,
    M12Meta,
    M12Output,
    ProcedureRecognition,
    ProcessLinking,
)


def build_m12_output_from_pass_outputs(
    *,
    pass_1a_data: dict[str, Any],
    pass_1b_data: dict[str, Any],
    pass_1c_data: dict[str, Any],
    pass_1d_data: dict[str, Any],
) -> M12Output:
    rec_raw = pass_1a_data.get("m12_recognition") or {}
    recognition = ProcedureRecognition.model_validate(rec_raw)
    validity = DocumentValidity.model_validate(pass_1b_data.get("m12_validity") or {})
    conformity = DocumentConformitySignal.model_validate(
        pass_1c_data.get("m12_conformity") or {}
    )
    handoffs = M12Handoffs.model_validate(pass_1c_data.get("m12_handoffs") or {})
    linking = ProcessLinking.model_validate(pass_1d_data.get("m12_linking") or {})

    meta = M12Meta(
        mode="bootstrap",
        confidence_ceiling=1.0,
        corpus_size_at_processing=0,
        processing_timestamp=datetime.now(UTC).isoformat(),
        pass_sequence=["1a", "1b", "1c", "1d"],
    )
    return M12Output(
        procedure_recognition=recognition,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=handoffs,
        m12_meta=meta,
    )
