"""R2 — Requirements Instantiation."""

from __future__ import annotations

import logging
from typing import Any

from src.procurement.compliance_models_m13 import (
    ApprovalStep,
    ControlOrgan,
    EvaluationRequirements,
    GuaranteeRequirements,
    MinimumBidsRequirement,
    NormativeReference,
    ProcedureRequirements,
    RegulatoryDocumentValidityRule,
    RegulatoryRegime,
    RequiredDocument,
    RequiredDocumentSet,
    TimelineRequirements,
)
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader
from src.procurement.regulatory_yaml_validity import RegulatoryYamlValidityLoader

logger = logging.getLogger(__name__)


class RequirementsInstantiator:
    def __init__(
        self,
        config_loader: RegulatoryConfigLoader,
        validity_loader: RegulatoryYamlValidityLoader,
    ) -> None:
        self.config = config_loader
        self.validity = validity_loader

    def instantiate(self, regime: RegulatoryRegime) -> ProcedureRequirements:
        fw = regime.framework.value
        bundle = self.config.load_framework_bundle(fw)
        proc = regime.procedure_type.value
        tier_name = regime.threshold_tier.tier_name

        req_docs = self._load_required_documents(bundle, proc, tier_name)
        timelines = self._load_timelines(bundle, proc, regime)
        organs = self._load_organs(bundle, proc)
        evaluation = self._load_evaluation(bundle, proc, regime)
        guarantees = self._load_guarantees(bundle, proc)
        approval = self._load_approval_chain(bundle)
        min_bids = self._load_minimum_bids(bundle, proc)
        validity_rules = self.validity.load(fw)
        self._link_validity(req_docs, validity_rules)

        return ProcedureRequirements(
            regime=regime,
            required_documents=req_docs,
            timeline_requirements=timelines,
            control_organs=organs,
            evaluation_requirements=evaluation,
            guarantee_requirements=guarantees,
            approval_chain=approval,
            minimum_bids=min_bids,
            document_validity_rules=validity_rules,
        )

    def _link_validity(
        self,
        docs: RequiredDocumentSet,
        _rules: list[RegulatoryDocumentValidityRule],
    ) -> None:
        for doc in docs.supplier_documents + docs.buyer_documents:
            if doc.admin_subtype and not doc.validity_rule_ref:
                doc.validity_rule_ref = doc.admin_subtype

    def _load_required_documents(
        self, bundle: dict[str, Any], procedure: str, tier_name: str
    ) -> RequiredDocumentSet:
        rd = bundle.get("required_documents") or {}
        buyer: list[RequiredDocument] = []
        by_proc = (rd.get("buyer_documents") or {}).get("by_procedure") or {}
        for doc in by_proc.get(procedure, []) or []:
            buyer.append(self._one_required(doc, rd.get("framework", "")))

        supplier: list[RequiredDocument] = []
        sd = rd.get("supplier_documents") or {}
        for doc in sd.get("common") or []:
            supplier.append(self._one_required(doc, rd.get("framework", "")))
        by_th = sd.get("by_threshold") or {}
        for doc in by_th.get(tier_name, []) or []:
            supplier.append(self._one_required(doc, rd.get("framework", "")))

        return RequiredDocumentSet(
            buyer_documents=buyer,
            supplier_documents=supplier,
        )

    def _one_required(self, doc: dict[str, Any], fw: str) -> RequiredDocument:
        return RequiredDocument(
            document_name=doc["document_name"],
            admin_subtype=doc.get("admin_subtype"),
            is_mandatory=doc.get("is_mandatory", True),
            is_eliminatory=doc.get("is_eliminatory", False),
            applicable_stages=list(doc.get("applicable_stages") or []),
            normative_reference=NormativeReference(
                framework=fw,
                article=doc.get("article"),
                description=doc.get("document_name", ""),
            ),
            validity_rule_ref=doc.get("validity_rule_ref"),
        )

    def _load_timelines(
        self, bundle: dict[str, Any], procedure: str, regime: RegulatoryRegime
    ) -> TimelineRequirements:
        tl = bundle.get("timelines") or {}
        by_p = (tl.get("by_procedure") or {}).get(procedure) or {}
        hum = tl.get("humanitarian_override") or {}
        return TimelineRequirements(
            publication_delay_days=by_p.get("publication_delay_days"),
            submission_period_days=by_p.get("submission_period_days"),
            bid_validity_period_days=by_p.get("bid_validity_period_days"),
            evaluation_max_days=by_p.get("evaluation_max_days"),
            standstill_period_days=by_p.get("standstill_period_days"),
            contract_signature_max_days=by_p.get("contract_signature_max_days"),
            humanitarian_override=bool(hum.get("enabled")),
            humanitarian_reduction_pct=float(hum.get("reduction_pct", 0) or 0),
            normative_references=[],
        )

    def _load_organs(
        self, bundle: dict[str, Any], procedure: str
    ) -> list[ControlOrgan]:
        co = bundle.get("control_organs") or {}
        organs_raw = co.get("organs") or {}
        out: list[ControlOrgan] = []
        for _k, o in organs_raw.items():
            req = list(o.get("required_for_procedure") or [])
            if req and "all" not in req and procedure not in req:
                continue
            out.append(
                ControlOrgan(
                    organ_name=o["organ_name"],
                    organ_role=o["organ_role"],
                    required_for_procedure=req,
                    quorum_rule=o.get("quorum_rule"),
                    composition_rule=o.get("composition_rule"),
                    normative_reference=NormativeReference(
                        framework=co.get("framework", ""),
                        article=o.get("article"),
                        description=o["organ_name"],
                    ),
                )
            )
        return out

    def _load_evaluation(
        self, bundle: dict[str, Any], procedure: str, regime: RegulatoryRegime
    ) -> EvaluationRequirements:
        pt = bundle.get("procedure_types") or {}
        defaults = (pt.get("procedure_defaults") or {}).get(procedure) or {}
        method = defaults.get("evaluation_method", "unknown")
        allowed = (
            "lowest_price",
            "mieux_disant",
            "quality_cost_based",
            "fixed_budget",
            "consultant_qualification",
            "unknown",
        )
        if method not in allowed:
            method = "unknown"
        fw = pt.get("framework") or ""

        eval_cfg = bundle.get("evaluation_criteria") or {}
        by_method = (eval_cfg.get("by_method") or {}).get(method) or {}

        technical_weight = by_method.get("technical_weight")
        financial_weight = by_method.get("financial_weight")
        sustainability_weight = by_method.get("sustainability_weight")
        technical_threshold = by_method.get("technical_threshold")

        return EvaluationRequirements(
            evaluation_method=method,
            technical_weight=technical_weight,
            financial_weight=financial_weight,
            sustainability_weight=sustainability_weight,
            technical_threshold=technical_threshold,
            normative_reference=NormativeReference(
                framework=fw,
                description=f"default evaluation for {procedure}",
            ),
        )

    def _load_guarantees(
        self, bundle: dict[str, Any], procedure: str
    ) -> GuaranteeRequirements:
        return GuaranteeRequirements(
            bid_guarantee_required=procedure
            in ("open_national", "open_international", "request_for_quotation"),
        )

    def _load_approval_chain(self, bundle: dict[str, Any]) -> list[ApprovalStep]:
        ac = bundle.get("approval_chain") or {}
        steps_raw = ac.get("steps") or []
        fw = ac.get("framework") or ""
        steps: list[ApprovalStep] = []
        for s in steps_raw:
            steps.append(
                ApprovalStep(
                    step_name=s.get("step_name", "unknown"),
                    authority=s.get("authority", "unknown"),
                    threshold_applies=bool(s.get("threshold_applies", False)),
                    is_mandatory=bool(s.get("is_mandatory", True)),
                    normative_reference=NormativeReference(
                        framework=fw,
                        article=s.get("article"),
                        description=s.get("description", ""),
                    ),
                )
            )
        return steps

    def _load_minimum_bids(
        self, bundle: dict[str, Any], procedure: str
    ) -> MinimumBidsRequirement:
        return MinimumBidsRequirement(
            minimum_bids=(
                3 if procedure in ("request_for_quotation", "open_national") else 1
            ),
            normative_reference=NormativeReference(
                framework=bundle.get("thresholds", {}).get("framework", ""),
                description="minimum bids default",
            ),
        )
