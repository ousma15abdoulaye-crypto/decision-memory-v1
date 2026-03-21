"""
Validateur Pydantic v2 — schéma DMS v3.0.1d
Couche 2 de contrôle — après parsing Mistral.
Toute clé inconnue = rejetée (extra="forbid").
line_total_check recalculé par le backend — jamais par Mistral.
ADR-015 — 2026-03-16
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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
    """ARCH-03 — hiérarchie budget (récap vs détail)."""

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
    level: LineItemLevel
    parent_subtotal_no: int | None = None

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
    """Parse financier.total_price.value (aligné parse_loose_money_float)."""
    val = fv.value
    if val in (None, "", "ABSENT", "NOT_APPLICABLE"):
        return None
    s = str(val).replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


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
        ARCH-03 : level=subtotal|total → pas de qty×price ; cohérence globale vs total_price.

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

        subtotals = [i for i in items if i.level == LineItemLevel.SUBTOTAL]
        details = [i for i in items if i.level == LineItemLevel.DETAIL]
        tol = max(1.0, abs(total_val) * 0.01)

        if subtotals:
            sum_sub = sum(i.line_total for i in subtotals)
            if abs(sum_sub - total_val) > tol:
                code = (
                    f"ANOMALY_subtotals_sum_{int(sum_sub)}"
                    f"_vs_total_price_{int(total_val)}"
                )
                if code not in self.ambiguites:
                    self.ambiguites.append(code)
        else:
            sum_det = sum(i.line_total for i in details)
            if abs(sum_det - total_val) > tol:
                code = (
                    f"ANOMALY_details_sum_{int(sum_det)}"
                    f"_vs_total_price_{int(total_val)}"
                )
                if code not in self.ambiguites:
                    self.ambiguites.append(code)

        return self
