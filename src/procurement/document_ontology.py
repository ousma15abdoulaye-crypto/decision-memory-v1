"""
M12 V6 — Document Ontology: all closed-list enums for the procurement recognizer.

Aligné sur corpus annoté 100 annotations 5 couches, schéma v3.0.1d.
Extensible via configuration YAML, pas via modification de code (sauf ProcurementFramework).
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class ProcurementFramework(StrEnum):
    SCI = "sci"
    DGMP_MALI = "dgmp_mali"
    WORLD_BANK = "world_bank"
    AFD = "afd"
    BAD = "bad"
    EU = "eu"
    MINING_LOCAL = "mining_local"
    OHADA = "ohada"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@unique
class ProcurementFamily(StrEnum):
    GOODS = "goods"
    SERVICES = "services"
    WORKS = "works"
    CONSULTANCY = "consultancy"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@unique
class ProcurementFamilySub(StrEnum):
    GENERIC = "generic"
    CONSTRUCTION = "construction"
    REHABILITATION = "rehabilitation"
    FOURNITURE_BUREAU = "fourniture_bureau"
    FOURNITURE_MEDICAL = "fourniture_medical"
    FOURNITURE_IT = "fourniture_it"
    CONSULTANCY_BASELINE_STUDY = "consultancy_baseline_study"
    CONSULTANCY_EVALUATION = "consultancy_evaluation"
    CONSULTANCY_AUDIT = "consultancy_audit"
    CONSULTANCY_FORMATION = "consultancy_formation"
    EXTERNAL_LABOR = "external_labor"
    OTHER = "other"


@unique
class DocumentKindParent(StrEnum):
    TDR = "tdr"
    RFQ = "rfq"
    ITT = "itt"
    DAO = "dao"
    OFFER_TECHNICAL = "offer_technical"
    OFFER_FINANCIAL = "offer_financial"
    OFFER_COMBINED = "offer_combined"
    SUBMISSION_LETTER = "submission_letter"
    PRICE_SCHEDULE = "price_schedule"
    BOQ = "boq"
    ADMIN_DOC = "admin_doc"
    EVALUATION_DOC = "evaluation_doc"
    CONTRACT = "contract"
    PO = "po"
    GRN = "grn"
    SUPPORTING_DOC = "supporting_doc"
    MARKET_SURVEY = "market_survey"
    MERCURIALE_REFERENCE = "mercuriale"
    UNKNOWN = "unknown"


@unique
class DocumentKindSubtype(StrEnum):
    GENERIC = "generic"
    CONSTRUCTION_GOODS = "construction_goods"
    CONSTRUCTION_WORKS = "construction_works"
    CONSULTANCY_BASELINE_STUDY = "consultancy_baseline_study"
    CONSULTANCY_GENERIC = "consultancy_generic"
    WORKS = "works"
    GOODS = "goods"
    GOODS_FOURNITURE = "goods_fourniture"
    SERVICES = "services"
    FOURNITURE = "fourniture"
    POLICY = "policy"
    ADMIN = "admin"
    CERTIFICATION = "certification"
    CARTOUCHES = "cartouches"
    IT_EQUIPMENT = "it_equipment"
    MEDICAL = "medical"
    FOOD = "food"
    VEHICLE = "vehicle"
    OTHER = "other"


@unique
class DocumentLayer(StrEnum):
    NEED_DEFINITION = "need_definition_layer"
    SOURCE_RULES = "source_rules_layer"
    INVITATION = "invitation_layer"
    BID_RESPONSE = "bid_response_layer"
    EVALUATION = "evaluation_layer"
    AWARD_CONTRACT = "award_contract_layer"
    EXECUTION = "execution_layer"
    MARKET_INTELLIGENCE = "market_intelligence_layer"
    UNKNOWN = "unknown"


@unique
class DocumentStage(StrEnum):
    PLANNING = "planning"
    SOLICITATION = "solicitation"
    SUBMISSION = "submission"
    EVALUATION = "evaluation"
    AWARD = "award"
    EXECUTION = "execution"
    CLOSE_OUT = "close_out"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


@unique
class ProcedureType(StrEnum):
    OPEN_COMPETITIVE = "open_competitive"
    RESTRICTED = "restricted"
    DIRECT_PROCUREMENT = "direct_procurement"
    REQUEST_FOR_QUOTATION = "request_for_quotation"
    FRAMEWORK_AGREEMENT = "framework_agreement"
    CONSULTANCY_SELECTION = "consultancy_selection"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


@unique
class LinkNature(StrEnum):
    RESPONDS_TO = "responds_to"
    EVALUATES = "evaluates"
    FORMALIZES = "formalizes"
    ACCOMPANIES = "accompanies"
    REFINES = "refines"
    SUPERSEDES = "supersedes"
    SOURCES_FROM = "sources_from"
    PRICES_AGAINST = "prices_against"
    EXECUTES = "executes"
    RECEIVES = "receives"


@unique
class ProcessRole(StrEnum):
    OPENS_PROCESS = "opens_process"
    DEFINES_NEED = "defines_need"
    SURVEYS_MARKET = "surveys_market"
    DEFINES_RULES = "defines_rules"
    INVITES_BIDS = "invites_bids"
    RESPONDS_TO_BID = "responds_to_bid"
    EVALUATES_BIDS = "evaluates_bids"
    FORMALIZES_AWARD = "formalizes_award"
    STARTS_EXECUTION = "starts_execution"
    CONFIRMS_RECEPTION = "confirms_reception"
    SUPPORTS_PROCESS = "supports_process"
    PROVIDES_REFERENCE = "provides_reference"
    UNKNOWN = "unknown"


# Mapping: document_kind -> default document_layer
DOCUMENT_KIND_TO_LAYER: dict[DocumentKindParent, DocumentLayer] = {
    DocumentKindParent.TDR: DocumentLayer.NEED_DEFINITION,
    DocumentKindParent.RFQ: DocumentLayer.INVITATION,
    DocumentKindParent.ITT: DocumentLayer.INVITATION,
    DocumentKindParent.DAO: DocumentLayer.SOURCE_RULES,
    DocumentKindParent.OFFER_TECHNICAL: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.OFFER_FINANCIAL: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.OFFER_COMBINED: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.SUBMISSION_LETTER: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.PRICE_SCHEDULE: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.BOQ: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.ADMIN_DOC: DocumentLayer.BID_RESPONSE,
    DocumentKindParent.EVALUATION_DOC: DocumentLayer.EVALUATION,
    DocumentKindParent.CONTRACT: DocumentLayer.AWARD_CONTRACT,
    DocumentKindParent.PO: DocumentLayer.EXECUTION,
    DocumentKindParent.GRN: DocumentLayer.EXECUTION,
    DocumentKindParent.SUPPORTING_DOC: DocumentLayer.UNKNOWN,
    DocumentKindParent.MARKET_SURVEY: DocumentLayer.MARKET_INTELLIGENCE,
    DocumentKindParent.MERCURIALE_REFERENCE: DocumentLayer.MARKET_INTELLIGENCE,
    DocumentKindParent.UNKNOWN: DocumentLayer.UNKNOWN,
}

# Mapping: document_kind -> default document_stage
DOCUMENT_KIND_TO_STAGE: dict[DocumentKindParent, DocumentStage] = {
    DocumentKindParent.TDR: DocumentStage.PLANNING,
    DocumentKindParent.RFQ: DocumentStage.SOLICITATION,
    DocumentKindParent.ITT: DocumentStage.SOLICITATION,
    DocumentKindParent.DAO: DocumentStage.SOLICITATION,
    DocumentKindParent.OFFER_TECHNICAL: DocumentStage.SUBMISSION,
    DocumentKindParent.OFFER_FINANCIAL: DocumentStage.SUBMISSION,
    DocumentKindParent.OFFER_COMBINED: DocumentStage.SUBMISSION,
    DocumentKindParent.SUBMISSION_LETTER: DocumentStage.SUBMISSION,
    DocumentKindParent.PRICE_SCHEDULE: DocumentStage.SUBMISSION,
    DocumentKindParent.BOQ: DocumentStage.SUBMISSION,
    DocumentKindParent.ADMIN_DOC: DocumentStage.SUBMISSION,
    DocumentKindParent.EVALUATION_DOC: DocumentStage.EVALUATION,
    DocumentKindParent.CONTRACT: DocumentStage.AWARD,
    DocumentKindParent.PO: DocumentStage.EXECUTION,
    DocumentKindParent.GRN: DocumentStage.EXECUTION,
    DocumentKindParent.SUPPORTING_DOC: DocumentStage.UNKNOWN,
    DocumentKindParent.MARKET_SURVEY: DocumentStage.REFERENCE,
    DocumentKindParent.MERCURIALE_REFERENCE: DocumentStage.REFERENCE,
    DocumentKindParent.UNKNOWN: DocumentStage.UNKNOWN,
}

# Mapping: document_kind -> default process_role
DOCUMENT_KIND_TO_PROCESS_ROLE: dict[DocumentKindParent, ProcessRole] = {
    DocumentKindParent.TDR: ProcessRole.DEFINES_NEED,
    DocumentKindParent.RFQ: ProcessRole.INVITES_BIDS,
    DocumentKindParent.ITT: ProcessRole.INVITES_BIDS,
    DocumentKindParent.DAO: ProcessRole.DEFINES_RULES,
    DocumentKindParent.OFFER_TECHNICAL: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.OFFER_FINANCIAL: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.OFFER_COMBINED: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.SUBMISSION_LETTER: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.PRICE_SCHEDULE: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.BOQ: ProcessRole.RESPONDS_TO_BID,
    DocumentKindParent.ADMIN_DOC: ProcessRole.SUPPORTS_PROCESS,
    DocumentKindParent.EVALUATION_DOC: ProcessRole.EVALUATES_BIDS,
    DocumentKindParent.CONTRACT: ProcessRole.FORMALIZES_AWARD,
    DocumentKindParent.PO: ProcessRole.STARTS_EXECUTION,
    DocumentKindParent.GRN: ProcessRole.CONFIRMS_RECEPTION,
    DocumentKindParent.SUPPORTING_DOC: ProcessRole.SUPPORTS_PROCESS,
    DocumentKindParent.MARKET_SURVEY: ProcessRole.SURVEYS_MARKET,
    DocumentKindParent.MERCURIALE_REFERENCE: ProcessRole.PROVIDES_REFERENCE,
    DocumentKindParent.UNKNOWN: ProcessRole.UNKNOWN,
}

SOURCE_RULES_KINDS: frozenset[DocumentKindParent] = frozenset(
    {
        DocumentKindParent.TDR,
        DocumentKindParent.RFQ,
        DocumentKindParent.ITT,
        DocumentKindParent.DAO,
    }
)

OFFER_KINDS: frozenset[DocumentKindParent] = frozenset(
    {
        DocumentKindParent.OFFER_TECHNICAL,
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindParent.OFFER_COMBINED,
    }
)
