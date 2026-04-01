"""
M12 V6 L7 — Process Linker.

5-level linking: EXACT -> FUZZY -> SUBJECT_TEMPORAL -> CONTEXTUAL -> UNRESOLVED.
Uses rapidfuzz for Level 2 fuzzy matching (reuse existing asset).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from src.procurement.document_ontology import (
    DOCUMENT_KIND_TO_PROCESS_ROLE,
    OFFER_KINDS,
    SOURCE_RULES_KINDS,
    DocumentKindParent,
    LinkNature,
    ProcessRole,
)
from src.procurement.procedure_models import (
    LinkHint,
    ProcessLinking,
    SupplierDetected,
    TracedField,
)

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz as _fuzz

    def _fuzzy_ratio(a: str, b: str) -> float:
        return _fuzz.ratio(a, b) / 100.0

except ImportError:
    logger.warning("rapidfuzz not available; fuzzy linking degraded")

    def _fuzzy_ratio(a: str, b: str) -> float:  # type: ignore[misc]
        return 1.0 if a == b else 0.0


def _load_fuzzy_threshold(
    fallback: float = 0.85,
    *,
    _config_path: Path | None = None,
) -> float:
    """Charge le seuil fuzzy depuis config/llm_arbitration.yaml.

    Retourne ``fallback`` si le fichier est absent ou le chemin introuvable.

    ``_config_path`` (tests uniquement) : surcharge du chemin YAML.
    """
    try:
        import yaml  # type: ignore[import-untyped]

        cfg_path = _config_path or (
            Path(__file__).resolve().parents[2] / "config" / "llm_arbitration.yaml"
        )
        if not cfg_path.exists():
            logger.warning(
                "process_linker: llm_arbitration.yaml absent — "
                "FUZZY_THRESHOLD=%s (fallback)",
                fallback,
            )
            return fallback
        with cfg_path.open(encoding="utf-8") as _f:
            _cfg = yaml.safe_load(_f)
        if not isinstance(_cfg, dict):
            logger.warning(
                "process_linker: llm_arbitration.yaml invalide (type=%s) — "
                "FUZZY_THRESHOLD=%s (fallback)",
                type(_cfg).__name__,
                fallback,
            )
            return fallback
        return float(
            _cfg.get("thresholds", {})
            .get("process_linking", {})
            .get("trigger_below_fuzzy", fallback)
        )
    except Exception as exc:
        logger.warning(
            "process_linker: impossible de charger llm_arbitration.yaml — "
            "FUZZY_THRESHOLD=%s (fallback) — %s",
            fallback,
            exc,
        )
        return fallback


FUZZY_THRESHOLD: float = _load_fuzzy_threshold()

# Budget LLM par document : limite le nombre d'appels semantiques Level 5
# pour eviter l'explosion sur les dossiers avec N candidats sans references.
_MAX_LLM_CALLS_PER_DOC = 3

_REF_PATTERN = re.compile(
    r"(?:r[eé]f[eé]rence|n[°o]|ref)\s*[:\.]?\s*([A-Z0-9][-A-Z0-9/_.]{3,})",
    re.IGNORECASE,
)

_SUPPLIER_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:fournisseur|soumissionnaire|bidder|cabinet|bureau|soci[eé]t[eé]|entreprise)\s*"
    r"[:\-]?\s*([A-Z][A-Za-zÀ-ÿ\s&.,-]{2,50})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    """Minimal summary of a document for linking purposes."""

    document_id: str
    document_kind: DocumentKindParent
    procedure_reference: str | None
    issuing_entity: str | None
    project_name: str | None
    zones: list[str]
    submission_deadline: str | None


def extract_procedure_references(text: str) -> list[str]:
    """Extract procedure reference numbers from text."""
    refs: list[str] = []
    for m in _REF_PATTERN.finditer(text[:5000]):
        ref = m.group(1).strip()
        if len(ref) >= 4:
            refs.append(ref)
    return refs


def extract_suppliers(text: str) -> list[SupplierDetected]:
    """Extract supplier names from offer/evaluation documents."""
    suppliers: list[SupplierDetected] = []
    seen: set[str] = set()
    for m in _SUPPLIER_PATTERN.finditer(text):
        name_raw = m.group(1).strip()
        name_lower = name_raw.lower()
        if name_lower in seen or len(name_raw) < 3:
            continue
        seen.add(name_lower)

        legal_form = None
        for lf in ("SARL", "SA", "SUARL", "GIE", "SAS", "EURL"):
            if lf.lower() in name_lower:
                legal_form = lf
                break

        suppliers.append(
            SupplierDetected(
                name_raw=name_raw,
                name_normalized=name_lower,
                legal_form=legal_form,
                confidence=0.70,
                evidence=f"pattern_match={name_raw[:100]}",
            )
        )
    return suppliers


def _infer_link_nature(
    source_kind: DocumentKindParent, target_kind: DocumentKindParent
) -> LinkNature:
    """Infer link nature from document kind pair."""
    if source_kind in OFFER_KINDS and target_kind in SOURCE_RULES_KINDS:
        return LinkNature.RESPONDS_TO
    if source_kind == DocumentKindParent.EVALUATION_DOC and target_kind in OFFER_KINDS:
        return LinkNature.EVALUATES
    if source_kind == DocumentKindParent.CONTRACT:
        return LinkNature.FORMALIZES
    if source_kind == DocumentKindParent.ADMIN_DOC:
        return LinkNature.ACCOMPANIES
    if (
        source_kind == DocumentKindParent.PO
        and target_kind == DocumentKindParent.CONTRACT
    ):
        return LinkNature.EXECUTES
    if source_kind == DocumentKindParent.GRN and target_kind == DocumentKindParent.PO:
        return LinkNature.RECEIVES
    if source_kind == DocumentKindParent.MARKET_SURVEY:
        return LinkNature.SOURCES_FROM
    return LinkNature.RESPONDS_TO


def link_documents(
    source: DocumentSummary,
    candidates: list[DocumentSummary],
    llm_arbitrator=None,
) -> list[LinkHint]:
    """
    Link a source document to candidates using 5-level matching.
    Level 5 : LLM semantic link (online-first) quand fuzzy et contextuel insuffisants.
    Returns list of LinkHints sorted by confidence (highest first).
    """
    hints: list[LinkHint] = []
    llm_calls_made = (
        0  # budget guard — evite N appels LLM si N candidats sans reference
    )

    for target in candidates:
        if target.document_id == source.document_id:
            continue

        link_nature = _infer_link_nature(source.document_kind, target.document_kind)

        # Level 1: Exact reference match
        if (
            source.procedure_reference
            and target.procedure_reference
            and source.procedure_reference == target.procedure_reference
        ):
            hints.append(
                LinkHint(
                    target_document_id=target.document_id,
                    link_nature=link_nature,
                    link_level="EXACT_REFERENCE",
                    confidence=0.95,
                    evidence=[
                        f"ref={source.procedure_reference}",
                        f"target_kind={target.document_kind.value}",
                    ],
                )
            )
            continue

        # Level 2: Fuzzy reference match
        if source.procedure_reference and target.procedure_reference:
            ratio = _fuzzy_ratio(source.procedure_reference, target.procedure_reference)
            if ratio >= FUZZY_THRESHOLD:
                hints.append(
                    LinkHint(
                        target_document_id=target.document_id,
                        link_nature=link_nature,
                        link_level="FUZZY_REFERENCE",
                        confidence=min(0.85, ratio),
                        evidence=[
                            f"fuzzy_ratio={ratio:.2f}",
                            f"src_ref={source.procedure_reference}",
                            f"tgt_ref={target.procedure_reference}",
                        ],
                    )
                )
                continue

        # Level 3: Subject + temporal match
        subject_match = False
        if source.project_name and target.project_name:
            ratio = _fuzzy_ratio(
                source.project_name.lower(), target.project_name.lower()
            )
            if ratio >= 0.70:
                subject_match = True

        zone_overlap = bool(set(source.zones) & set(target.zones))

        if subject_match or zone_overlap:
            conf = 0.60
            ev = []
            if subject_match:
                ev.append(f"project_match={source.project_name}")
                conf += 0.10
            if zone_overlap:
                ev.append(f"zone_overlap={set(source.zones) & set(target.zones)}")
                conf += 0.05
            hints.append(
                LinkHint(
                    target_document_id=target.document_id,
                    link_nature=link_nature,
                    link_level="SUBJECT_TEMPORAL",
                    confidence=min(0.75, conf),
                    evidence=ev,
                )
            )
            continue

        # Level 4: Contextual — only if same source_rules → offer relationship
        contextual_pair = (
            source.document_kind in OFFER_KINDS
            and target.document_kind in SOURCE_RULES_KINDS
        ) or (
            source.document_kind == DocumentKindParent.EVALUATION_DOC
            and target.document_kind in OFFER_KINDS
        )
        if contextual_pair:
            # Level 5: LLM semantic link — quand fuzzy insuffisant mais lien possible.
            # Budget guard : au max _MAX_LLM_CALLS_PER_DOC appels LLM par document
            # pour eviter l'explosion sur les dossiers a N candidats sans reference.
            # Signal guard : au moins un signal minimal partage (entity/projet/zone)
            # pour ne pas appeler le LLM sur des paires sans aucun contexte commun.
            if llm_arbitrator is not None and llm_calls_made < _MAX_LLM_CALLS_PER_DOC:
                same_entity = bool(
                    source.issuing_entity
                    and target.issuing_entity
                    and source.issuing_entity == target.issuing_entity
                )
                same_project = bool(
                    source.project_name
                    and target.project_name
                    and _fuzzy_ratio(
                        source.project_name.lower(), target.project_name.lower()
                    )
                    >= 0.60
                )
                zone_signal = bool(set(source.zones) & set(target.zones))

                if same_entity or same_project or zone_signal:
                    doc_a_summary = (
                        f"Type: {source.document_kind.value}, "
                        f"Ref: {source.procedure_reference}, "
                        f"Projet: {source.project_name}, "
                        f"Entite: {source.issuing_entity}, "
                        f"Zones: {source.zones}"
                    )
                    doc_b_summary = (
                        f"Type: {target.document_kind.value}, "
                        f"Ref: {target.procedure_reference}, "
                        f"Projet: {target.project_name}, "
                        f"Entite: {target.issuing_entity}, "
                        f"Zones: {target.zones}"
                    )
                    try:
                        llm_field = llm_arbitrator.semantic_link_documents(
                            doc_a_summary=doc_a_summary,
                            doc_b_summary=doc_b_summary,
                        )
                        llm_calls_made += 1
                        if llm_field.value is True and llm_field.confidence >= 0.50:
                            hints.append(
                                LinkHint(
                                    target_document_id=target.document_id,
                                    link_nature=link_nature,
                                    link_level="SEMANTIC_LLM",
                                    confidence=min(llm_field.confidence, 0.80),
                                    evidence=llm_field.evidence,
                                )
                            )
                            continue
                    except Exception as llm_exc:
                        logger.warning(
                            "[LINKER] Level 5 LLM echec pour %s<->%s : %s",
                            source.document_id,
                            target.document_id,
                            llm_exc,
                        )
            elif (
                llm_arbitrator is not None and llm_calls_made >= _MAX_LLM_CALLS_PER_DOC
            ):
                logger.debug(
                    "[LINKER] Budget LLM atteint (%d appels) — fallback CONTEXTUAL pour %s",
                    _MAX_LLM_CALLS_PER_DOC,
                    target.document_id,
                )

            hints.append(
                LinkHint(
                    target_document_id=target.document_id,
                    link_nature=link_nature,
                    link_level="CONTEXTUAL",
                    confidence=0.40,
                    evidence=["contextual_type_pair_only"],
                )
            )

    hints.sort(key=lambda h: -h.confidence)
    return hints


def build_process_linking(
    source: DocumentSummary,
    candidates: list[DocumentSummary],
    text: str,
    llm_arbitrator=None,
) -> ProcessLinking:
    """Build full ProcessLinking for a document.

    llm_arbitrator : LLMArbitrator optionnel pour le Level 5 semantic link.
    """
    role = DOCUMENT_KIND_TO_PROCESS_ROLE.get(source.document_kind, ProcessRole.UNKNOWN)

    parent_hints = link_documents(source, candidates, llm_arbitrator=llm_arbitrator)

    end_marker = "no"
    if source.document_kind == DocumentKindParent.CONTRACT:
        end_marker = "yes"
    elif source.document_kind == DocumentKindParent.GRN:
        end_marker = "yes"

    suppliers: list[SupplierDetected] = []
    if (
        source.document_kind in OFFER_KINDS
        or source.document_kind == DocumentKindParent.EVALUATION_DOC
    ):
        suppliers = extract_suppliers(text)

    refs = extract_procedure_references(text)

    return ProcessLinking(
        process_role=TracedField(
            value=role,
            confidence=0.80,
            evidence=[f"kind={source.document_kind.value}"],
        ),
        linked_parent_hint=parent_hints,
        procedure_end_marker=TracedField(
            value=end_marker,  # type: ignore[arg-type]
            confidence=0.80 if end_marker != "no" else 0.90,
            evidence=[f"kind={source.document_kind.value}"],
        ),
        suppliers_detected=suppliers,
        procedure_reference_chain=refs,
    )
