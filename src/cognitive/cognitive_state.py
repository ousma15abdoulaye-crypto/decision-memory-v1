"""État cognitif E0–E6 — pur, sans DB (SPEC BLOC5 V4.3.1 B.1)."""

from __future__ import annotations

from dataclasses import dataclass


class TransitionForbidden(Exception):  # noqa: N818 — nom canon SPEC BLOC5
    """Levée lorsqu'une transition de status workspace viole un garde."""

    def __init__(self, target_status: str, reason: str) -> None:
        self.target_status = target_status
        self.reason = reason
        super().__init__(f"TransitionForbidden({target_status!r}): {reason}")


@dataclass(frozen=True)
class CognitiveFacts:
    """Faits observables pour le calcul d'état — aucun accès DB ici."""

    workspace_status: str
    has_source_package: bool
    bundle_count: int
    bundles_all_qualified: bool
    evaluation_frame_complete: bool


def compute_cognitive_state(facts: CognitiveFacts) -> str:
    """Retourne l'identifiant d'état cognitif (E0–E6)."""

    s = facts.workspace_status

    if s in ("sealed", "closed", "cancelled"):
        return "E6"
    if s == "in_deliberation":
        return "E5"
    if s == "assembling":
        return "E2"

    if s == "draft":
        if not facts.has_source_package:
            return "E0"
        return "E1"

    if s in ("assembled", "in_analysis", "analysis_complete"):
        all_q = facts.bundle_count > 0 and facts.bundles_all_qualified
        if not all_q:
            return "E3"
        return "E4"

    return "E0"


def validate_transition(
    current_status: str,
    target_status: str,
    facts: CognitiveFacts,
) -> None:
    """Valide un changement de status workspace (guards SPEC B.1)."""

    if target_status == "assembling":
        if not facts.has_source_package:
            raise TransitionForbidden("assembling", "has_source_package doit être True")
    elif target_status == "in_analysis":
        if facts.bundle_count <= 0:
            raise TransitionForbidden("in_analysis", "bundle_count doit être > 0")
    elif target_status == "in_deliberation":
        if not facts.evaluation_frame_complete:
            raise TransitionForbidden(
                "in_deliberation", "evaluation_frame_complete doit être True"
            )
    elif target_status == "sealed":
        if current_status != "in_deliberation":
            raise TransitionForbidden(
                "sealed", "status actuel doit être in_deliberation"
            )


# Libellés SPEC B.1 (identifiant E0–E6 + phase métier).
COGNITIVE_STATE_METADATA: dict[str, dict[str, str]] = {
    "E0": {"phase": "intake", "label_fr": "Collecte initiale"},
    "E1": {"phase": "context_building", "label_fr": "Construction du contexte"},
    "E2": {"phase": "assembly", "label_fr": "Assemblage des offres"},
    "E3": {"phase": "qualification_partial", "label_fr": "Qualification partielle"},
    "E4": {"phase": "comparative_ready", "label_fr": "Comparatif prêt"},
    "E5": {"phase": "deliberation", "label_fr": "Délibération"},
    "E6": {"phase": "memory_committed", "label_fr": "Mémoire engagée / clos"},
}


def describe_cognitive_state(state_id: str) -> dict[str, str]:
    """Retourne phase + libellé pour un identifiant E0–E6."""

    meta = COGNITIVE_STATE_METADATA.get(state_id)
    if not meta:
        return {"state_id": state_id, "phase": "unknown", "label_fr": "Inconnu"}
    return {
        "state_id": state_id,
        "phase": meta["phase"],
        "label_fr": meta["label_fr"],
    }
