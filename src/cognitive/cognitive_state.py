"""État cognitif E0–E6 — pur, sans DB (SPEC BLOC5 V4.3.1 B.1).

V5.1.0 : ajout de CognitiveStateResult + compute_cognitive_state_result.
INV-C01 : projection pure — jamais de colonne SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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


# ---------------------------------------------------------------------------
# V5.1.0 — CognitiveStateResult (Canon Section O3)
# ---------------------------------------------------------------------------

# Matrice d'actions disponibles par état (Canon Section 6)
_AVAILABLE_ACTIONS: dict[str, frozenset[str]] = {
    "E0": frozenset({"workspace.manage", "agent.query", "documents.upload"}),
    "E1": frozenset({"workspace.manage", "agent.query"}),
    "E2": frozenset({"workspace.manage", "agent.query", "documents.upload"}),
    "E3": frozenset(
        {"workspace.manage", "agent.query", "evaluation.write", "evaluation.read"}
    ),
    "E4": frozenset(
        {
            "workspace.manage",
            "agent.query",
            "evaluation.write",
            "evaluation.read",
            "committee.comment",
            "market.query",
        }
    ),
    "E5": frozenset(
        {
            "workspace.manage",
            "agent.query",
            "evaluation.read",
            "committee.comment",
            "committee.seal",
            "market.query",
        }
    ),
    "E6": frozenset(
        {
            "evaluation.read",
            "pv.read",
            "pv.export",
            "market.query",
            "agent.query",
        }
    ),
}

_COMPLETENESS: dict[str, float] = {
    "E0": 0.00,
    "E1": 0.17,
    "E2": 0.33,
    "E3": 0.50,
    "E4": 0.67,
    "E5": 0.83,
    "E6": 1.00,
}


@dataclass(frozen=True)
class CognitiveStateResult:
    """Résultat enrichi du moteur cognitif E0→E6 (Canon V5.1.0 Section O3).

    INV-C01 : projection pure — jamais persistée en DB.
    INV-C04 : advance_blockers en français.
    """

    state: str
    label_fr: str
    phase: str
    completeness: float
    can_advance: bool
    advance_blockers: list[str] = field(default_factory=list)
    available_actions: frozenset[str] = field(default_factory=frozenset)
    confidence_regime: str = "red"


def compute_cognitive_state_result(facts: CognitiveFacts) -> CognitiveStateResult:
    """Retourne le résultat complet de la projection cognitive (V5.1.0).

    Backward-compatible : ``compute_cognitive_state`` retourne encore un str.

    Args:
        facts: Faits observables du workspace.

    Returns:
        CognitiveStateResult avec tous les champs Canon Section O3.
    """
    state = compute_cognitive_state(facts)
    meta = COGNITIVE_STATE_METADATA.get(
        state, {"phase": "unknown", "label_fr": "Inconnu"}
    )
    completeness = _COMPLETENESS.get(state, 0.0)

    blockers: list[str] = []
    can_advance = False

    if state == "E0":
        if not facts.has_source_package:
            blockers.append("Aucun dossier source téléchargé.")
        else:
            can_advance = True
    elif state == "E1":
        can_advance = True
    elif state == "E2":
        if facts.bundle_count <= 0:
            blockers.append("Aucune offre fournisseur soumise.")
        else:
            can_advance = True
    elif state == "E3":
        if not facts.bundles_all_qualified:
            blockers.append("Toutes les offres doivent être qualifiées.")
        else:
            can_advance = True
    elif state == "E4":
        if not facts.evaluation_frame_complete:
            blockers.append("La grille d'évaluation doit être complète.")
        else:
            can_advance = True
    elif state == "E5":
        can_advance = True
    elif state == "E6":
        can_advance = False

    actions = _AVAILABLE_ACTIONS.get(state, frozenset())
    if state == "E5" and not can_advance:
        actions = actions - {"committee.seal"}

    if completeness >= 0.80:
        confidence_regime = "green"
    elif completeness >= 0.50:
        confidence_regime = "amber"
    else:
        confidence_regime = "red"

    return CognitiveStateResult(
        state=state,
        label_fr=meta["label_fr"],
        phase=meta["phase"],
        completeness=completeness,
        can_advance=can_advance,
        advance_blockers=blockers,
        available_actions=actions,
        confidence_regime=confidence_regime,
    )


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
