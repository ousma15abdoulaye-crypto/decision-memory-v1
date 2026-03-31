"""
M12 V6 L4 — Mandatory Parts Detection Engine.

3-level detection per part: heading match -> keyword density -> LLM fallback.
Rules loaded dynamically from config/mandatory_parts/*.yaml.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.procurement.procedure_models import PartDetectionResult

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "mandatory_parts"


@dataclass(frozen=True, slots=True)
class MandatoryPartRule:
    part_name: str
    level_1_patterns: list[re.Pattern[str]]
    level_1_confidence: float
    level_2_keywords: list[str]
    level_2_min_hits: int
    level_2_window: int
    level_2_confidence: float
    level_2_custom_rule: str | None
    threshold: float


@dataclass(frozen=True, slots=True)
class OptionalPartRule:
    part_name: str
    patterns: list[re.Pattern[str]]


@dataclass(frozen=True, slots=True)
class DocumentTypeRules:
    document_kind: str
    mandatory: list[MandatoryPartRule]
    optional: list[OptionalPartRule]
    not_applicable: list[str]
    critical_rules: list[str]


def _compile_patterns(raw: list[str]) -> list[re.Pattern[str]]:
    compiled = []
    for p in raw:
        if isinstance(p, str) and p.strip():
            compiled.append(re.compile(re.escape(p.strip()), re.IGNORECASE))
    return compiled


def _load_type_rules(path: Path) -> DocumentTypeRules | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return None

    doc_kind = raw.get("document_kind", path.stem)
    mandatory_parts = []
    for part_name, part_cfg in raw.get("mandatory_parts", {}).items():
        if not isinstance(part_cfg, dict):
            continue
        l1 = part_cfg.get("level_1", {})
        l2 = part_cfg.get("level_2", {})
        l1_patterns = l1.get("patterns", []) if isinstance(l1, dict) else []
        # l1 dictionary_keys reserved for future Couche B dictionary boost
        _ = l1.get("dictionary_keys", []) if isinstance(l1, dict) else []

        l2_kw = l2.get("keywords", []) if isinstance(l2, dict) else []
        l2_min = l2.get("min_hits", 2) if isinstance(l2, dict) else 2
        l2_win = l2.get("window", 5) if isinstance(l2, dict) else 5
        l2_custom = l2.get("custom_rule") if isinstance(l2, dict) else None

        threshold = float(part_cfg.get("threshold", 0.75))

        mandatory_parts.append(
            MandatoryPartRule(
                part_name=part_name,
                level_1_patterns=_compile_patterns(l1_patterns),
                level_1_confidence=0.90,
                level_2_keywords=[k for k in l2_kw if isinstance(k, str)],
                level_2_min_hits=int(l2_min),
                level_2_window=int(l2_win),
                level_2_confidence=0.75,
                level_2_custom_rule=l2_custom if isinstance(l2_custom, str) else None,
                threshold=threshold,
            )
        )

    optional_parts = []
    for part_name, part_cfg in raw.get("optional_parts", {}).items():
        if isinstance(part_cfg, dict):
            patterns = part_cfg.get("patterns", [])
        elif isinstance(part_cfg, list):
            patterns = part_cfg
        else:
            patterns = []
        optional_parts.append(
            OptionalPartRule(
                part_name=part_name,
                patterns=_compile_patterns(patterns),
            )
        )

    na = raw.get("not_applicable", [])
    if not isinstance(na, list):
        na = []

    crit = raw.get("critical_rules", [])
    if not isinstance(crit, list):
        crit = []

    return DocumentTypeRules(
        document_kind=doc_kind,
        mandatory=mandatory_parts,
        optional=optional_parts,
        not_applicable=[str(x) for x in na],
        critical_rules=[str(x) for x in crit],
    )


class MandatoryPartsEngine:
    """Loads all config/mandatory_parts/*.yaml and detects parts per document type.

    llm_arbitrator (optionnel) : instance de LLMArbitrator pour le Level 3.
    Si absent, Level 3 retourne not_detected (comportement offline inchange).
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        llm_arbitrator=None,
    ) -> None:
        self._config_dir = config_dir or _CONFIG_DIR
        self._rules: dict[str, DocumentTypeRules] = {}
        self._llm_arbitrator = llm_arbitrator
        self._load_all()

    def _load_all(self) -> None:
        if not self._config_dir.is_dir():
            logger.warning("mandatory_parts config dir missing: %s", self._config_dir)
            return
        for p in sorted(self._config_dir.glob("*.yaml")):
            if p.name.startswith("_"):
                continue
            rules = _load_type_rules(p)
            if rules is not None:
                self._rules[rules.document_kind] = rules

    def get_rules(self, document_kind: str) -> DocumentTypeRules | None:
        return self._rules.get(document_kind)

    @property
    def known_types(self) -> frozenset[str]:
        return frozenset(self._rules.keys())

    def detect_parts(
        self,
        text: str,
        document_kind: str,
    ) -> tuple[list[PartDetectionResult], list[str], list[str]]:
        """
        Detect mandatory + optional parts for a given document type.
        Returns (detection_details, optional_present, not_applicable).
        """
        rules = self._rules.get(document_kind)
        if rules is None:
            return [], [], []

        text_lower = text.lower()
        results: list[PartDetectionResult] = []

        for part in rules.mandatory:
            result = self._detect_single_part(
                text_lower, part, document_kind=document_kind, text_original=text
            )
            results.append(result)

        optional_present: list[str] = []
        for opt in rules.optional:
            for pat in opt.patterns:
                if pat.search(text_lower):
                    optional_present.append(opt.part_name)
                    break

        return results, optional_present, rules.not_applicable

    def _detect_single_part(
        self,
        text_lower: str,
        rule: MandatoryPartRule,
        document_kind: str = "",
        text_original: str = "",
    ) -> PartDetectionResult:
        # Level 1: heading match
        for pat in rule.level_1_patterns:
            if pat.search(text_lower):
                return PartDetectionResult(
                    part_name=rule.part_name,
                    detection_level="level_1_heading",
                    confidence=rule.level_1_confidence,
                    evidence=[f"pattern_match={pat.pattern}"],
                )

        # Level 2: keyword density in sliding window
        if rule.level_2_keywords:
            best_hits = self._sliding_window_keyword_hits(
                text_lower, rule.level_2_keywords, rule.level_2_window
            )
            if best_hits >= rule.level_2_min_hits:
                return PartDetectionResult(
                    part_name=rule.part_name,
                    detection_level="level_2_keyword",
                    confidence=rule.level_2_confidence,
                    evidence=[
                        f"keyword_hits={best_hits}/{rule.level_2_min_hits}",
                        f"window={rule.level_2_window}_sentences",
                    ],
                )

        # Level 2 custom rules (simple heuristics, no LLM)
        if rule.level_2_custom_rule:
            custom_result = self._run_custom_rule(text_lower, rule.level_2_custom_rule)
            if custom_result:
                return PartDetectionResult(
                    part_name=rule.part_name,
                    detection_level="level_2_keyword",
                    confidence=rule.level_2_confidence,
                    evidence=[f"custom_rule={rule.level_2_custom_rule}"],
                )

        # Level 3 : LLM arbitration (online-first, appele uniquement si L1+L2 echouent)
        if self._llm_arbitrator is not None:
            try:
                part_desc = (
                    f"Section obligatoire d'un document {document_kind}"
                    if document_kind
                    else rule.part_name
                )
                # Preferer le texte original (non minusculise) pour la qualite du prompt LLM
                excerpt = (text_original or text_lower)[:2000]
                llm_result = self._llm_arbitrator.detect_mandatory_part(
                    text_excerpt=excerpt,
                    part_name=rule.part_name,
                    part_description=part_desc,
                )
                # Seuil coherent avec le plafond LLM : min(rule.threshold, cap LLM)
                # evite que la condition soit inatteignable quand rule.threshold > cap
                l3_threshold = min(
                    rule.threshold,
                    (
                        self._llm_arbitrator._max_conf_parts
                        if hasattr(self._llm_arbitrator, "_max_conf_parts")
                        else 0.70
                    ),
                )
                if llm_result.value is True and llm_result.confidence >= l3_threshold:
                    return PartDetectionResult(
                        part_name=rule.part_name,
                        detection_level="level_3_llm",
                        confidence=llm_result.confidence,
                        evidence=llm_result.evidence,
                    )
            except Exception as llm_exc:
                logger.warning(
                    "[PARTS] Level 3 LLM echec pour '%s' (non bloquant) : %s",
                    rule.part_name,
                    llm_exc,
                )

        return PartDetectionResult(
            part_name=rule.part_name,
            detection_level="not_detected",
            confidence=0.0,
            evidence=["no_match_at_any_level"],
        )

    @staticmethod
    def _sliding_window_keyword_hits(
        text_lower: str, keywords: list[str], window_size: int
    ) -> int:
        """Count max keyword hits in any window of *window_size* sentences.

        Splits text on sentence-like boundaries (period / newline) and slides
        a window of *window_size* consecutive sentences, returning the highest
        keyword-hit count observed in any single window.
        """
        sentences = re.split(r"[.\n]+", text_lower)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0
        if window_size <= 0 or window_size >= len(sentences):
            chunk = " ".join(sentences)
            return sum(1 for kw in keywords if kw.lower() in chunk)
        best = 0
        for start in range(len(sentences) - window_size + 1):
            chunk = " ".join(sentences[start : start + window_size])
            hits = sum(1 for kw in keywords if kw.lower() in chunk)
            if hits > best:
                best = hits
                if best >= len(keywords):
                    break
        return best

    @staticmethod
    def _run_custom_rule(text_lower: str, rule_name: str) -> bool:
        """Simple heuristic custom rules (no LLM, no DB)."""
        if rule_name == "word_count_gte_500":
            return len(text_lower.split()) >= 500
        if rule_name == "word_count_gte_200":
            return len(text_lower.split()) >= 200
        if rule_name == "detect_legal_form":
            return bool(
                re.search(
                    r"\b(SARL|SA|SUARL|GIE|SAS|EURL)\b", text_lower, re.IGNORECASE
                )
            )
        if rule_name == "detect_entity_name":
            return bool(
                re.search(
                    r"\b(société|cabinet|bureau|entreprise|company)\b",
                    text_lower,
                    re.IGNORECASE,
                )
            )
        if rule_name == "detect_currency_and_amount":
            return bool(
                re.search(r"\b(FCFA|XOF|USD|EUR)\b", text_lower, re.IGNORECASE)
            ) and bool(re.search(r"\d{1,3}(?:[.\s]\d{3})+|\d{4,}", text_lower))
        if rule_name == "detect_signature_blocks":
            return bool(
                re.search(r"(signature|signé|sign[ée])", text_lower, re.IGNORECASE)
            )
        if rule_name == "detect_reference_number":
            return bool(re.search(r"n[°o]\s*\w+[-/]\w+", text_lower, re.IGNORECASE))
        if rule_name == "count_distinct_supplier_names_gte_2":
            suppliers = re.findall(
                r"(?:fournisseur|soumissionnaire|bidder)\s*(?:n[°o])?\s*(\d+|[A-Z])",
                text_lower,
                re.IGNORECASE,
            )
            return len(set(suppliers)) >= 2
        if rule_name == "detect_institutional_markers":
            return bool(
                re.search(r"(délivré|émis|certifié|numéro)", text_lower, re.IGNORECASE)
            )
        if rule_name == "match_any_admin_subtype":
            admin_markers = [
                "nif",
                "rccm",
                "rib",
                "quitus",
                "non-faillite",
                "attestation",
                "licence",
                "certificat",
            ]
            return any(m in text_lower for m in admin_markers)
        if rule_name == "detect_hierarchical_numbering":
            return bool(re.search(r"\b\d+\.\d+\.\d+", text_lower))
        if rule_name == "detect_unit_column":
            units = ["m2", "m3", "ml", "fft", "kg", "t ", " l ", " m "]
            return sum(1 for u in units if u in text_lower) >= 2
        if rule_name == "detect_numeric_column_pu":
            return bool(
                re.search(
                    r"(prix\s+unitaire|pu|unit\s+price)", text_lower, re.IGNORECASE
                )
            )
        if rule_name == "table_row_count_gte_1":
            return "\t" in text_lower or "|" in text_lower
        if rule_name == "offer_technical_corps_detected":
            return bool(
                re.search(
                    r"(m[eé]thodologie|approche\s+technique|organigramme|planning"
                    r"|chronogramme|moyens?\s+(?:humains?|mat[eé]riels?))",
                    text_lower,
                    re.IGNORECASE,
                )
            )
        if rule_name == "offer_financial_structure_detected":
            return bool(
                re.search(
                    r"(bordereau|d[eé]composition|sous[- ]?d[eé]tail|prix\s+unitaire"
                    r"|montant\s+(?:total|global|ht|ttc))",
                    text_lower,
                    re.IGNORECASE,
                )
            )
        if rule_name == "detect_entity_with_address":
            has_entity = bool(
                re.search(
                    r"\b(soci[eé]t[eé]|cabinet|bureau|entreprise|company|sarl|sa)\b",
                    text_lower,
                    re.IGNORECASE,
                )
            )
            has_address = bool(
                re.search(
                    r"(adresse|bp\s*\d|rue\s+|avenue\s+|boulevard\s+|quartier\s+)",
                    text_lower,
                    re.IGNORECASE,
                )
            )
            return has_entity and has_address
        if rule_name == "detect_two_distinct_named_entities":
            entities = re.findall(
                r"(?:soci[eé]t[eé]|cabinet|entreprise|ets|company)"
                r"\s+([a-z\u00e0-\u00ff][a-z\u00e0-\u00ff&-]{1,30})",
                text_lower,
            )
            return len(set(e.strip() for e in entities)) >= 2
        if rule_name == "detect_numeric_table":
            rows_with_numbers = re.findall(
                r"[\t|].*\d{1,3}(?:[.\s,]\d{3})*.*[\t|]", text_lower
            )
            return len(rows_with_numbers) >= 3
        if rule_name == "detect_table_headers_price":
            return bool(
                re.search(
                    r"(d[eé]signation|libell[eé]|description)"
                    r".*?(quantit[eé]|qt[eé]|unit[eé]|prix|montant|total)",
                    text_lower,
                    re.IGNORECASE,
                )
            )
        return False
