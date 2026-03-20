"""
DMS Annotation Backend — Framework v3.0.1d
Mistral AI ML Backend pour Label Studio
Mali Procurement · ADR-015 line_items unit_raw 2026-03-16
"""

import copy
import hashlib
import hmac
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

# Import prompt — chemin absolu garanti — zéro PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral  # mistralai v2.x

from prompts import SYSTEM_PROMPT
from prompts.schema_validator import DMSAnnotation, GateName

# CONSTANTES — v3.0.1d ADR-015
# Label Studio : <Text name="document_text" …/> + toName="document_text" sur les contrôles (E-66)
LS_TEXTAREA_TO_NAME = "document_text"

SCHEMA_VERSION = "v3.0.1d"
FRAMEWORK_VERSION = "annotation-framework-v3.0.1d"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "80000"))
# M-ANNOTATION-CONTAINMENT-01 — aligné couche A (MIN_EXTRACTED_TEXT_CHARS_FOR_ML)
MIN_LLM_CONTEXT_CHARS = int(os.environ.get("MIN_LLM_CONTEXT_CHARS", "100"))
MIN_PREDICT_TEXT_CHARS = int(os.environ.get("MIN_PREDICT_TEXT_CHARS", "200"))

# E-27 : CORS restrictif — CORS_ORIGINS env (comma-separated)
# Default localhost:8080 pour dev. Prod Railway : définir CORS_ORIGINS=URL_LABEL_STUDIO
_CORS_RAW = os.environ.get("CORS_ORIGINS", "http://localhost:8080")
CORS_ORIGINS = (
    ["*"]
    if _CORS_RAW.strip() == "*"
    else [o.strip() for o in _CORS_RAW.split(",") if o.strip()]
)

# Sel pseudonymisation — variable env obligatoire
# Si absent → échec du démarrage, sauf si ALLOW_WEAK_PSEUDONYMIZATION est activé
PSEUDONYM_SALT = os.environ.get("PSEUDONYM_SALT", "")
ALLOW_WEAK_PSEUDONYMIZATION = os.environ.get(
    "ALLOW_WEAK_PSEUDONYMIZATION", ""
).lower() in {"1", "true", "yes", "on"}
if not PSEUDONYM_SALT:
    if ALLOW_WEAK_PSEUDONYMIZATION:
        logging.getLogger(__name__).warning(
            "[SECURITY] PSEUDONYM_SALT absent — "
            "pseudonymisation DÉGRADÉE (SHA256 sans sel) explicitement autorisée "
            "par ALLOW_WEAK_PSEUDONYMIZATION"
        )
    else:
        raise RuntimeError(
            "[SECURITY] PSEUDONYM_SALT manquant et ALLOW_WEAK_PSEUDONYMIZATION "
            "non activé — refus de démarrer avec une pseudonymisation faible"
        )

# Grille confidence — MC-2 — IMMUABLE
CONF_EXACT = 1.0
CONF_INFERRED = 0.8
CONF_OCR = 0.6

# NULL Doctrine — états sémantiques
ABSENT = "ABSENT"
AMBIGUOUS = "AMBIGUOUS"
NOT_APPLICABLE = "NOT_APPLICABLE"


def _fv_absent(confidence: float = CONF_OCR) -> dict[str, Any]:
    """FieldValue minimal — aucune donnée inventée (M-ANNOTATION-CONTRACT-02)."""
    return {"value": ABSENT, "confidence": confidence, "evidence": ABSENT}


def _build_fallback_response() -> dict[str, Any]:
    """
    Squelette DMSAnnotation complet pour parse/API KO / client absent.
    Validé au chargement — aligné prompts.schema_validator (sans assouplir le contrat).
    """
    gates = [
        {
            "gate_name": g.value,
            "gate_value": None,
            "gate_state": "NOT_APPLICABLE",
            "gate_threshold_value": None,
            "gate_reason_raw": ABSENT,
            "gate_evidence_hint": ABSENT,
            "confidence": CONF_EXACT,
        }
        for g in GateName
    ]
    couche_2_core = {
        "procedure_reference": _fv_absent(),
        "issuing_entity": _fv_absent(),
        "project_name": _fv_absent(),
        "lot_count": _fv_absent(),
        "lot_scope": {"value": [], "confidence": CONF_OCR, "evidence": ABSENT},
        "zone_scope": {"value": [], "confidence": CONF_OCR, "evidence": ABSENT},
        "submission_deadline": _fv_absent(),
        "submission_mode": {"value": [], "confidence": CONF_OCR, "evidence": ABSENT},
        "result_type": _fv_absent(),
        "technical_threshold": _fv_absent(),
        "visit_required": _fv_absent(),
        "sample_required": _fv_absent(),
        "negotiation_allowed": _fv_absent(),
        "regime_dominant": _fv_absent(),
        "modalite_paiement": _fv_absent(),
        "eligibility_gates": [],
        "scoring_structure": [],
        "ponderation_coherence": ABSENT,
    }
    couche_3 = {
        "has_sci_conditions_signed": _fv_absent(),
        "has_iapg_signed": _fv_absent(),
        "has_non_sanction": _fv_absent(),
        "ariba_network_required": _fv_absent(),
        "sci_sustainability_pct": _fv_absent(),
    }
    ca = {
        k: _fv_absent()
        for k in (
            "has_nif",
            "has_rccm",
            "has_rib",
            "has_id_representative",
            "has_statutes",
            "has_quitus_fiscal",
            "has_certificat_non_faillite",
        )
    }
    cs = {
        k: _fv_absent()
        for k in (
            "similar_assignments_count",
            "lead_expert_years",
            "lead_expert_similar_projects_count",
            "team_composition_present",
            "methodology_present",
            "workplan_present",
            "qa_plan_present",
            "ethics_plan_present",
        )
    }
    cw = {
        k: _fv_absent()
        for k in (
            "execution_delay_days",
            "work_methodology_present",
            "environment_plan_present",
            "site_visit_pv_present",
            "equipment_list_present",
            "key_staff_present",
            "local_labor_commitment_present",
        )
    }
    cg = {
        k: _fv_absent()
        for k in (
            "client_references_present",
            "warranty_present",
            "delivery_schedule_present",
            "warehouse_capacity_present",
            "stock_sufficiency_present",
            "product_specs_present",
            "official_distribution_license_present",
            "sample_submission_present",
            "phytosanitary_cert_present",
            "bank_credit_line_present",
        )
    }
    du = {
        k: _fv_absent()
        for k in (
            "local_content_present",
            "community_employment_present",
            "environment_commitment_present",
            "gender_inclusion_present",
            "sustainability_certifications",
        )
    }
    financier = {
        "financial_layout_mode": NOT_APPLICABLE,
        "pricing_scope": ABSENT,
        "total_price": _fv_absent(),
        "currency": _fv_absent(),
        "price_basis": _fv_absent(),
        "price_date": _fv_absent(),
        "delivery_delay_days": _fv_absent(),
        "validity_days": _fv_absent(),
        "discount_terms_present": _fv_absent(),
        "review_required": True,
        "line_items": [],
    }
    out: dict[str, Any] = {
        "couche_1_routing": {
            "procurement_family_main": AMBIGUOUS,
            "procurement_family_sub": AMBIGUOUS,
            "taxonomy_core": AMBIGUOUS,
            "taxonomy_client_adapter": AMBIGUOUS,
            "document_stage": AMBIGUOUS,
            "document_role": AMBIGUOUS,
        },
        "couche_2_core": couche_2_core,
        "couche_3_policy_sci": couche_3,
        "couche_4_atomic": {
            "conformite_admin": ca,
            "capacite_services": cs,
            "capacite_works": cw,
            "capacite_goods": cg,
            "durabilite": du,
            "financier": financier,
        },
        "couche_5_gates": gates,
        "identifiants": {
            "supplier_name_raw": NOT_APPLICABLE,
            "supplier_name_normalized": NOT_APPLICABLE,
            "supplier_legal_form": ABSENT,
            "supplier_identifier_raw": ABSENT,
            "has_nif": ABSENT,
            "has_rccm": ABSENT,
            "has_rib": ABSENT,
            "supplier_address_raw": ABSENT,
            "supplier_phone_raw": ABSENT,
            "supplier_email_raw": ABSENT,
            "quitus_fiscal_date": ABSENT,
            "cert_non_faillite_date": ABSENT,
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
            "annotation_status": "review_required",
            "list_null_reason": {},
            "page_range": {"start": None, "end": None},
            "parent_document_id": NOT_APPLICABLE,
            "parent_document_role": NOT_APPLICABLE,
            "supplier_inherited_from": None,
        },
    }
    # Conformité DMSAnnotation : vérifiée en CI (tests), pas au import — évite crash
    # démarrage si dérive schéma / Pydantic ; le fallback doit toujours être chargeable.
    return out


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

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
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FALLBACK — Mistral échoue ou JSON cassé (squelette validé DMSAnnotation)
FALLBACK_RESPONSE: dict[str, Any] = _build_fallback_response()


def _pseudonymise(value: str) -> str:
    """Pseudonymise phone/email — HMAC-SHA256[:16] ou SHA256[:16] si pas de sel."""
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
    """Bloc pseudonymisé phone/email. ABSENT/NOT_APPLICABLE → present=false."""
    if raw_value in (ABSENT, NOT_APPLICABLE, "AMBIGUOUS", "", None):
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


# PROMPT — pattern fichier texte pur — prompts/system_prompt.txt (ADR-015)
def _normalize_input_text(text: str) -> str:
    """Normalisation légère avant seuil — espaces, pas de mutation sémantique."""
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip())


def _truncate_text(text: str, task_id: int) -> str:
    """Tronque le texte à MAX_TEXT_CHARS. Log si troncature appliquée."""
    if len(text) <= MAX_TEXT_CHARS:
        return text
    logger.warning(
        "[TRUNCATE] task_id=%s — %d chars → %d chars tronqués",
        task_id,
        len(text),
        MAX_TEXT_CHARS,
    )
    return text[:MAX_TEXT_CHARS]


def _build_messages(user_content: str, document_role: str = "") -> list[dict]:
    """
    Construit les messages pour l'API Mistral.
    user_content contient le document.
    document_role : si fourni (extraction.py), injecté pour LOI 1bis.

    M-ANNOTATION-CONTAINMENT-01 : refuse texte vide / trop court — ne pas construire
    de prompt exploitable sans contexte documentaire minimal.
    """
    normalized = _normalize_input_text(user_content)
    if len(normalized) < MIN_LLM_CONTEXT_CHARS:
        raise ValueError(
            f"INSUFFICIENT_TEXT_FOR_LLM len={len(normalized)} min={MIN_LLM_CONTEXT_CHARS}"
        )

    prefix = ""
    if document_role:
        prefix = f"CONTEXTE: document_role attendu = {document_role}\n\n"

    anti_invention = (
        "\n\nRÈGLES STRICTES — NE PAS INVENTER : toute information absente du document "
        "ci-dessus doit rester ABSENT, NOT_APPLICABLE ou AMBIGUOUS selon le cadre DMS. "
        "Ne pas déduire de valeurs numériques ou de noms non présents dans le texte. "
        "Chaque champ extrait doit respecter value + confidence + evidence (pas de valeur nue)."
    )
    user_prompt = (
        f"{prefix}{user_content}\n\n"
        "Extraire les données en JSON selon les règles du prompt système."
        f"{anti_invention}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


# PARSER ROBUSTE — 5 tentatives + fallback loggué
def _parse_mistral_response(raw: str, task_id: int = 0) -> dict:
    """Parse robuste — JSON brut, markdown, trailing commas, tronqué."""
    if not raw:
        logger.warning("[PARSE] raw vide — task_id=%s", task_id)
        return copy.deepcopy(FALLBACK_RESPONSE)

    raw = raw.strip().lstrip("\ufeff")

    def _try(s: str) -> "dict | None":
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            try:
                return json.loads(re.sub(r",\s*([}\]])", r"\1", s))
            except (json.JSONDecodeError, re.error):
                return None

    if (r := _try(raw)) is not None:
        return r
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if m and (r := _try(m.group(1).strip())) is not None:
        return r
    try:
        frag = raw[raw.index("{") : raw.rindex("}") + 1]
        if (r := _try(frag)) is not None:
            return r
    except ValueError:
        pass
    try:
        for mk in ("```json\n", "```json", "```\n", "```"):
            idx = raw.find(mk)
            if idx != -1:
                s = raw[idx + len(mk) :]
                ei = s.find("```")
                s = (s[:ei] if ei != -1 else s).strip()
                s = s[s.index("{") : s.rindex("}") + 1]
                if (r := _try(s)) is not None:
                    return r
    except (ValueError, re.error):
        pass
    try:
        s = raw[raw.index("{") :]
        deficit = s.count("{") - s.count("}")
        if deficit > 0:
            s = re.sub(r",\s*$", "", s.rstrip()) + "}" * deficit
        if (r := _try(s)) is not None:
            return r
    except (ValueError, re.error):
        pass

    _raw_len = len(raw) if raw else 0
    _raw_hash = hashlib.sha256(raw.encode()).hexdigest()[:12] if raw else "empty"
    logger.error("[PARSE] Fallback — raw_len=%s raw_hash=%s", _raw_len, _raw_hash)
    return dict(FALLBACK_RESPONSE)


_ALLOWED_CONFIDENCE = frozenset({0.6, 0.8, 1.0})


def _normalize_gates(annotation: dict) -> dict:
    """
    Normalise les gates AVANT validation Pydantic.

    Absorbe les imperfections systématiques de Mistral :
      1. confidence=0.0 + NOT_APPLICABLE → 1.0
         LOI 4 DMS : NOT_APPLICABLE = certitude maximale
      2. confidence=0.0 + APPLICABLE → 0.6 (minimum autorisé)
      3. gate_value=null + APPLICABLE → False + AMBIG-5 tracé
         Le système ne décide pas → AMBIG tracé → humain valide

    Ces 3 règles sont figées.
    GO CTO obligatoire avant toute modification.
    Ref : E-65 — audit logs 2026-03-18
    """
    gates = annotation.get("couche_5_gates", [])
    ambiguites = list(annotation.get("ambiguites", []))

    for gate in gates:
        if not isinstance(gate, dict):
            continue

        gate_name = gate.get("gate_name", "unknown")
        gate_state = gate.get("gate_state", "")
        confidence = gate.get("confidence", 0.0)

        # RÈGLE 1 : NOT_APPLICABLE → confidence = 1.0
        if gate_state == "NOT_APPLICABLE":
            if confidence != 1.0:
                gate["confidence"] = 1.0
            if gate.get("gate_value") is not None:
                gate["gate_value"] = None

        # RÈGLE 2 : APPLICABLE + confidence=0.0 → 0.6
        elif gate_state == "APPLICABLE":
            if confidence not in _ALLOWED_CONFIDENCE:
                gate["confidence"] = 0.6
            # RÈGLE 3 : APPLICABLE + gate_value=null → False + AMBIG
            if gate.get("gate_value") is None:
                gate["gate_value"] = False
                ambig = f"AMBIG-5_gate_{gate_name}_value_null_forced_false"
                if ambig not in ambiguites:
                    ambiguites.append(ambig)

    annotation["ambiguites"] = ambiguites
    return annotation


def _norm_spot(s: str) -> str:
    """Normalisation pour comparaison tolérante (espaces, casse)."""
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _digits_compact(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _spot_check_annotation_vs_source(
    annotation: dict, source_text: str, task_id: int
) -> dict:
    """
    Spot-check minimal post-réponse LLM — M-ANNOTATION-CONTAINMENT-01.
    Non destructif : marque review_required + ambiguïté, ne « corrige » pas le JSON.
    """
    annotation = copy.deepcopy(annotation)
    src = _norm_spot(source_text)
    raw_amb = annotation.get("ambiguites", [])
    if isinstance(raw_amb, list):
        amb = list(raw_amb)
    elif isinstance(raw_amb, (tuple, set)):
        amb = list(raw_amb)
    else:
        amb = []
    raw_meta = annotation.get("_meta")
    if isinstance(raw_meta, dict):
        meta = raw_meta
    else:
        meta = {}
        annotation["_meta"] = meta
    skip_vals = (ABSENT, NOT_APPLICABLE, AMBIGUOUS, "", None)

    ident = annotation.get("identifiants")
    ident = ident if isinstance(ident, dict) else {}
    raw_name = ident.get("supplier_name_raw")
    if raw_name not in skip_vals:
        needle = _norm_spot(str(raw_name))
        if len(needle) >= 3 and needle not in src:
            code = "AMBIG-SPOT-supplier_not_in_source"
            if code not in amb:
                amb.append(code)
            meta["review_required"] = True
            logger.warning(
                "[SPOT_CHECK] task_id=%s reason=supplier_not_in_source preview=%r",
                task_id,
                str(raw_name)[:80],
            )

    fin_block = annotation.get("couche_4_atomic")
    fin_block = fin_block if isinstance(fin_block, dict) else {}
    fin = fin_block.get("financier")
    fin = fin if isinstance(fin, dict) else {}
    total_raw = fin.get("total_price")
    if total_raw in skip_vals or total_raw is None:
        total_raw = fin.get("total")
    val = None
    if isinstance(total_raw, dict):
        val = total_raw.get("value")
    elif total_raw not in skip_vals:
        val = total_raw
    if val not in skip_vals and val is not None:
        td = _digits_compact(str(val))
        src_d = _digits_compact(source_text)
        if len(td) >= 5 and td not in src_d:
            code = "AMBIG-SPOT-total_not_in_source"
            if code not in amb:
                amb.append(code)
            meta["review_required"] = True
            logger.warning(
                "[SPOT_CHECK] task_id=%s reason=total_not_in_source value_digits=%s",
                task_id,
                td[:24],
            )

    annotation["ambiguites"] = amb
    return annotation


def _validate_financial_coherence(annotation: dict, task_id: int) -> list[str]:
    """
    Valide la cohérence mathématique des montants.
        validated = DMSAnnotation.model_validate(annotation)
        corrected_annotation = validated.model_dump(by_alias=True)
        return corrected_annotation, []
      → ANOMALY tracé
      → review_required = True
    E-47 étendu au niveau document.
    """
    warnings: list[str] = []
    routing = annotation.get("couche_1_routing", {})
    role = routing.get("document_role", "")

    if role not in (
        "financial_proposal",
        "offer_financial",
        "financial_offer",
        "annex_pricing",
    ):
        return warnings

    financier = annotation.get("couche_4_atomic", {}).get("financier", {})
    total_raw = financier.get("total_price", {})
    line_items = financier.get("line_items", [])

    total_declared = None
    if isinstance(total_raw, dict):
        try:
            val = total_raw.get("value", 0)
            if val in (None, "", "ABSENT", "NOT_APPLICABLE"):
                return warnings
            s = str(val).replace(" ", "").replace("\u202f", "")
            total_declared = float(s)
        except (ValueError, TypeError):
            return warnings
    elif isinstance(total_raw, int | float):
        total_declared = float(total_raw)

    if not total_declared or not line_items:
        return warnings

    total_computed = sum(
        float(li.get("line_total", 0) or 0) for li in line_items if isinstance(li, dict)
    )

    if total_computed == 0:
        return warnings

    ecart = abs(total_declared - total_computed) / max(total_computed, 1)
    if ecart > 0.01:
        msg = (
            f"ANOMALY_total_price_{int(total_declared)}"
            f"_vs_sum_items_{int(total_computed)}"
        )
        warnings.append(msg)
        logger.error(
            "[VALIDATE] Incohérence montant task_id=%s : "
            "total_price=%s sum_items=%s ecart=%.1f%%",
            task_id,
            total_declared,
            total_computed,
            ecart * 100,
        )

    return warnings


def _validate_and_correct(annotation: dict, task_id: int = 0) -> tuple[dict, list]:
    """
    Valide le JSON annoté contre le schéma DMS v3.0.1d.
    Retourne (annotation_corrigée, liste_erreurs).
    Ne lève jamais d'exception — les erreurs sont tracées.
    """
    errors: list[dict] = []
    annotation = copy.deepcopy(annotation)

    try:
        DMSAnnotation.model_validate(annotation)
        # Validation cohérence financière (E-47 étendu) — même si schéma OK
        financial_warnings = _validate_financial_coherence(annotation, task_id)
        if financial_warnings:
            annotation.setdefault("ambiguites", [])
            for w in financial_warnings:
                if w not in annotation["ambiguites"]:
                    annotation["ambiguites"].append(w)
            annotation.setdefault("_meta", {})
            annotation["_meta"]["review_required"] = True
            logger.error(
                "[VALIDATE] Incohérence financière task_id=%s : %s",
                task_id,
                financial_warnings,
            )
        return annotation, []
    except ValidationError as exc:
        if hasattr(exc, "errors"):
            for err in exc.errors():
                loc = err.get("loc", ())
                msg = err.get("msg", "")
                errors.append({"loc": loc, "msg": msg})
                logger.error(
                    "[VALIDATE] loc=%s msg=%s — task_id=%s",
                    loc,
                    msg,
                    task_id,
                )
            logger.error(
                "[VALIDATE] %d erreurs schema — task_id=%s",
                len(errors),
                task_id,
            )
        else:
            errors.append({"loc": (), "msg": str(exc)})
            logger.error(
                "[VALIDATE] Erreur validation — task_id=%s : %s",
                task_id,
                exc,
            )

        annotation.setdefault("_meta", {})
        annotation["_meta"]["review_required"] = True
        annotation["_meta"]["annotation_status"] = "review_required"
        annotation.setdefault("ambiguites", [])
        ambig = "AMBIG-6_schema_validation_errors"
        if ambig not in annotation["ambiguites"]:
            annotation["ambiguites"].append(ambig)

    # Validation cohérence financière — même en cas d'erreur schéma
    financial_warnings = _validate_financial_coherence(annotation, task_id)
    if financial_warnings:
        for w in financial_warnings:
            if w not in annotation["ambiguites"]:
                annotation["ambiguites"].append(w)
        annotation["_meta"]["review_required"] = True
        logger.error(
            "[VALIDATE] Incohérence financière task_id=%s : %s",
            task_id,
            financial_warnings,
        )

    return annotation, errors


# ─────────────────────────────────────────────────────────
# BUILDER LABEL STUDIO — structure conforme E-66
# ─────────────────────────────────────────────────────────


def _build_empty_result(task_id: int, reason: str, score: float = 0.1) -> dict:
    """
    Résultat vide traçable — quand le JSON ne peut pas être produit.
    Jamais silencieux.
    score=0.0 pour refus entrée (text_insufficient) ; défaut 0.1 pour autres cas.
    """
    fallback = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "review_required": True,
            "annotation_status": "review_required",
            "error_reason": reason,
        },
        "ambiguites": [
            "AMBIG-6_review_required",
            f"AMBIG-6_{reason[:50]}",
        ],
    }
    json_str = json.dumps(fallback, ensure_ascii=False, indent=2)
    return {
        "id": task_id,
        "score": score,
        "result": [
            {
                "from_name": "extracted_json",
                "to_name": LS_TEXTAREA_TO_NAME,
                "type": "textarea",
                "value": {"text": [json_str]},
            }
        ],
    }


def _build_ls_result(
    annotation: dict,
    task_id: int,
    has_errors: bool = False,
) -> dict:
    """
    Construit le résultat Label Studio depuis le JSON annoté.

    RÈGLE ABSOLUE :
      Toujours envoyer le JSON dans le textarea.
      Jamais de textarea vide — même si review_required=True.
      L'annotateur humain voit le JSON et peut corriger.

    Structure Label Studio stricte (E-66) :
      value.text = [string]  ← liste Python avec 1 élément string
      to_name = LS_TEXTAREA_TO_NAME  ← aligné sur <Text name="document_text"/> / toName
    """
    annotation = copy.deepcopy(annotation)

    # Pseudonymisation phone / email — valeur brute ne quitte jamais le backend
    identifiants = annotation.get("identifiants", {})
    if not isinstance(identifiants, dict):
        identifiants = {}
    phone_raw = identifiants.pop("supplier_phone_raw", ABSENT)
    email_raw = identifiants.pop("supplier_email_raw", ABSENT)
    identifiants["supplier_phone"] = _pseudonymise_contact(phone_raw)
    identifiants["supplier_email"] = _pseudonymise_contact(email_raw)
    addr = identifiants.get("supplier_address_raw", ABSENT)
    if addr not in (ABSENT, NOT_APPLICABLE, "", None):
        identifiants["supplier_address_raw"] = str(addr)[:60]
    annotation["identifiants"] = identifiants

    review_required = annotation.get("_meta", {}).get("review_required", False)
    json_str = json.dumps(annotation, ensure_ascii=False, indent=2)

    if has_errors or review_required:
        score = 0.4
    else:
        score = 0.9

    return {
        "id": task_id,
        "score": score,
        "result": [
            {
                "from_name": "extracted_json",
                "to_name": LS_TEXTAREA_TO_NAME,
                "type": "textarea",
                "value": {"text": [json_str]},
            }
        ],
    }


# APPEL MISTRAL


async def _call_mistral(
    text: str,
    task_id: int | None = None,
    document_role: str = "",
) -> dict:
    """
    Appelle Mistral v3.0.1d. Retourne le dict parsé brut (sans validation).
    document_role : si fourni, applique LOI 1bis (squelette conditionné).
    """
    if not client:
        logger.warning("[MISTRAL] Client non configuré — fallback activé")
        return copy.deepcopy(FALLBACK_RESPONSE)

    tid = task_id if task_id is not None else 0
    pre_len = len(_normalize_input_text(text))
    if pre_len < MIN_LLM_CONTEXT_CHARS:
        logger.error(
            "[MISTRAL] SKIP insufficient context task_id=%s text_len_norm=%d min=%d — pas d'appel LLM",
            tid,
            pre_len,
            MIN_LLM_CONTEXT_CHARS,
        )
        return copy.deepcopy(FALLBACK_RESPONSE)

    text = _truncate_text(text, tid)
    try:
        messages = _build_messages(text, document_role=document_role)
    except ValueError as exc:
        logger.error(
            "[MISTRAL] SKIP build_messages refusé task_id=%s — %s",
            tid,
            exc,
        )
        return copy.deepcopy(FALLBACK_RESPONSE)

    try:
        response = client.chat.complete(
            model=MISTRAL_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=32000,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        logger.info("[MISTRAL] Réponse reçue — %d caractères", len(raw))
        parsed = _parse_mistral_response(raw, task_id=tid)
        return _spot_check_annotation_vs_source(parsed, text, tid)
    except Exception as exc:
        logger.error("[MISTRAL] Erreur appel API : %s — fallback activé", exc)
        return copy.deepcopy(FALLBACK_RESPONSE)


# ENDPOINTS


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
    """Label Studio appelle /setup — retourner model_version."""
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
    Endpoint ML backend Label Studio.

    Contrat Label Studio :
      INPUT  : {"tasks": [{"id": N, "data": {"text": "..."}}]}
      OUTPUT : {"results": [{"id": N, "score": F, "result": [...]}]}

    Structure result obligatoire (E-66) :
      from_name = extracted_json (TextArea dans le XML)
      to_name   = document_text (cible toName — voir LS_TEXTAREA_TO_NAME)
      value.text = [string]  ← liste avec 1 string, jamais dict
    Données tâche : data.text ou data.content ; distinct du nom de tag LS.
    """
    try:
        body = await request.json()
    except Exception as exc:
        logger.error("[PREDICT] Body non parsable : %s", exc)
        return JSONResponse({"results": []}, status_code=200)

    tasks = body.get("tasks", [])
    if not tasks:
        return JSONResponse({"results": []})

    body_document_role = body.get("document_role", "")
    predictions = []

    for task in tasks:
        task_id = task.get("id", 0)
        task_data = task.get("data", {})
        raw_td = task_data.get("text")
        raw_cd = task_data.get("content")
        raw_text = raw_td if raw_td not in (None, "") else raw_cd
        if raw_text is None:
            raw_text = ""
        if not isinstance(raw_text, str):
            raw_text = str(raw_text)

        field_used = (
            "text"
            if raw_td not in (None, "")
            else ("content" if raw_cd not in (None, "") else "none")
        )
        text = _normalize_input_text(raw_text)
        document_role = task_data.get("document_role", "") or body_document_role
        doc_id = body.get("document_id") or task_data.get("document_id") or "n/a"

        logger.info(
            "[PREDICT] task_id=%s text_len_raw=%d text_len_norm=%d document_id=%s field=%s",
            task_id,
            len(raw_text),
            len(text),
            doc_id,
            field_used,
        )

        if not text or not text.strip():
            logger.warning(
                "[PREDICT] Texte vide — task_id=%s document_id=%s", task_id, doc_id
            )
            predictions.append(_build_empty_result(task_id, "empty_text", score=0.0))
            continue

        if len(text) < MIN_LLM_CONTEXT_CHARS:
            logger.error(
                "[PREDICT] BLOCK llm_skipped=1 reason=text_insufficient task_id=%s "
                "text_len_norm=%d min=%d document_id=%s",
                task_id,
                len(text),
                MIN_LLM_CONTEXT_CHARS,
                doc_id,
            )
            predictions.append(
                _build_empty_result(task_id, "text_insufficient", score=0.0)
            )
            continue

        stripped_len = len(text.strip())
        if stripped_len < MIN_PREDICT_TEXT_CHARS:
            logger.warning(
                "[PREDICT] Texte trop court — task_id=%s text_len=%d (min=%d)",
                task_id,
                stripped_len,
                MIN_PREDICT_TEXT_CHARS,
            )
            predictions.append(_build_empty_result(task_id, "text_too_short"))
            continue

        try:
            annotation = await _call_mistral(text, task_id, document_role=document_role)
            annotation = _normalize_gates(annotation)
            annotation, errors = _validate_and_correct(annotation, task_id)
            result = _build_ls_result(
                annotation=annotation,
                task_id=task_id,
                has_errors=bool(errors),
            )
            predictions.append(result)
        except Exception as exc:
            logger.error(
                "[PREDICT] Erreur inattendue task_id=%s : %s",
                task_id,
                exc,
                exc_info=True,
            )
            predictions.append(_build_empty_result(task_id, str(exc)[:80]))

    return JSONResponse({"results": predictions})


@app.post("/train")
async def train(request: Request) -> JSONResponse:
    """Endpoint train — réservé M12 fine-tuning Mistral. Accusé réception."""
    body = await request.json()
    n = len(body.get("annotations", []))
    logger.info("[TRAIN] %d annotations reçues — fine-tuning non actif (M12)", n)
    return JSONResponse(
        {
            "status": "received",
            "message": f"Fine-tuning réservé M12 — {n} annotations reçues",
        }
    )


@app.post("/webhook")
async def webhook_handler(request: Request) -> JSONResponse:
    """Webhook Label Studio — robuste, zéro exception non catchée. Toujours 200."""
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("[WEBHOOK] Payload non parsable : %s", type(exc).__name__)
        return JSONResponse({"status": "error", "reason": "invalid_payload"})
    action = (
        payload.get("action", "UNKNOWN") if isinstance(payload, dict) else "UNKNOWN"
    )
    logger.info("[WEBHOOK] action=%s", action)
    try:
        if action in ("ANNOTATION_CREATED", "ANNOTATION_UPDATED"):
            t = payload.get("task") or {}
            a = (
                (payload.get("annotation") or {})
                if action == "ANNOTATION_CREATED"
                else {}
            )
            logger.info(
                "[WEBHOOK] %s — task_id=%s ann_id=%s",
                action,
                t.get("id", "unknown"),
                a.get("id", "N/A"),
            )
    except Exception as exc:
        logger.error("[WEBHOOK] Erreur action=%s : %s", action, type(exc).__name__)
        return JSONResponse({"status": "error", "action": action})
    return JSONResponse({"status": "ok", "action": action})
