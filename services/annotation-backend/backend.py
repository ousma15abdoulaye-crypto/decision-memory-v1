"""
DMS Annotation Backend — Framework v3.0.1b
Mistral AI ML Backend pour Label Studio
Mali Procurement · FREEZE DÉFINITIF 2026-03-15
"""

import copy
import hashlib
import hmac
import json
import logging
import os
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mistralai import Mistral

# ─────────────────────────────────────────────────────────
# CONSTANTES — FREEZE v3.0.1b
# ─────────────────────────────────────────────────────────

SCHEMA_VERSION = "v3.0.1b"
FRAMEWORK_VERSION = "annotation-framework-v3.0.1b"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# Sel pseudonymisation — variable env obligatoire
# Si absent → WARNING + SHA256 sans sel (dégradé)
PSEUDONYM_SALT = os.environ.get("PSEUDONYM_SALT", "")
if not PSEUDONYM_SALT:
    logging.getLogger(__name__).warning(
        "[SECURITY] PSEUDONYM_SALT absent — "
        "pseudonymisation dégradée (SHA256 sans sel)"
    )

# Grille confidence — MC-2 — IMMUABLE
CONF_EXACT = 1.0
CONF_INFERRED = 0.8
CONF_OCR = 0.6

# NULL Doctrine — états sémantiques
ABSENT = "ABSENT"
AMBIGUOUS = "AMBIGUOUS"
NOT_APPLICABLE = "NOT_APPLICABLE"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

# ─────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────

app = FastAPI(
    title="DMS Annotation Backend",
    version=SCHEMA_VERSION,
    description=f"Framework {FRAMEWORK_VERSION}",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# FALLBACK — activé si Mistral échoue ou JSON cassé
# ─────────────────────────────────────────────────────────

FALLBACK_RESPONSE: dict = {
    "couche_1_routing": {
        "procurement_family_main": AMBIGUOUS,
        "procurement_family_sub": AMBIGUOUS,
        "taxonomy_core": AMBIGUOUS,
        "taxonomy_client_adapter": AMBIGUOUS,
        "document_stage": AMBIGUOUS,
        "document_role": AMBIGUOUS,
    },
    "couche_2_core": {},
    "couche_3_policy_sci": {},
    "couche_4_atomic": {
        "conformite_admin": {},
        "capacite_services": {},
        "capacite_works": {},
        "capacite_goods": {},
        "durabilite": {},
        "financier": {
            "financial_layout_mode": NOT_APPLICABLE,
            "review_required": True,
            "line_items": [],
        },
    },
    "couche_5_gates": [],
    "identifiants": {
        "supplier_name_raw": NOT_APPLICABLE,
        "supplier_name_normalized": NOT_APPLICABLE,
        "supplier_identifier_raw": ABSENT,
        "supplier_legal_form": ABSENT,
        "supplier_address_raw": ABSENT,
        "supplier_phone_raw": ABSENT,
        "supplier_email_raw": ABSENT,
        "case_id": ABSENT,
        "supplier_id": NOT_APPLICABLE,
        "lot_scope": [],
        "zone_scope": [],
    },
    "ambiguites": ["AMBIG-PARSE_FAILED"],
    "_meta": {
        "schema_version": SCHEMA_VERSION,
        "framework_version": FRAMEWORK_VERSION,
        "mistral_model_used": MISTRAL_MODEL,
        "review_required": True,
        "annotation_status": "pending",
        "list_null_reason": {},
        "page_range": {"start": None, "end": None},
        "parent_document_id": NOT_APPLICABLE,
        "parent_document_role": NOT_APPLICABLE,
        "supplier_inherited_from": None,
    },
}


def _pseudonymise(value: str) -> str:
    """
    Pseudonymise une valeur sensible (phone, email).
    Retourne un hash hexadécimal 16 chars.

    Avec sel   : HMAC-SHA256(value, PSEUDONYM_SALT)[:16]
    Sans sel   : SHA256(value)[:16] — dégradé si PSEUDONYM_SALT absent
    Objectif   : présence détectable, valeur brute irrécupérable
                 sans le sel projet.
    """
    if PSEUDONYM_SALT:
        h = hmac.new(
            PSEUDONYM_SALT.encode(),
            value.encode(),
            hashlib.sha256,
        ).hexdigest()
    else:
        h = hashlib.sha256(value.encode()).hexdigest()
    return h[:16]


def _pseudonymise_contact(raw_value: str) -> dict:
    """
    Retourne le bloc pseudonymisé pour phone ou email.
    Format :
      {
        "pseudo":   "a3f9c2b1d4e87654",
        "present":  true,
        "redacted": true
      }
    Si raw_value = ABSENT / NOT_APPLICABLE → présent=false, pas de hash.
    """
    if raw_value in (ABSENT, NOT_APPLICABLE, "", None):
        return {
            "pseudo": None,
            "present": False,
            "redacted": False,
        }
    return {
        "pseudo": _pseudonymise(str(raw_value)),
        "present": True,
        "redacted": True,
    }


# ─────────────────────────────────────────────────────────
# PROMPT — RÈGLE-19 · AXIOME-3 · MC-1 · MC-2 · MC-3
# ─────────────────────────────────────────────────────────

PROMPT_SYSTEM = f"""Tu es un expert en analyse de documents procurement humanitaire (Mali, Afrique de l'Ouest).
Tu produits des pré-annotations JSON strictement conformes au Framework Annotation DMS {SCHEMA_VERSION}.

RÈGLES ABSOLUES :
1. AXIOME-3 : procurement_family_main (goods|services) EST LA PREMIÈRE DÉCISION. Toujours.
2. RÈGLE-19 : chaque champ critique = {{"value": ..., "confidence": X, "evidence": "5-10 mots exacts"}}.
   confidence DOIT être dans {{0.6, 0.8, 1.0}} UNIQUEMENT.
   0.6 = OCR dégradé · 0.8 = inféré indirect · 1.0 = texte exact copié.
3. MC-1 : gate_value = booléen JSON (true/false/null). JAMAIS la string "true" ou "false".
   gate_state = "APPLICABLE" ou "NOT_APPLICABLE".
4. MC-3 : price_date = valeur ISO si trouvée, "ABSENT" si non trouvée. JAMAIS forcer document_date.
5. NULL DOCTRINE : utiliser "ABSENT" / "AMBIGUOUS" / "NOT_APPLICABLE" — jamais null comme valeur sémantique.
6. financial_layout_mode DOIT être déclaré AVANT les line_items.
7. Si tableau de prix présent → line_items obligatoires. 1 ligne = 1 objet atomique.
   Vérifier : line_total = quantity × unit_price. Si écart > 1% → ambiguites += "AMBIG-3_line_total_math_anomaly".
8. Ne pas annoter : introductions, remerciements, rappels juridiques sans effet opératoire.
9. evaluation_report : routing uniquement si détecté. Zéro annotation active.
10. Retourner UNIQUEMENT le JSON. Zéro prose avant ou après le JSON.
11. Sur les offres (technical_offer / financial_offer / combined_offer) :
    Extraire les éléments d'identification fournisseur VISIBLES.

    AUTORISÉ — extraire la valeur brute :
      supplier_name_raw      : nom exact tel qu'écrit
      supplier_legal_form    : SARL / SA / ONG / GIE / ABSENT
      supplier_address_raw   : adresse postale (60 chars max)
      supplier_phone_raw     : numéro(s) de téléphone
      supplier_email_raw     : adresse(s) email

    INTERDIT — NE JAMAIS extraire la valeur brute :
      Numéro RIB / IBAN / numéro de compte bancaire
      Numéro NIF exact
      Numéro RCCM exact
    Pour ces trois : extraire UNIQUEMENT has_rib / has_nif / has_rccm
    = true si présent dans le document, false si absent, ABSENT si non applicable.

12. Sur source_rules :
    supplier_name_raw      = NOT_APPLICABLE
    supplier_phone_raw     = NOT_APPLICABLE
    supplier_email_raw     = NOT_APPLICABLE
    supplier_address_raw   = NOT_APPLICABLE
    has_rib / has_nif / has_rccm = NOT_APPLICABLE"""


def _build_prompt(text: str) -> str:
    # Tronquer à 12 000 caractères pour rester dans le contexte Mistral small
    text_trimmed = text[:12000] if len(text) > 12000 else text
    return f"""Analyse ce document procurement et retourne UNIQUEMENT un JSON conforme au schéma ci-dessous.

DOCUMENT :
\"\"\"
{text_trimmed}
\"\"\"

SCHÉMA JSON CIBLE (respecter exactement la structure) :
{{
  "couche_1_routing": {{
    "procurement_family_main":  "goods | services",
    "procurement_family_sub":   "food|office_consumables|construction_materials|nfi|it_equipment|software|nutrition_products|vehicles|motorcycles|other_goods|consultancy|audit|training|catering|vehicle_rental|survey|audiovisual|works|other_services",
    "taxonomy_core":            "dao|rfq|rfp_consultance|tdr_consultance_audit|offer_technical|offer_financial|offer_combined|annex_pricing|supporting_doc|evaluation_report|marketsurvey",
    "taxonomy_client_adapter":  "<wording exact client>",
    "document_stage":           "solicitation|offer|evaluation|decision",
    "document_role":            "source_rules|technical_offer|financial_offer|combined_offer|annex_pricing|supporting_doc|evaluation_report"
  }},

  "couche_2_core": {{
    "procedure_reference":        {{"value": "...", "confidence": 1.0, "evidence": "..."}},
    "issuing_entity":             {{"value": "...", "confidence": 1.0, "evidence": "..."}},
    "project_name":               {{"value": "...", "confidence": 1.0, "evidence": "..."}},
    "lot_count":                  {{"value": null,  "confidence": 1.0, "evidence": "..."}},
    "lot_scope":                  {{"value": [],    "confidence": 1.0, "evidence": "..."}},
    "zone_scope":                 {{"value": [],    "confidence": 1.0, "evidence": "..."}},
    "submission_deadline":        {{"value": "ABSENT", "confidence": 1.0, "evidence": "..."}},
    "submission_mode":            {{"value": [],    "confidence": 1.0, "evidence": "..."}},
    "result_type":                {{"value": "ABSENT", "confidence": 0.8, "evidence": "..."}},
    "technical_threshold":        {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "visit_required":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "sample_required":            {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "negotiation_allowed":        {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "regime_dominant":            {{"value": "AUCUN", "confidence": 0.8, "evidence": "..."}},
    "modalite_paiement":          {{"value": "ABSENT", "confidence": 0.8, "evidence": "..."}},
    "eligibility_gates":          [],
    "scoring_structure":          [],
    "ponderation_coherence":      "100_exact|non_precisee_dans_doc|incomplete|incoherente"
  }},

  "couche_3_policy_sci": {{
    "has_sci_conditions_signed": {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "has_iapg_signed":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "has_non_sanction":          {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "ariba_network_required":    {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
    "sci_sustainability_pct":    {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}}
  }},

  "couche_4_atomic": {{
    "conformite_admin": {{
      "has_nif":                     {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_rccm":                    {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_rib":                     {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_id_representative":       {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_statutes":                {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_quitus_fiscal":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "has_certificat_non_faillite": {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}}
    }},
    "capacite_services": {{
      "similar_assignments_count":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "lead_expert_years":                   {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "lead_expert_similar_projects_count":  {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "team_composition_present":            {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "methodology_present":                 {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "workplan_present":                    {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "qa_plan_present":                     {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "ethics_plan_present":                 {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}}
    }},
    "capacite_works": {{
      "execution_delay_days":               {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "work_methodology_present":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "environment_plan_present":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "site_visit_pv_present":              {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "equipment_list_present":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "key_staff_present":                  {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "local_labor_commitment_present":     {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}}
    }},
    "capacite_goods": {{
      "client_references_present":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "warranty_present":                      {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "delivery_schedule_present":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "warehouse_capacity_present":            {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "stock_sufficiency_present":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "product_specs_present":                 {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "official_distribution_license_present": {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "sample_submission_present":             {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "phytosanitary_cert_present":            {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "bank_credit_line_present":              {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}}
    }},
    "durabilite": {{
      "local_content_present":          {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "community_employment_present":   {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "environment_commitment_present": {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "gender_inclusion_present":       {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "sustainability_certifications":  {{"value": [],               "confidence": 1.0, "evidence": "..."}}
    }},
    "financier": {{
      "financial_layout_mode": "NOT_APPLICABLE",
      "pricing_scope":         "NOT_APPLICABLE",
      "total_price":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "currency":              {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "price_basis":           {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "price_date":            {{"value": "ABSENT",         "confidence": 1.0, "evidence": "..."}},
      "delivery_delay_days":   {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "validity_days":         {{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "discount_terms_present":{{"value": "NOT_APPLICABLE", "confidence": 1.0, "evidence": "..."}},
      "review_required":       false,
      "line_items":            []
    }}
  }},

  "couche_5_gates": [
    {{"gate_name": "gate_eligibility_passed", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_capacity_passed", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_visit_required", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_visit_passed", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_samples_required", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_samples_passed", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_commercial_eligible", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_financial_format_usable", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_line_item_extractable", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}},
    {{"gate_name": "gate_negotiation_reached", "gate_value": null, "gate_state": "NOT_APPLICABLE", "gate_threshold_value": null, "gate_reason_raw": "...", "gate_evidence_hint": "NOT_APPLICABLE", "confidence": 1.0}}
  ],

  "identifiants": {{
    "supplier_name_raw":        "NOT_APPLICABLE",
    "supplier_name_normalized": "NOT_APPLICABLE",
    "supplier_identifier_raw":  "{ABSENT}",
    "supplier_legal_form":      "{ABSENT}",
    "supplier_address_raw":     "{ABSENT}",
    "supplier_phone_raw":       "{ABSENT}",
    "supplier_email_raw":       "{ABSENT}",
    "case_id":                  "{ABSENT}",
    "supplier_id":              "NOT_APPLICABLE",
    "lot_scope":                [],
    "zone_scope":               []
  }},

  "ambiguites": [],

  "_meta": {{
    "schema_version":          "{SCHEMA_VERSION}",
    "framework_version":       "{FRAMEWORK_VERSION}",
    "mistral_model_used":      "{MISTRAL_MODEL}",
    "review_required":         false,
    "annotation_status":       "pending",
    "list_null_reason":        {{}},
    "page_range":              {{"start": null, "end": null}},
    "parent_document_id":      "NOT_APPLICABLE",
    "parent_document_role":    "NOT_APPLICABLE",
    "supplier_inherited_from": null
  }}
}}

INSTRUCTIONS COMPLÉMENTAIRES :
- Remplir chaque champ selon ce qui est RÉELLEMENT présent dans le document.
- Si un champ n'est pas applicable → garder "NOT_APPLICABLE".
- Si un champ est applicable mais absent du document → mettre "ABSENT".
- Si présent mais illisible / contradictoire → mettre "AMBIGUOUS".
- Pour les offres financières (offer_financial / combined_offer) :
    * Déclarer financial_layout_mode EN PREMIER.
    * Si tableau présent → extraire TOUS les line_items.
    * Vérifier line_total = quantity × unit_price pour chaque ligne.
- Pour les gates : gate_value = true / false / null (booléen JSON, jamais string).
- Retourner UNIQUEMENT le JSON. Rien d'autre."""


# ─────────────────────────────────────────────────────────
# PARSER ROBUSTE — 4 tentatives + fallback loggué
# ─────────────────────────────────────────────────────────


def _parse_mistral_response(raw: str) -> dict:
    """
    4 tentatives de parsing dans l'ordre :
    1. JSON brut direct
    2. Extraction bloc ```json ... ```
    3. Extraction première { → dernière }
    4. Fallback FALLBACK_RESPONSE + log erreur
    """
    if not raw or not raw.strip():
        logger.error("[PARSE] Réponse Mistral vide — fallback activé")
        return FALLBACK_RESPONSE

    # Tentative 1 — JSON brut
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Tentative 2 — bloc ```json
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Tentative 3 — première { → dernière }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    _raw_len = len(raw) if raw else 0
    _raw_hash = hashlib.sha256(raw.encode()).hexdigest()[:12] if raw else "empty"
    logger.error(
        "[PARSE] Fallback activé — raw_len=%s raw_hash=%s "
        "(contenu non loggué — données sensibles possibles)",
        _raw_len,
        _raw_hash,
    )
    return FALLBACK_RESPONSE


# ─────────────────────────────────────────────────────────
# BUILDER LABEL STUDIO — from_name : extracted_json + annotation_notes
# ─────────────────────────────────────────────────────────


def _build_ls_result(parsed: dict, task_id: int) -> list:
    """
    Pseudonymise phone et email AVANT insertion dans extracted_json.
    La valeur brute ne quitte jamais le backend.
    """
    parsed = copy.deepcopy(parsed)

    # Pseudonymisation phone / email dans identifiants
    identifiants = parsed.get("identifiants", {})

    phone_raw = identifiants.pop("supplier_phone_raw", ABSENT)
    email_raw = identifiants.pop("supplier_email_raw", ABSENT)

    identifiants["supplier_phone"] = _pseudonymise_contact(phone_raw)
    identifiants["supplier_email"] = _pseudonymise_contact(email_raw)

    # Address : tronquer à 60 chars
    addr = identifiants.get("supplier_address_raw", ABSENT)
    if addr not in (ABSENT, NOT_APPLICABLE, "", None):
        identifiants["supplier_address_raw"] = str(addr)[:60]

    parsed["identifiants"] = identifiants

    # Suite identique au _build_ls_result existant
    routing = parsed.get("couche_1_routing", {})
    meta = parsed.get("_meta", {})
    gates = parsed.get("couche_5_gates", [])
    ambig = parsed.get("ambiguites", [])

    valid_gates = [g for g in gates if isinstance(g, dict) and "gate_name" in g]
    gates_failed = [
        g.get("gate_name", "unknown")
        for g in valid_gates
        if g.get("gate_value") is False and g.get("gate_state") == "APPLICABLE"
    ]

    family = routing.get("procurement_family_main", "UNKNOWN")
    sub = routing.get("procurement_family_sub", "UNKNOWN")
    tax_core = routing.get("taxonomy_core", "UNKNOWN")
    role = routing.get("document_role", "UNKNOWN")
    stage = routing.get("document_stage", "UNKNOWN")
    review = meta.get("review_required", False)

    notes = (
        f"[{SCHEMA_VERSION}] {family}/{sub}\n"
        f"taxonomy={tax_core} | role={role} | stage={stage}\n"
        f"review_required={review}\n"
        f"gates_failed={gates_failed if gates_failed else 'aucun'}\n"
        f"ambiguites={ambig if ambig else 'aucune'}\n"
        f"model={meta.get('mistral_model_used', MISTRAL_MODEL)}"
    )

    return [
        {
            "from_name": "extracted_json",
            "to_name": "document_text",
            "type": "textarea",
            "value": {"text": [json.dumps(parsed, ensure_ascii=False, indent=2)]},
        },
        {
            "from_name": "annotation_notes",
            "to_name": "document_text",
            "type": "textarea",
            "value": {"text": [notes]},
        },
    ]


# ─────────────────────────────────────────────────────────
# APPEL MISTRAL — async
# ─────────────────────────────────────────────────────────


async def _mistral_extract(text: str) -> dict:
    """
    Appelle Mistral avec le prompt v3.0.1a.
    Retourne le dict parsé ou FALLBACK_RESPONSE.
    """
    if not client:
        logger.warning("[MISTRAL] Client non configuré — fallback activé")
        return FALLBACK_RESPONSE

    try:
        response = client.chat.complete(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": _build_prompt(text)},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        raw = response.choices[0].message.content or ""
        logger.info("[MISTRAL] Réponse reçue — %d caractères", len(raw))
        return _parse_mistral_response(raw)

    except Exception as exc:
        logger.error("[MISTRAL] Erreur appel API : %s — fallback activé", exc)
        return FALLBACK_RESPONSE


# ─────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "schema": SCHEMA_VERSION,
        "framework": FRAMEWORK_VERSION,
        "model": MISTRAL_MODEL,
        "mistral_configured": bool(MISTRAL_API_KEY),
    }


@app.post("/setup")
async def setup(request: Request) -> JSONResponse:
    """
    Label Studio appelle /setup au démarrage du ML Backend.
    Retourner model_version pour confirmer la compatibilité.
    """
    return JSONResponse(
        {
            "model_version": f"dms-{SCHEMA_VERSION}",
            "status": "ready",
            "framework": FRAMEWORK_VERSION,
        }
    )


@app.post("/predict")
async def predict(request: Request) -> JSONResponse:
    """
    Label Studio envoie les tâches → on retourne les pré-annotations Mistral.
    1 tâche = 1 document. Extraction async Mistral v3.0.1a.
    """
    body = await request.json()
    tasks = body.get("tasks", [])

    if not tasks:
        return JSONResponse({"results": []})

    predictions = []
    for task in tasks:
        task_id = task.get("id", 0)
        data = task.get("data", {})
        text = data.get("text", "") or data.get("content", "") or ""

        if not text.strip():
            logger.warning("[PREDICT] task_id=%s — texte vide, fallback", task_id)
            parsed = FALLBACK_RESPONSE
        else:
            parsed = await _mistral_extract(text)

        result = _build_ls_result(parsed, task_id)

        predictions.append(
            {
                "id": task_id,
                "result": result,
                "score": None,
                "model_version": f"dms-{SCHEMA_VERSION}",
            }
        )

    return JSONResponse({"results": predictions})


@app.post("/train")
async def train(request: Request) -> JSONResponse:
    """
    Endpoint train — réservé M12 fine-tuning Mistral.
    Actuellement : accusé de réception uniquement.
    """
    body = await request.json()
    annotations = body.get("annotations", [])
    logger.info(
        "[TRAIN] %d annotations reçues — fine-tuning non actif (M12)", len(annotations)
    )
    return JSONResponse(
        {
            "status": "received",
            "message": f"Fine-tuning réservé M12 — {len(annotations)} annotations reçues",
        }
    )


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """
    Webhook Label Studio — événements annotation.
    Log uniquement — aucun traitement actif en M11-bis.
    """
    body = await request.json()
    action = body.get("action", "unknown")
    logger.info("[WEBHOOK] action=%s", action)
    return JSONResponse({"status": "ok", "action": action})
