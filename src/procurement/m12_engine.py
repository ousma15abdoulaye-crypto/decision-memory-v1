"""M12 engine — enchaîne Pass 1A–1D pour produire un M12Output métier.

Utilisé par ``run_pipeline_v5`` (ADR-0012 addendum) à la place du bootstrap
heuristique ``build_pipeline_v5_minimal_m12`` (D-001 : carte ``bundle_id → M12Output``).

Assemblage identique à ``run_pass_2a_regulatory_profile`` : les sorties des
passes sont fusionnées via ``build_m12_output_from_pass_outputs``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.annotation.pass_output import AnnotationPassOutput, PassRunStatus
from src.annotation.passes.pass_1a_core_recognition import run_pass_1a_core_recognition
from src.annotation.passes.pass_1b_document_validity import (
    run_pass_1b_document_validity,
)
from src.annotation.passes.pass_1c_conformity_and_handoffs import (
    run_pass_1c_conformity_and_handoffs,
)
from src.annotation.passes.pass_1d_process_linking import run_pass_1d_process_linking
from src.procurement.m12_reconstruct import build_m12_output_from_pass_outputs
from src.procurement.procedure_models import M12Output

logger = logging.getLogger(__name__)


class M12CorpusPipelineError(RuntimeError):
    """Échec explicite d'une passe M12 — pas de repli bootstrap."""

    def __init__(self, pass_label: str, detail: str) -> None:
        self.pass_label = pass_label
        self.detail = detail
        super().__init__(f"[{pass_label}] {detail}")


def _require_pass_output(
    label: str,
    out: AnnotationPassOutput,
    *,
    required_keys: frozenset[str],
) -> dict[str, Any]:
    if out.status == PassRunStatus.FAILED:
        msg = out.errors[0].message if out.errors else "no error detail"
        raise M12CorpusPipelineError(label, f"status=failed: {msg}")
    data = out.output_data or {}
    missing = required_keys - data.keys()
    if missing:
        raise M12CorpusPipelineError(
            label,
            f"missing output_data keys: {sorted(missing)}",
        )
    return data


def _m12_recognition(pass_1a_data: dict[str, Any]) -> dict[str, Any]:
    rec = pass_1a_data.get("m12_recognition")
    if not isinstance(rec, dict) or not rec:
        raise M12CorpusPipelineError(
            "pass_1a",
            "m12_recognition missing or empty",
        )
    return rec


def _traced_value_str(
    m12_rec: dict[str, Any], key: str, default: str = "unknown"
) -> str:
    block = m12_rec.get(key)
    if not isinstance(block, dict):
        return default
    v = block.get("value")
    if v is None:
        return default
    if hasattr(v, "value"):
        return str(v.value)
    return str(v)


def _traced_confidence(m12_rec: dict[str, Any], key: str) -> float:
    block = m12_rec.get(key)
    if not isinstance(block, dict):
        return 0.6
    c = block.get("confidence")
    try:
        return float(c) if c is not None else 0.6
    except (TypeError, ValueError):
        return 0.6


def _is_composite_str(m12_rec: dict[str, Any]) -> str:
    block = m12_rec.get("is_composite")
    if not isinstance(block, dict):
        return "no"
    v = block.get("value")
    if v is True:
        return "yes"
    if v is False:
        return "no"
    if isinstance(v, str):
        return v.lower() if v else "no"
    return str(v).lower() if v else "no"


def build_m12_output_for_corpus(
    *,
    corpus_text: str,
    document_id: str,
    run_id: uuid.UUID,
    quality_class: str = "good",
    block_llm: bool = False,
) -> M12Output:
    """Exécute les passes 1A–1D sur un corpus et assemble ``M12Output``.

    Args:
        corpus_text: Texte concaténé (ex. bundle_documents du workspace).
        document_id: Identifiant stable (ex. ``pipeline_v5:{workspace_id}``).
        run_id: UUID de corrélation pour les passes.
        quality_class: Transmis à 1A / 1B (défaut ``good``).
        block_llm: Si True, 1A peut dégrader sans LLM (tests / containment).

    Raises:
        M12CorpusPipelineError: passe en FAILED ou données requises absentes.
    """
    text = (corpus_text or "").strip()
    if not text:
        raise M12CorpusPipelineError("pass_1a", "corpus_text vide")

    logger.info(
        "[M12-ENGINE] build_m12_output_for_corpus document_id=%s text_len=%d",
        document_id,
        len(text),
    )

    p1a = run_pass_1a_core_recognition(
        normalized_text=text,
        document_id=document_id,
        run_id=run_id,
        quality_class=quality_class,
        block_llm=block_llm,
    )
    pass_1a_data = _require_pass_output(
        "pass_1a",
        p1a,
        required_keys=frozenset({"m12_recognition"}),
    )
    m12_rec = _m12_recognition(pass_1a_data)

    doc_kind = _traced_value_str(m12_rec, "document_kind")
    if doc_kind == "unknown" and pass_1a_data.get("taxonomy_core"):
        doc_kind = str(pass_1a_data["taxonomy_core"])

    p1b = run_pass_1b_document_validity(
        normalized_text=text,
        document_id=document_id,
        run_id=run_id,
        document_kind=doc_kind,
        quality_class=quality_class,
    )
    pass_1b_data = _require_pass_output(
        "pass_1b",
        p1b,
        required_keys=frozenset({"m12_validity"}),
    )

    fw_str = _traced_value_str(m12_rec, "framework_detected")
    fam_str = _traced_value_str(m12_rec, "procurement_family")
    fam_sub_str = _traced_value_str(m12_rec, "procurement_family_sub")
    fw_conf = _traced_confidence(m12_rec, "framework_detected")
    isc = _is_composite_str(m12_rec)

    p1c = run_pass_1c_conformity_and_handoffs(
        normalized_text=text,
        document_id=document_id,
        run_id=run_id,
        document_kind_str=doc_kind,
        is_composite=isc,
        validity_dict=pass_1b_data["m12_validity"],
        framework_str=fw_str,
        framework_confidence=fw_conf,
        family_str=fam_str,
        family_sub_str=fam_sub_str,
    )
    pass_1c_data = _require_pass_output(
        "pass_1c",
        p1c,
        required_keys=frozenset({"m12_conformity", "m12_handoffs"}),
    )

    p1d = run_pass_1d_process_linking(
        normalized_text=text,
        document_id=document_id,
        run_id=run_id,
        pass_1a_output_data=pass_1a_data,
        case_documents_1a=None,
    )
    pass_1d_data = _require_pass_output(
        "pass_1d",
        p1d,
        required_keys=frozenset({"m12_linking"}),
    )

    return build_m12_output_from_pass_outputs(
        pass_1a_data=pass_1a_data,
        pass_1b_data=pass_1b_data,
        pass_1c_data=pass_1c_data,
        pass_1d_data=pass_1d_data,
    )
