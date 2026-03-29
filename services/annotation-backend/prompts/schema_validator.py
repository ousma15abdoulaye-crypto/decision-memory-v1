"""
Validateur Pydantic v2 — schéma DMS v3.0.1d
Couche 2 de contrôle — après parsing Mistral.
Toute clé inconnue = rejetée (extra="forbid").
line_total_check recalculé par le backend — jamais par Mistral.
ADR-015 — 2026-03-16
"""

from __future__ import annotations

import copy
import json
import logging
import math
from enum import StrEnum
from typing import Any, Literal

from annotation_qa import parse_loose_money_float
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ÉNUMÉRATIONS FIGÉES
# ─────────────────────────────────────────────


class GateName(StrEnum):
    ELIGIBILITY_PASSED = "gate_eligibility_passed"
    CAPACITY_PASSED = "gate_capacity_passed"
    VISIT_REQUIRED = "gate_visit_required"
    VISIT_PASSED = "gate_visit_passed"
    SAMPLES_REQUIRED = "gate_samples_required"
    SAMPLES_PASSED = "gate_samples_passed"
    COMMERCIAL_ELIGIBLE = "gate_commercial_eligible"
    FINANCIAL_FORMAT_USABLE = "gate_financial_format_usable"
    LINE_ITEM_EXTRACTABLE = "gate_line_item_extractable"
    NEGOTIATION_REACHED = "gate_negotiation_reached"


class GateState(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class LineCheck(StrEnum):
    OK = "OK"
    ANOMALY = "ANOMALY"
    NON_VERIFIABLE = "NON_VERIFIABLE"
    # ARCH-03 — agrégat : pas de contrôle qty×unit_price sur cette ligne
    SUBTOTAL_NOT_CHECKED_HERE = "SUBTOTAL_NOT_CHECKED_HERE"


class LineItemLevel(StrEnum):
    """ARCH-03 — hiérarchie : detail | subtotal | total ; item_line_no séquentiel (JSON-FIX-ANNOT-01-v2 D3)."""

    DETAIL = "detail"
    SUBTOTAL = "subtotal"
    TOTAL = "total"


class AnnotationStatus(StrEnum):
    PENDING = "pending"
    REVIEW_REQUIRED = "review_required"
    ANNOTATED_VALIDATED = "annotated_validated"


# ─────────────────────────────────────────────
# MODÈLES DE BASE
# ─────────────────────────────────────────────


class FieldValue(BaseModel):
    """Champ standard : value + confidence + evidence."""

    model_config = {"extra": "forbid"}

    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str

    @model_validator(mode="after")
    def validate_confidence_levels(self) -> FieldValue:
        allowed = {0.6, 0.8, 1.0}
        if self.confidence not in allowed:
            raise ValueError(
                f"confidence={self.confidence} interdit. Valeurs autorisées : {allowed}"
            )
        return self

    @model_validator(mode="after")
    def validate_no_sensitive_in_evidence(self) -> FieldValue:
        """Empêche les numéros sensibles dans evidence."""
        forbidden_patterns = ["NIF:", "RCCM:", "IBAN:", "RIB:"]
        ev = str(self.evidence)
        for pattern in forbidden_patterns:
            if pattern in ev:
                raise ValueError(
                    f"evidence contient '{pattern}' — "
                    "données sensibles interdites. "
                    "Utiliser 'p.N — NIF présent' uniquement."
                )
        return self


def _coerce_whole_int(v: Any, field_label: str) -> Any:
    """parent_subtotal_no : entier (référence sous-total parent)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        r = int(round(v))
        if abs(v - r) > 1e-9:
            raise ValueError(f"{field_label} doit être un entier, reçu {v!r}")
        return r
    if isinstance(v, str):
        s = v.strip().replace("\u202f", "").replace("\u00a0", " ").replace(" ", "")
        if not s:
            return v
        try:
            x = float(s.replace(",", "."))
        except (ValueError, TypeError):
            return v
        r = int(round(x))
        if abs(x - r) > 1e-9:
            raise ValueError(f"{field_label} doit être un entier, reçu {v!r}")
        return r
    return v


# ─────────────────────────────────────────────
# JSON-FIX-ANNOT-01-v2 — normalisation post-Mistral (Phase 1)
# ─────────────────────────────────────────────

BOOLEAN_FIELDS = frozenset(
    {
        "has_nif",
        "has_rccm",
        "has_rib",
        "has_id_representative",
        "has_statutes",
        "has_quitus_fiscal",
        "has_certificat_non_faillite",
        "has_sci_conditions_signed",
        "has_iapg_signed",
        "has_non_sanction",
        "ariba_network_required",
        "discount_terms_present",
        "review_required",
    }
)

BOOL_MAP = {
    "true": True,
    "false": False,
    "True": True,
    "False": False,
    "TRUE": True,
    "FALSE": False,
    # Sorties Mistral / formulaires FR (DAO, listes de pièces)
    "OUI": True,
    "oui": True,
    "Oui": True,
    "NON": False,
    "non": False,
    "Non": False,
    "requis": True,
    "REQUIS": True,
    "Requis": True,
    # Listes de pièces / specs (anglais)
    "required": True,
    "Required": True,
    "REQUIRED": True,
    "optional": False,
    "Optional": False,
    "OPTIONAL": False,
}


def _parse_bool_string(s: str) -> bool | None:
    """Interprète une chaîne comme booléen ; None si non reconnu."""
    if not isinstance(s, str):
        return None
    t = s.strip()
    if t in BOOL_MAP:
        return BOOL_MAP[t]
    low = t.lower()
    if low in ("oui", "yes"):
        return True
    if low in ("non", "no"):
        return False
    if low == "requis":
        return True
    if low == "required":
        return True
    if low == "optional":
        return False
    return None


def coerce_gate_value_for_applicable(v: Any) -> bool:
    """gate_value pour gate_state=APPLICABLE : Mistral peut renvoyer null ou OUI/NON."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, str):
        pb = _parse_bool_string(v)
        if pb is not None:
            return pb
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return bool(v)
    return False


def coerce_gate_threshold_value(v: Any) -> float | None:
    """Seuil gate : nombre, chaîne numérique, ou null ; illisible → null."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace("\u202f", "").replace("\u00a0", " ")
        if not s or s.lower() in ("n/a", "na", "-", "—"):
            return None
        try:
            return float(s.replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return None
    return None


ABSENT_ON_EMPTY = frozenset(
    {
        "procedure_reference",
        "submission_deadline",
        "submission_mode",
        "result_type",
        "technical_threshold",
        "negotiation_allowed",
        "ponderation_coherence",
        "has_sci_conditions_signed",
        "has_iapg_signed",
        "has_non_sanction",
        "ariba_network_required",
        "sci_sustainability_pct",
        "has_nif",
        "has_rccm",
        "has_statutes",
        "has_quitus_fiscal",
        "has_certificat_non_faillite",
        "local_content_present",
        "community_employment_present",
        "environment_commitment_present",
        "gender_inclusion_present",
        "supplier_name_normalized",
        "supplier_identifier_raw",
        "supplier_address_raw",
    }
)

LIST_VALUE_FIELDS = frozenset({"submission_mode", "lot_scope", "zone_scope"})

_IDENT_BOOL_KEYS = frozenset({"has_nif", "has_rccm", "has_rib"})

_VALID_LINE_LEVELS = frozenset({"detail", "subtotal", "total"})


def normalize_boolean(value: Any, field_name: str) -> Any:
    """Normalise un booléen potentiellement string ; sentinelles texte inchangées."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value in ("ABSENT", "NOT_APPLICABLE"):
            return value
        if value == "":
            return None
        pb = _parse_bool_string(value)
        if pb is not None:
            return pb
        logger.warning(
            "booléen non reconnu pour %s : %r — laissé inchangé",
            field_name,
            value,
        )
        return value
    return value


def normalize_sentinel(value: Any, field_name: str) -> Any:
    """Convertit '' vers la sentinelle appropriée (D5)."""
    if not isinstance(value, str):
        return value
    if value != "":
        return value
    if field_name in ABSENT_ON_EMPTY:
        return "ABSENT"
    return None


def normalize_extraction_field(
    field: dict[str, Any], field_name: str
) -> dict[str, Any]:
    """Normalise un champ {value, confidence, evidence}."""
    if not isinstance(field, dict):
        return field
    v = field.get("value")

    if isinstance(v, str) and v == "":
        if field_name in LIST_VALUE_FIELDS:
            field["value"] = []
        elif field_name in ABSENT_ON_EMPTY:
            field["value"] = "ABSENT"
        elif field_name in BOOLEAN_FIELDS:
            field["value"] = None
        else:
            field["value"] = None
    elif field_name in BOOLEAN_FIELDS:
        field["value"] = normalize_boolean(v, field_name)

    if field.get("evidence") == "":
        field["evidence"] = "ABSENT"
    return field


def _looks_like_field_value(d: dict[str, Any]) -> bool:
    return (
        "value" in d
        and "confidence" in d
        and "evidence" in d
        and isinstance(d.get("confidence"), (int, float))
    )


def _normalize_extraction_fields_recursive(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "line_items":
                continue
            if isinstance(v, dict) and _looks_like_field_value(v):
                normalize_extraction_field(v, k)
            elif k in _IDENT_BOOL_KEYS and isinstance(v, str):
                pb = _parse_bool_string(v)
                if pb is not None:
                    obj[k] = pb
            elif isinstance(v, str) and v == "" and k in ABSENT_ON_EMPTY:
                obj[k] = normalize_sentinel(v, k)
            elif isinstance(v, (dict, list)):
                _normalize_extraction_fields_recursive(v)
    elif isinstance(obj, list):
        for el in obj:
            _normalize_extraction_fields_recursive(el)


def _coerce_review_flag(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        pb = _parse_bool_string(v)
        if pb is not None:
            return pb
    return False


def ensure_item_line_no_parseable(v: Any) -> None:
    """Valide qu'une entrée Mistral est un nombre utilisable (y compris hiérarchique 1.1)."""
    if v is None:
        raise ValueError("item_line_no ne peut pas être null")
    if isinstance(v, bool):
        raise ValueError("item_line_no ne peut pas être booléen")
    if isinstance(v, str):
        s = v.strip().replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
        if not s:
            raise ValueError("item_line_no ne peut pas être vide")
        try:
            float(s.replace(",", "."))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"item_line_no non numérique : {v!r}") from exc
        return
    if isinstance(v, int | float):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"item_line_no invalide : {v}")
        return
    raise ValueError(f"item_line_no type inattendu : {type(v)}")


def normalize_item_line_no_value(v: Any) -> int:
    """
    Int strict pour LineItem après resequence.
    Lève pour null, vide, non numérique, ou float hiérarchique (1.1) non resequencé.
    """
    if v is None:
        raise ValueError("item_line_no ne peut pas être null")
    if isinstance(v, bool):
        raise ValueError("item_line_no ne peut pas être booléen")
    if isinstance(v, str):
        s = v.strip().replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
        if not s:
            raise ValueError("item_line_no ne peut pas être vide")
        try:
            fv = float(s.replace(",", "."))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"item_line_no non numérique : {v!r}") from exc
    elif isinstance(v, int | float):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"item_line_no invalide : {v}")
        fv = float(v)
    else:
        raise ValueError(f"item_line_no type inattendu : {type(v)}")
    if abs(fv - round(fv)) > 1e-9:
        raise ValueError(
            "item_line_no hiérarchique — appliquer normalize_annotation_output avant validation"
        )
    return int(round(fv))


_ALLOWED_LINE_CHECK_VALUES = frozenset(m.value for m in LineCheck)


def _coerce_line_total_check_in_line_item(item: dict[str, Any]) -> None:
    """LS / Mistral : libellés hors enum (ex. SUBTOTAL_INTERMEDIATE) → valeur schéma ; recalcul ensuite."""
    raw = item.get("line_total_check")
    if raw in _ALLOWED_LINE_CHECK_VALUES:
        return
    if isinstance(raw, LineCheck):
        item["line_total_check"] = raw.value
        return
    if isinstance(raw, str):
        s = raw.strip().upper()
        if s in _ALLOWED_LINE_CHECK_VALUES:
            item["line_total_check"] = s
            return
    item["line_total_check"] = LineCheck.NON_VERIFIABLE.value


def resequence_line_items(line_items: list[Any]) -> list[dict[str, Any]]:
    """
    Réattribue item_line_no 1..n, supprime parent_subtotal_no (D2), défaut level (D3).
    """
    out: list[dict[str, Any]] = []
    for raw in line_items:
        if not isinstance(raw, dict):
            raise ValueError("line_items : chaque entrée doit être un objet")
        ensure_item_line_no_parseable(raw.get("item_line_no"))
        out.append(raw)
    for i, item in enumerate(out, start=1):
        item["item_line_no"] = i
        item.pop("parent_subtotal_no", None)
        lvl = item.get("level")
        if isinstance(lvl, LineItemLevel):
            item["level"] = lvl.value
        elif isinstance(lvl, str):
            ls = lvl.strip().lower()
            if ls in ("detail", "subtotal", "total"):
                item["level"] = ls
            else:
                item["level"] = "detail"
        else:
            item["level"] = "detail"
        _coerce_line_total_check_in_line_item(item)
    return out


def align_review_required(json_output: dict[str, Any]) -> dict[str, Any]:
    """D6 — _meta.review_required est autoritaire ; financier aligné."""
    meta = json_output.setdefault("_meta", {})
    meta_r = _coerce_review_flag(meta.get("review_required"))
    c4 = json_output.get("couche_4_atomic")
    fin_r = False
    if isinstance(c4, dict):
        financier = c4.get("financier")
        if isinstance(financier, dict) and "review_required" in financier:
            fin_r = _coerce_review_flag(financier.get("review_required"))
    final = meta_r or fin_r
    if isinstance(c4, dict):
        fin = c4.get("financier")
        if isinstance(fin, dict):
            fin["review_required"] = final
    meta["review_required"] = final
    return json_output


def clean_ambiguities(json_output: dict[str, Any]) -> dict[str, Any]:
    amb = json_output.get("ambiguites")
    if not isinstance(amb, list):
        return json_output
    json_output["ambiguites"] = [
        a for a in amb if a != "AMBIG-6_schema_validation_errors"
    ]
    return json_output


# Doit rester aligné sur Couche2Core (extra=forbid) — Mistral ajoute parfois evidence/confidence ici.
_COUCHE2_CORE_ALLOWED_KEYS = frozenset(
    {
        "procedure_reference",
        "issuing_entity",
        "project_name",
        "lot_count",
        "lot_scope",
        "zone_scope",
        "submission_deadline",
        "submission_mode",
        "result_type",
        "technical_threshold",
        "visit_required",
        "sample_required",
        "negotiation_allowed",
        "regime_dominant",
        "modalite_paiement",
        "eligibility_gates",
        "scoring_structure",
        "ponderation_coherence",
    }
)

# Clés explicitement connues comme parasites ajoutées par le LLM au niveau couche_2_core.
_COUCHE2_CORE_PARASITE_KEYS = frozenset(
    {
        "evidence",
        "confidence",
    }
)


def _strip_couche_2_core_extras(json_output: dict[str, Any]) -> None:
    """Retire les clés parasites au niveau couche_2_core (LLM hors schéma).

    Ne supprime que les clés explicitement connues comme parasites (evidence/confidence),
    afin de laisser Pydantic rejeter les autres clés inconnues via extra="forbid".
    """
    c2 = json_output.get("couche_2_core")
    if not isinstance(c2, dict):
        return
    parasites = [k for k in c2 if k in _COUCHE2_CORE_PARASITE_KEYS]
    for k in parasites:
        del c2[k]
    if parasites:
        logger.warning(
            "couche_2_core : clés parasites retirées avant validation stricte : %s",
            parasites,
        )


def _coerce_ponderation_coherence_to_str(json_output: dict[str, Any]) -> None:
    """Couche2Core.ponderation_coherence est un str schéma ; le LLM renvoie souvent un FieldValue."""
    c2 = json_output.get("couche_2_core")
    if not isinstance(c2, dict):
        return
    raw = c2.get("ponderation_coherence")
    if isinstance(raw, dict):
        # Traiter également les dicts partiels qui contiennent au moins une clé "value",
        # afin de ne pas convertir tout le dict en str et masquer l'intention du LLM.
        if "value" in raw:
            val = raw.get("value")
            if val in (None, ""):
                c2["ponderation_coherence"] = "ABSENT"
            elif isinstance(val, str):
                c2["ponderation_coherence"] = val
            else:
                c2["ponderation_coherence"] = str(val)
        else:
            # Dict sans clé "value" : sérialiser proprement avec limite de taille.
            c2["ponderation_coherence"] = json.dumps(raw, ensure_ascii=False)[:500]
    elif raw is None:
        c2["ponderation_coherence"] = "ABSENT"
    elif not isinstance(raw, str):
        # list ou autre type non-scalaire : sérialiser proprement avec limite de taille.
        if isinstance(raw, (list, dict)):
            c2["ponderation_coherence"] = json.dumps(raw, ensure_ascii=False)[:500]
        else:
            c2["ponderation_coherence"] = str(raw)


# Bloc financier — champs au format FieldValue (Mistral renvoie parfois un nombre seul pour total_price, etc.)
_FINANCIER_FIELDVALUE_KEYS = frozenset(
    {
        "total_price",
        "currency",
        "price_basis",
        "price_date",
        "delivery_delay_days",
        "validity_days",
        "discount_terms_present",
    }
)


def _snap_fieldvalue_confidence(c: Any) -> float:
    """Ramène une confidence vers la grille FieldValue 0.6 / 0.8 / 1.0."""
    if c in (0.6, 0.8, 1.0):
        return float(c)
    try:
        x = float(c)
    except (TypeError, ValueError):
        return 0.8
    if x <= 0.7:
        return 0.6
    if x <= 0.9:
        return 0.8
    return 1.0


def _coerce_financier_field_values(json_output: dict[str, Any]) -> None:
    """Scalaires ou dicts incomplets → FieldValue avant validation Pydantic."""
    c4 = json_output.get("couche_4_atomic")
    if not isinstance(c4, dict):
        return
    fin = c4.get("financier")
    if not isinstance(fin, dict):
        return
    for fk in _FINANCIER_FIELDVALUE_KEYS:
        if fk not in fin:
            continue
        val = fin[fk]
        if isinstance(val, dict) and _looks_like_field_value(val):
            continue
        if isinstance(val, dict) and "value" in val:
            fin[fk] = {
                "value": val["value"],
                "confidence": _snap_fieldvalue_confidence(val.get("confidence", 0.8)),
                "evidence": str(val.get("evidence") or "") or "ABSENT",
            }
            continue
        if not isinstance(val, dict):
            fin[fk] = {
                "value": val,
                "confidence": 0.8,
                "evidence": "ABSENT",
            }
            continue
        fin[fk] = {
            "value": val,
            "confidence": 0.8,
            "evidence": "ABSENT",
        }


def _scope_list_item_to_str(item: Any) -> str:
    """Mistral renvoie parfois des objets dans lot_scope / zone_scope — schéma exige list[str]."""
    if isinstance(item, str):
        return item
    if item is None:
        return ""
    if isinstance(item, bool):
        return str(item)
    if isinstance(item, (int, float)):
        return str(item)
    if isinstance(item, dict):
        for k in ("lot", "label", "value", "name", "id", "description", "zone"):
            v = item.get(k)
            if v is not None and v != "":
                return str(v)
        return json.dumps(item, ensure_ascii=False)[:500]
    return str(item)


def _coerce_identifiants_scope_lists(json_output: dict[str, Any]) -> None:
    ident = json_output.get("identifiants")
    if not isinstance(ident, dict):
        return
    for key in ("lot_scope", "zone_scope"):
        v = ident.get(key)
        if not isinstance(v, list):
            continue
        ident[key] = [_scope_list_item_to_str(x) for x in v]


def normalize_annotation_output(json_output: dict[str, Any]) -> dict[str, Any]:
    """
    Point d'entrée unique — après parsing JSON Mistral, avant validation schéma.
    Ordre : nettoyage couche_2_core → sentinelles / FieldValue → line_items → review_required → ambiguïtés.
    """
    _strip_couche_2_core_extras(json_output)
    _coerce_financier_field_values(json_output)
    _coerce_identifiants_scope_lists(json_output)
    _normalize_extraction_fields_recursive(json_output)
    _coerce_ponderation_coherence_to_str(json_output)

    c4 = json_output.get("couche_4_atomic")
    if isinstance(c4, dict):
        financier = c4.get("financier")
        if isinstance(financier, dict) and isinstance(
            financier.get("line_items"), list
        ):
            financier["line_items"] = resequence_line_items(financier["line_items"])

    align_review_required(json_output)
    clean_ambiguities(json_output)
    return json_output


normalize_item_line_no_strict = normalize_item_line_no_value
normalize_item_line_no = normalize_item_line_no_value


class LineItem(BaseModel):
    """Ligne de prix — schéma ADR-015 strict + ARCH-03 hiérarchie."""

    model_config = {"extra": "forbid"}

    item_line_no: int
    item_description_raw: str
    unit_raw: str
    quantity: float
    unit_price: float
    line_total: float
    line_total_check: LineCheck
    confidence: float
    evidence: str
    level: LineItemLevel = LineItemLevel.DETAIL

    @field_validator("level", mode="before")
    @classmethod
    def coerce_level(cls, v: Any) -> str:
        if v is None or v == "":
            return LineItemLevel.DETAIL.value
        if isinstance(v, LineItemLevel):
            return v.value
        s = str(v).strip().lower()
        if s in ("detail", "subtotal", "total"):
            return s
        return LineItemLevel.DETAIL.value

    @field_validator("item_line_no", mode="before")
    @classmethod
    def coerce_item_line_no(cls, v: Any) -> int:
        return normalize_item_line_no_value(v)

    @model_validator(mode="after")
    def validate_unit_not_empty(self) -> LineItem:
        if not self.unit_raw or self.unit_raw.strip() == "":
            raise ValueError(
                f"unit_raw vide — item {self.item_line_no}. "
                "Utiliser 'non_precise' si unité absente."
            )
        return self

    @model_validator(mode="after")
    def validate_confidence(self) -> LineItem:
        if self.confidence not in {0.6, 0.8, 1.0}:
            raise ValueError(f"confidence={self.confidence} interdit sur LineItem.")
        return self


def _total_price_field_to_float(fv: FieldValue) -> float | None:
    """Parse financier.total_price.value — même logique que annotation_qa.parse_loose_money_float (OCR)."""
    return parse_loose_money_float(fv.value)


def _anomaly_money_token(amount: float) -> str:
    """Montant dans un code ANOMALY : arrondi 2 décimales, pas de troncature int (évite collisions)."""
    rounded = round(float(amount), 2)
    return f"{rounded:.2f}".replace(".", "p")


class Gate(BaseModel):
    """Gate métier — liste figée à 10. E-17 : confidence 0.6|0.8|1.0."""

    model_config = {"extra": "forbid"}

    gate_name: GateName
    gate_value: bool | None
    gate_state: GateState
    gate_threshold_value: float | None
    gate_reason_raw: str
    gate_evidence_hint: str
    confidence: float

    @model_validator(mode="after")
    def validate_gate_confidence(self) -> Gate:
        if self.confidence not in {0.6, 0.8, 1.0}:
            raise ValueError(
                f"gate {self.gate_name}: confidence={self.confidence} interdit. "
                "Valeurs autorisées : 0.6, 0.8, 1.0"
            )
        return self

    @model_validator(mode="after")
    def validate_gate_coherence(self) -> Gate:
        if self.gate_state == GateState.NOT_APPLICABLE and self.gate_value is not None:
            raise ValueError(
                f"{self.gate_name}: gate_state=NOT_APPLICABLE exige gate_value=null."
            )
        if self.gate_state == GateState.APPLICABLE and self.gate_value is None:
            raise ValueError(
                f"{self.gate_name}: gate_state=APPLICABLE "
                "exige gate_value=true ou false."
            )
        return self


# ─────────────────────────────────────────────
# COUCHES — structure minimale pour validation
# ─────────────────────────────────────────────


class Couche1Routing(BaseModel):
    model_config = {"extra": "forbid"}

    procurement_family_main: str
    procurement_family_sub: str
    taxonomy_core: str
    taxonomy_client_adapter: str
    document_stage: str
    document_role: str


class Couche2Core(BaseModel):
    model_config = {"extra": "forbid"}

    procedure_reference: FieldValue
    issuing_entity: FieldValue
    project_name: FieldValue
    lot_count: FieldValue
    lot_scope: FieldValue
    zone_scope: FieldValue
    submission_deadline: FieldValue
    submission_mode: FieldValue
    result_type: FieldValue
    technical_threshold: FieldValue
    visit_required: FieldValue
    sample_required: FieldValue
    negotiation_allowed: FieldValue
    regime_dominant: FieldValue
    modalite_paiement: FieldValue
    eligibility_gates: list[Any]
    scoring_structure: list[Any]
    ponderation_coherence: str


class Couche3PolicySci(BaseModel):
    model_config = {"extra": "forbid"}

    has_sci_conditions_signed: FieldValue
    has_iapg_signed: FieldValue
    has_non_sanction: FieldValue
    ariba_network_required: FieldValue
    sci_sustainability_pct: FieldValue


class ConformiteAdmin(BaseModel):
    model_config = {"extra": "forbid"}

    has_nif: FieldValue
    has_rccm: FieldValue
    has_rib: FieldValue
    has_id_representative: FieldValue
    has_statutes: FieldValue
    has_quitus_fiscal: FieldValue
    has_certificat_non_faillite: FieldValue


class CapaciteServices(BaseModel):
    model_config = {"extra": "forbid"}

    similar_assignments_count: FieldValue
    lead_expert_years: FieldValue
    lead_expert_similar_projects_count: FieldValue
    team_composition_present: FieldValue
    methodology_present: FieldValue
    workplan_present: FieldValue
    qa_plan_present: FieldValue
    ethics_plan_present: FieldValue


class CapaciteWorks(BaseModel):
    model_config = {"extra": "forbid"}

    execution_delay_days: FieldValue
    work_methodology_present: FieldValue
    environment_plan_present: FieldValue
    site_visit_pv_present: FieldValue
    equipment_list_present: FieldValue
    key_staff_present: FieldValue
    local_labor_commitment_present: FieldValue


class CapaciteGoods(BaseModel):
    model_config = {"extra": "forbid"}

    client_references_present: FieldValue
    warranty_present: FieldValue
    delivery_schedule_present: FieldValue
    warehouse_capacity_present: FieldValue
    stock_sufficiency_present: FieldValue
    product_specs_present: FieldValue
    official_distribution_license_present: FieldValue
    sample_submission_present: FieldValue
    phytosanitary_cert_present: FieldValue
    bank_credit_line_present: FieldValue


class Durabilite(BaseModel):
    model_config = {"extra": "forbid"}

    local_content_present: FieldValue
    community_employment_present: FieldValue
    environment_commitment_present: FieldValue
    gender_inclusion_present: FieldValue
    sustainability_certifications: FieldValue


class Financier(BaseModel):
    model_config = {"extra": "forbid"}

    financial_layout_mode: str
    pricing_scope: str
    total_price: FieldValue
    currency: FieldValue
    price_basis: FieldValue
    price_date: FieldValue
    delivery_delay_days: FieldValue
    validity_days: FieldValue
    discount_terms_present: FieldValue
    review_required: bool
    line_items: list[LineItem]


class Couche4Atomic(BaseModel):
    model_config = {"extra": "forbid"}

    conformite_admin: ConformiteAdmin
    capacite_services: CapaciteServices
    capacite_works: CapaciteWorks
    capacite_goods: CapaciteGoods
    durabilite: Durabilite
    financier: Financier


class SupplierContactRedacted(BaseModel):
    """Bloc pseudonymisé — rempli à l’export LS ; absent à la sortie Mistral brute."""

    model_config = {"extra": "forbid"}

    pseudo: str | None = None
    present: bool
    redacted: bool


class Identifiants(BaseModel):
    model_config = {"extra": "forbid"}

    supplier_name_raw: str
    supplier_name_normalized: str
    supplier_legal_form: str
    supplier_identifier_raw: str
    has_nif: str | bool
    has_rccm: str | bool
    has_rib: str | bool
    supplier_address_raw: str
    supplier_phone_raw: str
    supplier_email_raw: str
    quitus_fiscal_date: str
    cert_non_faillite_date: str
    case_id: str
    supplier_id: str
    lot_scope: list[str]
    zone_scope: list[str]
    supplier_phone: SupplierContactRedacted | None = None
    supplier_email: SupplierContactRedacted | None = None


class Meta(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: Literal["v3.0.1d"]
    framework_version: Literal["annotation-framework-v3.0.1d"]
    mistral_model_used: str
    review_required: bool
    annotation_status: str
    list_null_reason: dict[str, Any]
    page_range: dict[str, Any]
    parent_document_id: str
    parent_document_role: str
    supplier_inherited_from: str | None
    # ARCH-02 — traçabilité routeur (déterministe / fallback LLM borné)
    routing_source: str | None = None
    routing_matched_rule: str | None = None
    routing_confidence: float | None = None
    # ARCH-04 — raisons review financier (liste optionnelle)
    review_reasons: list[str] | None = None


# ─────────────────────────────────────────────
# MODÈLE RACINE
# ─────────────────────────────────────────────


class DMSAnnotation(BaseModel):
    """
    Schéma complet DMS v3.0.1d.
    extra=forbid : toute clé hors schéma = ValidationError.
    Les 10 gates sont validés en ordre et en nombre.
    line_total_check est recalculé par le backend.
    """

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def normalize_annotation_before(cls, data: Any) -> Any:
        """
        JSON-FIX-ANNOT-01-v2 — normalisation types / sentinelles avant contrat Pydantic.
        Copie profonde : le dict passé à model_validate n'est pas muté sur place.
        """
        if isinstance(data, dict):
            return normalize_annotation_output(copy.deepcopy(data))
        return data

    couche_1_routing: Couche1Routing
    couche_2_core: Couche2Core
    couche_3_policy_sci: Couche3PolicySci
    couche_4_atomic: Couche4Atomic
    couche_5_gates: list[Gate]
    identifiants: Identifiants
    ambiguites: list[str]
    meta: Meta = Field(alias="_meta")

    @model_validator(mode="after")
    def validate_gates_count_and_order(self) -> DMSAnnotation:
        """Les 10 gates dans l'ordre exact — ni plus ni moins."""
        expected = [g.value for g in GateName]
        actual = [g.gate_name.value for g in self.couche_5_gates]
        if actual != expected:
            raise ValueError(
                f"couche_5_gates incorrect.\nAttendu : {expected}\nReçu    : {actual}"
            )
        return self

    @model_validator(mode="after")
    def recalculate_line_total_check(self) -> DMSAnnotation:
        """
        Recalcul mathématique par le backend — jamais par Mistral.
        ARCH-03 : level=subtotal → pas de qty×price ; cohérence globale vs total_price.

        Tolérance : écart relatif |expected−actual|/max(actual,1) ≤ 0,01 (~1 %).
        quantity ou unit_price « falsy » (0.0 inclus) → NON_VERIFIABLE (pas d’assertion math).
        """
        fin = self.couche_4_atomic.financier
        items = fin.line_items

        for item in items:
            if item.level in (LineItemLevel.SUBTOTAL, LineItemLevel.TOTAL):
                item.line_total_check = LineCheck.SUBTOTAL_NOT_CHECKED_HERE
                continue
            if item.quantity and item.unit_price:
                expected = round(item.quantity * item.unit_price, 2)
                actual = round(item.line_total, 2)
                ecart = abs(expected - actual) / max(actual, 1)
                if ecart <= 0.01:
                    item.line_total_check = LineCheck.OK
                else:
                    item.line_total_check = LineCheck.ANOMALY
                    ambig = (
                        f"AMBIG-3_item_{item.item_line_no}_math_anomaly"
                        f"_expected_{expected}_got_{actual}"
                    )
                    if ambig not in self.ambiguites:
                        self.ambiguites.append(ambig)
            else:
                item.line_total_check = LineCheck.NON_VERIFIABLE

        total_val = _total_price_field_to_float(fin.total_price)
        if total_val is None or not items:
            return self

        subtotals = [
            i for i in items if i.level == LineItemLevel.SUBTOTAL
        ]  # TOTAL exclu — évite double comptage avec une ligne grand total
        details = [i for i in items if i.level == LineItemLevel.DETAIL]
        tol = max(1.0, abs(total_val) * 0.01)

        sum_sub = sum(i.line_total for i in subtotals) if subtotals else 0.0
        sum_det = sum(i.line_total for i in details) if details else 0.0

        ok_sub = bool(subtotals) and abs(sum_sub - total_val) <= tol
        ok_det = bool(details) and abs(sum_det - total_val) <= tol
        reconciled = ok_sub or ok_det

        if not reconciled:
            if subtotals and abs(sum_sub - total_val) > tol:
                code = (
                    f"ANOMALY_subtotals_sum_{_anomaly_money_token(sum_sub)}"
                    f"_vs_total_price_{_anomaly_money_token(total_val)}"
                )
                if code not in self.ambiguites:
                    self.ambiguites.append(code)
            if details and abs(sum_det - total_val) > tol:
                code = (
                    f"ANOMALY_details_sum_{_anomaly_money_token(sum_det)}"
                    f"_vs_total_price_{_anomaly_money_token(total_val)}"
                )
                if code not in self.ambiguites:
                    self.ambiguites.append(code)

        return self
