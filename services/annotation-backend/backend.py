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
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Import prompt — chemin absolu garanti — zéro PYTHONPATH
_backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_backend_dir))


def _find_root_with_src_annotation(start: Path) -> Path | None:
    """Remonte depuis ce dossier jusqu’à trouver src/annotation (Docker /app ou racine monorepo)."""
    cur = start.resolve()
    for _ in range(10):
        if (cur / "src" / "annotation").is_dir():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


# ARCH-02A/02B : ne pas utiliser parents[2] — sous Docker WORKDIR=/app, parents[2] lève IndexError.
_root_src = _find_root_with_src_annotation(_backend_dir)
if _root_src is not None:
    _rs = str(_root_src)
    if _rs not in sys.path:
        sys.path.insert(0, _rs)

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral  # mistralai v2.x

from annotation_qa import (
    apply_financial_warnings_to_annotation,
    evidence_substring_violations,
    financial_coherence_warnings,
    parse_loose_money_float,
)

from prompts import SYSTEM_PROMPT
from prompts.schema_validator import (
    DMSAnnotation,
    GateName,
    coerce_gate_threshold_value,
    coerce_gate_value_for_applicable,
    normalize_annotation_output,
)
from src.annotation.document_classifier import (
    DocumentRole,
    TaxonomyCore,
    classify_document,
)
from src.annotation.orchestrator import (
    AnnotationOrchestrator,
    AnnotationPipelineState,
    PipelineRunRecord,
    use_m12_subpasses,
    use_pass_orchestrator,
)

_VALID_TAXONOMY_CORE = frozenset(e.value for e in TaxonomyCore)
_VALID_DOCUMENT_ROLE = frozenset(e.value for e in DocumentRole)

# CONSTANTES — v3.0.1d ADR-015
# Label Studio : <Text name="document_text" …/> + toName="document_text" sur les contrôles (E-66)
LS_TEXTAREA_TO_NAME = "document_text"

SCHEMA_VERSION = "v3.0.1d"
FRAMEWORK_VERSION = "annotation-framework-v3.0.1d"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
# Identifiant stable pour uuid5(run_id) — bump si sémantique orchestrateur change
_ANNOTATION_PIPELINE_VERSION = "v1"


def _mistral_api_key_from_env() -> str:
    """
    Clé Mistral : ``MISTRAL_API_KEY`` (historique) ou ``DMS_API_MISTRAL`` (Railway / DMS).
    ``MISTRAL_API_KEY`` prime si les deux sont définies.
    """
    for name in ("MISTRAL_API_KEY", "DMS_API_MISTRAL"):
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        raw = raw.replace("\r", "").replace("\n", "").strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
            raw = raw[1:-1].strip()
        if raw:
            return raw
    return ""


MISTRAL_API_KEY = _mistral_api_key_from_env()
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "200000"))
# M-ANNOTATION-CONTAINMENT-01 — aligné couche A (MIN_EXTRACTED_TEXT_CHARS_FOR_ML)
MIN_LLM_CONTEXT_CHARS = int(os.environ.get("MIN_LLM_CONTEXT_CHARS", "100"))
MIN_PREDICT_TEXT_CHARS = int(os.environ.get("MIN_PREDICT_TEXT_CHARS", "200"))

_DEFAULT_FINANCIAL_REVIEW_THRESHOLD_XOF = 10_000_000.0


def _parse_financial_review_threshold_xof_from_env() -> float:
    """Seuil ARCH-04 — tolère espaces/NBSP/virgules milliers ; défaut sûr si valeur illisible."""
    raw = os.environ.get("FINANCIAL_REVIEW_THRESHOLD_XOF", "10000000")
    try:
        s = str(raw).strip()
        for ch in ("\u202f", "\u00a0", "\u2009", "\u2007", "\u2028", "\u2008"):
            s = s.replace(ch, "")
        s = re.sub(r"[\s,]+", "", s)
        if not s:
            return _DEFAULT_FINANCIAL_REVIEW_THRESHOLD_XOF
        return float(s)
    except (ValueError, TypeError):
        return _DEFAULT_FINANCIAL_REVIEW_THRESHOLD_XOF


# STRICT_PREDICT — pas de pré-annotation si schéma / finances / evidence échouent
STRICT_PREDICT = os.environ.get("STRICT_PREDICT", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _env_truthy(name: str, default: bool = True) -> bool:
    """True par défaut pour name absent ; false si 0/false/no/off."""
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off")


def _annotation_pipeline_runs_dir() -> Path:
    """Répertoire writable pour les JSON d’exécution orchestrateur.

    Si ``ANNOTATION_PIPELINE_RUNS_DIR`` est défini : chemin persistant (volume Docker, etc.).
    Sinon : sous ``tempfile.gettempdir()`` / ``dms_annotation_pipeline_runs`` — souvent **non
    persistant** au redémarrage du conteneur.
    """
    raw = (os.environ.get("ANNOTATION_PIPELINE_RUNS_DIR") or "").strip()
    if raw:
        return Path(raw)
    return Path(tempfile.gettempdir()) / "dms_annotation_pipeline_runs"


def _orchestrator_run_id(doc_id: Any, task_id: int) -> uuid.UUID:
    """UUID déterministe pour checkpoints et idempotence (même doc/tâche → même run)."""
    name = f"annotation-pipeline:{_ANNOTATION_PIPELINE_VERSION}|doc:{doc_id}|task:{task_id}"
    return uuid.uuid5(uuid.NAMESPACE_URL, name)


def _llm_text_from_orchestrator_record(record: PipelineRunRecord, fallback: str) -> str:
    p0 = (record.pass_outputs or {}).get("pass_0_ingestion") or {}
    od = p0.get("output_data") or {}
    nt = (od.get("normalized_text") or "").strip()
    return nt if nt else fallback


def _orchestrator_skip_mistral_reason(
    state: AnnotationPipelineState,
) -> str | None:
    """Si non None : pas d’appel Mistral — résultat vide traçable (raison)."""
    if state == AnnotationPipelineState.DEAD_LETTER:
        return "orchestrator_dead_letter"
    if state == AnnotationPipelineState.REVIEW_REQUIRED:
        return "orchestrator_review_required_ocr"
    if state == AnnotationPipelineState.ROUTED:
        return "orchestrator_routed_no_llm"
    if state in (
        AnnotationPipelineState.LLM_PREANNOTATION_PENDING,
        AnnotationPipelineState.PASS_1D_DONE,
        AnnotationPipelineState.PASS_2A_DONE,
    ):
        return None
    return f"orchestrator_unexpected_state_{state.value}"


def _runs_dir_health_hint() -> str:
    p = _annotation_pipeline_runs_dir()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        return "(unwritable)"
    return p.name


def _mistral_message_content_to_str(content: Any) -> str:
    """
    Mistral SDK 1.5 : ``AssistantMessage.content`` peut être str ou liste de chunks
    (ex. TextChunk). Sans normalisation, list.strip() lève → fallback AMBIG-PARSE_FAILED.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                t = item.get("text")
                if t is not None:
                    parts.append(str(t))
            elif hasattr(item, "text"):
                tx = getattr(item, "text", None)
                if tx is not None:
                    parts.append(str(tx))
        return "".join(parts)
    return str(content)


# E-27 : CORS restrictif — CORS_ORIGINS env (comma-separated)
# Default localhost:8080 pour dev. Prod Railway : définir CORS_ORIGINS=URL_LABEL_STUDIO
# SÉCURITÉ : le wildcard "*" est interdit — fallback sur localhost:8080 + CRITICAL log.
_CORS_RAW = os.environ.get("CORS_ORIGINS", "http://localhost:8080")
if _CORS_RAW.strip() == "*":
    logging.getLogger(__name__).critical(
        "[SECURITY] CORS_ORIGINS='*' est interdit — "
        "fallback sur ['http://localhost:8080']. "
        "Définir CORS_ORIGINS=<URL_LABEL_STUDIO> en production."
    )
    CORS_ORIGINS: list[str] = ["http://localhost:8080"]
else:
    CORS_ORIGINS = [o.strip() for o in _CORS_RAW.split(",") if o.strip()]

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


@asynccontextmanager
async def _annotation_lifespan(_app: FastAPI):
    logger.info(
        "[BOOT] dms-annotation-backend — uvicorn backend:app ; LS healthcheck: GET /health"
    )
    try:
        from corpus_sink import log_s3_corpus_boot_diagnostics

        log_s3_corpus_boot_diagnostics()
    except Exception:
        logger.warning(
            "[BOOT][CORPUS] Diagnostic S3 indisponible (voir stacktrace ci-dessous)",
            exc_info=True,
        )
    yield


app = FastAPI(
    title="DMS Annotation Backend",
    version=SCHEMA_VERSION,
    description=f"Framework {FRAMEWORK_VERSION}",
    lifespan=_annotation_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# FALLBACK — Mistral échoue ou JSON cassé (squelette validé DMSAnnotation)
FALLBACK_RESPONSE: dict[str, Any] = _build_fallback_response()


def _apply_deterministic_routing(
    annotation: dict[str, Any],
    source_text: str,
    task_id: int,
) -> dict[str, Any]:
    """
    ARCH-02 — Classifieur déterministe avant validation Pydantic.
    Ne définit pas review_required (spot check / ARCH-04 séparés).
    """
    annotation = copy.deepcopy(annotation)
    clf = classify_document(source_text)

    cr = annotation.get("couche_1_routing")
    if not isinstance(cr, dict):
        cr = {}
        annotation["couche_1_routing"] = cr
    meta = annotation.get("_meta")
    if not isinstance(meta, dict):
        meta = {}
        annotation["_meta"] = meta

    if clf.deterministic:
        cr["taxonomy_core"] = clf.taxonomy_core.value
        cr["document_role"] = clf.document_role.value
        meta["routing_source"] = "deterministic_classifier"
        meta["routing_matched_rule"] = clf.matched_rule
        meta["routing_confidence"] = clf.confidence
        logger.info(
            "[ROUTING] task_id=%s deterministic=1 rule=%s tax=%s role=%s",
            task_id,
            clf.matched_rule,
            clf.taxonomy_core.value,
            clf.document_role.value,
        )
    else:
        llm_tax = str(cr.get("taxonomy_core") or "")
        llm_role = str(cr.get("document_role") or "")
        if llm_tax not in _VALID_TAXONOMY_CORE or llm_role not in _VALID_DOCUMENT_ROLE:
            cr["taxonomy_core"] = TaxonomyCore.UNKNOWN.value
            cr["document_role"] = DocumentRole.UNKNOWN.value
            meta["routing_source"] = "llm_fallback_unresolved"
            logger.warning(
                "[ROUTING] task_id=%s llm_fallback_unresolved tax=%r role=%r",
                task_id,
                llm_tax,
                llm_role,
            )
        else:
            meta["routing_source"] = "llm_fallback_validated"
        meta["routing_matched_rule"] = clf.matched_rule
        meta["routing_confidence"] = clf.confidence

    return annotation


def _apply_financial_offer_review_rules(
    annotation: dict[str, Any],
    total_price_threshold: float | None = None,
) -> dict[str, Any]:
    """
    ARCH-04 — Règles locales de prudence pour offres financières (pas invariant métier DMS).
    Complète _spot_check sans le remplacer. Seuil monétaire paramétrable (env).
    """
    cr0 = annotation.get("couche_1_routing")
    if not isinstance(cr0, dict) or cr0.get("taxonomy_core") != "offer_financial":
        return annotation

    if total_price_threshold is None:
        total_price_threshold = _parse_financial_review_threshold_xof_from_env()

    annotation = copy.deepcopy(annotation)

    reasons: list[str] = []
    meta = annotation.get("_meta")
    if not isinstance(meta, dict):
        meta = {}
        annotation["_meta"] = meta

    c4 = annotation.get("couche_4_atomic")
    c4 = c4 if isinstance(c4, dict) else {}
    conformite = c4.get("conformite_admin")
    conformite = conformite if isinstance(conformite, dict) else {}
    financier = c4.get("financier")
    financier = financier if isinstance(financier, dict) else {}

    for field in ("has_nif", "has_rccm"):
        val = conformite.get(field)
        if isinstance(val, dict) and val.get("value") == ABSENT:
            reasons.append(f"admin_{field}_absent")

    line_items = financier.get("line_items")
    if not isinstance(line_items, list):
        line_items = []

    for i, item in enumerate(line_items):
        if not isinstance(item, dict):
            continue
        if item.get("line_total_check") == "ANOMALY":
            reasons.append(f"arithmetic_anomaly_item_{i + 1}")

    if not line_items:
        reasons.append("line_items_empty_on_financial_offer")

    total_raw = financier.get("total_price")
    if isinstance(total_raw, dict):
        raw_v = total_raw.get("value")
        total = parse_loose_money_float(raw_v)
        if total is not None and total > total_price_threshold:
            reasons.append(
                f"high_value_above_{int(total_price_threshold)}_local_prudence"
            )

    if reasons:
        meta["review_required"] = True
        existing = meta.get("review_reasons")
        if not isinstance(existing, list):
            existing = []
        for r in reasons:
            if r not in existing:
                existing.append(r)
        meta["review_reasons"] = existing

    annotation["_meta"] = meta
    return annotation


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


def _build_messages(
    user_content: str,
    document_role: str = "",
    source_filename: str = "",
) -> list[dict]:
    """
    Construit les messages pour l'API Mistral.
    user_content contient le document (seuls ces caractères comptent pour MIN_LLM).
    document_role / source_filename : métadonnées injectées après contrôle de longueur
    du corps (évite d'« acheter » un seuil avec un préfixe artificiel dans data.text).
    """
    normalized = _normalize_input_text(user_content)
    if len(normalized) < MIN_LLM_CONTEXT_CHARS:
        raise ValueError(
            f"INSUFFICIENT_TEXT_FOR_LLM len={len(normalized)} min={MIN_LLM_CONTEXT_CHARS}"
        )

    ctx_parts: list[str] = []
    if document_role:
        ctx_parts.append(f"CONTEXTE: document_role attendu = {document_role}")
    if source_filename:
        ctx_parts.append(f"CONTEXTE: nom_fichier_source = {source_filename}")
    prefix = ("\n\n".join(ctx_parts) + "\n\n") if ctx_parts else ""

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
def _parse_mistral_response(raw: Any, task_id: int = 0) -> tuple[dict, bool]:
    """
    Parse robuste — JSON brut, markdown, trailing commas, tronqué.

    Retourne (annotation_dict, parse_ok). Si parse_ok est False, le dict est une copie
    du squelette FALLBACK (AMBIG-PARSE_FAILED).
    """
    if not isinstance(raw, str):
        raw = _mistral_message_content_to_str(raw)
    if not raw:
        logger.warning("[PARSE] raw vide — task_id=%s", task_id)
        return copy.deepcopy(FALLBACK_RESPONSE), False

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
        return r, True
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if m and (r := _try(m.group(1).strip())) is not None:
        return r, True
    try:
        frag = raw[raw.index("{") : raw.rindex("}") + 1]
        if (r := _try(frag)) is not None:
            return r, True
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
                    return r, True
    except (ValueError, re.error):
        pass
    try:
        s = raw[raw.index("{") :]
        deficit = s.count("{") - s.count("}")
        if deficit > 0:
            s = re.sub(r",\s*$", "", s.rstrip()) + "}" * deficit
        if (r := _try(s)) is not None:
            return r, True
    except (ValueError, re.error):
        pass

    _raw_len = len(raw) if raw else 0
    _raw_hash = hashlib.sha256(raw.encode()).hexdigest()[:12] if raw else "empty"
    logger.error("[PARSE] Fallback — raw_len=%s raw_hash=%s", _raw_len, _raw_hash)
    if _env_truthy("MISTRAL_PARSE_FAILURE_LOG_PREVIEW", default=False):
        _prev = int(os.environ.get("MISTRAL_PARSE_FAILURE_PREVIEW_CHARS", "280"))
        _prev = max(80, min(_prev, 2000))
        head = raw[:_prev].replace("\n", "\\n")
        logger.error(
            "[PARSE] preview_head task_id=%s chars=%s text=%r",
            task_id,
            _prev,
            head,
        )
    return copy.deepcopy(FALLBACK_RESPONSE), False


_ALLOWED_CONFIDENCE = frozenset({0.6, 0.8, 1.0})


def _normalize_gates(annotation: dict) -> dict:
    """
    Normalise les gates AVANT validation Pydantic.

    Absorbe les imperfections systématiques de Mistral :
      1. confidence=0.0 + NOT_APPLICABLE → 1.0
         LOI 4 DMS : NOT_APPLICABLE = certitude maximale
      2. confidence=0.0 + APPLICABLE → 0.6 (minimum autorisé)
      3. APPLICABLE : gate_value null ou chaîne (OUI/NON, etc.) → bool
         (défaut False si null — évite ValidationError ; revue humaine possible dans LS)
      4. gate_threshold_value toujours présent ; chaînes numériques parsées ; illisible → null
    """
    gates = annotation.get("couche_5_gates", [])
    ambiguites = list(annotation.get("ambiguites", []))

    for gate in gates:
        if not isinstance(gate, dict):
            continue

        gate_state = gate.get("gate_state", "")
        confidence = gate.get("confidence", 0.0)

        # RÈGLE 1 : NOT_APPLICABLE → confidence = 1.0
        if gate_state == "NOT_APPLICABLE":
            if confidence != 1.0:
                gate["confidence"] = 1.0
            if gate.get("gate_value") is not None:
                gate["gate_value"] = None

        # RÈGLE 2 : APPLICABLE + confidence hors plage → 0.6 ; gate_value coercé
        elif gate_state == "APPLICABLE":
            if confidence not in _ALLOWED_CONFIDENCE:
                gate["confidence"] = 0.6
            gate["gate_value"] = coerce_gate_value_for_applicable(
                gate.get("gate_value")
            )

        # Clé toujours présente (évite « Field required » sur gate_threshold_value)
        if "gate_threshold_value" not in gate:
            gate["gate_threshold_value"] = None
        else:
            gate["gate_threshold_value"] = coerce_gate_threshold_value(
                gate.get("gate_threshold_value")
            )

    annotation["ambiguites"] = ambiguites
    return annotation


def _sync_gate_reasons_with_document_role(annotation: dict) -> dict:
    """
    Quand le routeur déterministe écrase document_role (ex. financial_offer),
    Mistral peut laisser des gate_reason_raw obsolètes « document_role = supporting_doc ».
    On aligne le libellé sur le rôle effectif pour un JSON cohérent.
    """
    cr = annotation.get("couche_1_routing")
    if not isinstance(cr, dict):
        return annotation
    role = str(cr.get("document_role") or "").strip()
    if not role or role == DocumentRole.SUPPORTING_DOC.value:
        return annotation
    gates = annotation.get("couche_5_gates")
    if not isinstance(gates, list):
        return annotation
    needle = "document_role = supporting_doc"
    for g in gates:
        if not isinstance(g, dict):
            continue
        reason = str(g.get("gate_reason_raw") or "")
        if needle in reason:
            g["gate_reason_raw"] = f"Non applicable — document_role = {role}"
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
    elif isinstance(raw_amb, tuple | set):
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


def _normalize_identifiants_for_schema(annotation: dict) -> None:
    """
    Garantit supplier_phone_raw / supplier_email_raw si le LLM n’envoie que les blocs
    supplier_phone / supplier_email (ou omet les *_raw) — évite ValidationError Identifiants.
    """
    ident = annotation.get("identifiants")
    if not isinstance(ident, dict):
        return
    if "supplier_phone_raw" not in ident:
        ident["supplier_phone_raw"] = (
            "" if isinstance(ident.get("supplier_phone"), dict) else ABSENT
        )
    if "supplier_email_raw" not in ident:
        ident["supplier_email_raw"] = (
            "" if isinstance(ident.get("supplier_email"), dict) else ABSENT
        )


def _validate_and_correct(annotation: dict, task_id: int = 0) -> tuple[dict, list]:
    """
    Valide le JSON annoté contre le schéma DMS v3.0.1d.
    Retourne (annotation_corrigée, liste_erreurs).
    Ne lève jamais d'exception — les erreurs sont tracées.
    """
    errors: list[dict] = []
    annotation = copy.deepcopy(annotation)
    _normalize_identifiants_for_schema(annotation)
    annotation = normalize_annotation_output(annotation)

    try:
        validated = DMSAnnotation.model_validate(annotation)
        annotation = validated.model_dump(by_alias=True)
        financial_warnings = financial_coherence_warnings(annotation, task_id)
        if financial_warnings:
            apply_financial_warnings_to_annotation(annotation, financial_warnings)
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

    # Validation cohérence financière — même en cas d'erreur schéma (best-effort)
    financial_warnings = financial_coherence_warnings(annotation, task_id)
    if financial_warnings:
        apply_financial_warnings_to_annotation(annotation, financial_warnings)
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
    phone_block = _pseudonymise_contact(phone_raw)
    email_block = _pseudonymise_contact(email_raw)
    identifiants["supplier_phone"] = phone_block
    identifiants["supplier_email"] = email_block
    # ADR-013 : supplier_phone_raw / supplier_email_raw ne figurent pas dans extracted_json
    # (évite toute fuite de structure ; seuls les blocs pseudonymisés sont exportés)
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
    source_filename: str = "",
) -> dict:
    """
    Appelle Mistral v3.0.1d. Retourne le dict parsé brut (sans validation).
    document_role : si fourni, applique LOI 1bis (squelette conditionné).
    source_filename : nom fichier LS / bridge (signal quand l'en-tête PDF est image).
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
        messages = _build_messages(
            text,
            document_role=document_role,
            source_filename=source_filename,
        )
    except ValueError as exc:
        logger.error(
            "[MISTRAL] SKIP build_messages refusé task_id=%s — %s",
            tid,
            exc,
        )
        return copy.deepcopy(FALLBACK_RESPONSE)

    try:

        def _complete() -> str:
            response = client.chat.complete(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=32000,
                response_format={"type": "json_object"},
            )
            msg = response.choices[0].message
            return _mistral_message_content_to_str(getattr(msg, "content", None))

        raw = _complete()
        logger.info("[MISTRAL] Réponse reçue — %d caractères", len(raw))
        parsed, parse_ok = _parse_mistral_response(raw, task_id=tid)
        if (
            not parse_ok
            and _env_truthy("MISTRAL_PARSE_RETRY", default=True)
            and client is not None
        ):
            logger.warning(
                "[MISTRAL] Échec parse JSON — nouvel essai task_id=%s model=%s",
                tid,
                MISTRAL_MODEL,
            )
            raw2 = _complete()
            logger.info(
                "[MISTRAL] Réponse retry — %d caractères",
                len(raw2),
            )
            parsed2, ok2 = _parse_mistral_response(raw2, task_id=tid)
            if ok2:
                parsed = parsed2
        return _spot_check_annotation_vs_source(parsed, text, tid)
    except Exception as exc:
        logger.error("[MISTRAL] Erreur appel API : %s — fallback activé", exc)
        return copy.deepcopy(FALLBACK_RESPONSE)


# ENDPOINTS


def _webhook_corpus_secret_ok(request: Request) -> bool:
    """Si ``WEBHOOK_CORPUS_SECRET`` est défini, exiger ``X-Webhook-Secret`` identique."""
    secret = os.environ.get("WEBHOOK_CORPUS_SECRET", "").strip()
    if not secret:
        return True
    got = request.headers.get("X-Webhook-Secret", "").strip()
    return hmac.compare_digest(got, secret)


def _corpus_webhook_enabled() -> bool:
    """Aligné sur ``corpus_webhook._env_bool`` — pas d’import du module si désactivé."""
    v = os.environ.get("CORPUS_WEBHOOK_ENABLED", "").strip().lower()
    if not v:
        return False
    return v in ("1", "true", "yes", "on")


def _run_corpus_webhook(payload: dict[str, Any]) -> None:
    """Import paresseux uniquement si corpus activé (évite coût / erreurs quand CORPUS_WEBHOOK_ENABLED=0)."""
    if not _corpus_webhook_enabled():
        return
    try:
        from corpus_webhook import process_label_studio_webhook_for_corpus

        process_label_studio_webhook_for_corpus(payload)
    except Exception as exc:
        logger.error(
            "[WEBHOOK][CORPUS] %s — %s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )


def _health_payload() -> dict[str, Any]:
    """Réponse unique pour toutes les URLs de santé (LS 1.23 : GET …/health)."""
    return {
        "status": "ok",
        "service": "dms-annotation-backend",
        "schema": SCHEMA_VERSION,
        "framework": FRAMEWORK_VERSION,
        "model": MISTRAL_MODEL,
        "mistral_configured": bool(MISTRAL_API_KEY),
        "strict_predict": STRICT_PREDICT,
        "pass_orchestrator_enabled": use_pass_orchestrator(),
        "m12_subpasses_enabled": use_m12_subpasses(),
        "orchestrator_runs_dir_hint": _runs_dir_health_hint(),
    }


@app.get("/")
def root() -> dict[str, str]:
    """Permet de vifier rapidement que ce n’est pas l’API DMS racine (main:app)."""
    return {
        "service": "dms-annotation-backend",
        "health": "/health",
        "setup": "/setup",
        "predict": "/predict",
    }


@app.get("/health")
@app.get("/health/")
@app.get("/api/health")
def health() -> dict[str, Any]:
    return _health_payload()


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
        raw_body = await request.body()
    except Exception as exc:
        logger.error(
            "[PREDICT] Lecture corps impossible : %s — %r",
            type(exc).__name__,
            exc,
        )
        return JSONResponse({"results": []}, status_code=200)

    if not raw_body.strip():
        logger.warning(
            "[PREDICT] Corps HTTP vide — JSON attendu "
            "(souvent abort client, probe, ou LS). content-type=%r",
            request.headers.get("content-type", ""),
        )
        return JSONResponse({"results": []}, status_code=200)

    try:
        body = json.loads(raw_body.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        body_len = len(raw_body)
        content_type = request.headers.get("content-type", "")
        body_sha256 = hashlib.sha256(raw_body).hexdigest()
        logger.error(
            "[PREDICT] JSON invalide : %s (pos=%s) body_len=%s "
            "content_type=%r body_sha256=%s",
            exc.msg,
            exc.pos,
            body_len,
            content_type,
            body_sha256,
        )
        return JSONResponse({"results": []}, status_code=200)
    except UnicodeDecodeError as exc:
        logger.error("[PREDICT] Corps non UTF-8 : %s", exc)
        return JSONResponse({"results": []}, status_code=200)

    if not isinstance(body, dict):
        logger.error(
            "[PREDICT] JSON racine attendu (objet), reçu %s",
            type(body).__name__,
        )
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
        raw_fn = task_data.get("filename")
        source_filename = (
            raw_fn.strip() if isinstance(raw_fn, str) and raw_fn.strip() else ""
        )
        doc_id = body.get("document_id") or task_data.get("document_id") or "n/a"
        task_case_id = task_data.get("case_id") or body.get("case_id") or None

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

        text_for_llm = text
        if use_pass_orchestrator():
            runs_dir = _annotation_pipeline_runs_dir()
            try:
                runs_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.error(
                    "[PREDICT] ANNOTATION_PIPELINE_RUNS_DIR inaccessible : %s",
                    exc,
                )
                predictions.append(
                    _build_empty_result(task_id, "orchestrator_runs_dir_unwritable")
                )
                continue
            run_id = _orchestrator_run_id(
                doc_id, int(task_id) if task_id is not None else 0
            )
            orch = AnnotationOrchestrator(runs_dir=runs_dir)
            try:
                orch_record, orch_state = await run_in_threadpool(
                    orch.run_passes_0_to_1,
                    text,
                    document_id=str(doc_id),
                    run_id=run_id,
                    filename=source_filename or None,
                    case_id=task_case_id,
                )
            except Exception as exc:
                logger.error(
                    "[PREDICT] orchestrator error: %s",
                    exc,
                    exc_info=True,
                )
                predictions.append(_build_empty_result(task_id, "orchestrator_error"))
                continue

            if _env_truthy("ANNOTATION_ORCHESTRATOR_DUAL_LOG", default=False):
                logger.info(
                    "[PREDICT] orchestrator state=%s pass_keys=%s",
                    orch_state.value,
                    list((orch_record.pass_outputs or {}).keys()),
                )

            skip_reason = _orchestrator_skip_mistral_reason(orch_state)
            if skip_reason:
                predictions.append(_build_empty_result(task_id, skip_reason))
                continue

            text_for_llm = _llm_text_from_orchestrator_record(orch_record, text)

        try:
            annotation = await _call_mistral(
                text_for_llm,
                task_id,
                document_role=document_role,
                source_filename=source_filename,
            )
            annotation = _apply_deterministic_routing(annotation, text, task_id)
            annotation = _normalize_gates(annotation)
            annotation = _sync_gate_reasons_with_document_role(annotation)
            annotation, errors = _validate_and_correct(annotation, task_id)
            annotation = _apply_financial_offer_review_rules(annotation)
            if STRICT_PREDICT:
                if errors:
                    predictions.append(
                        _build_empty_result(
                            task_id,
                            "strict_schema_failed",
                            score=0.1,
                        )
                    )
                    continue
                fin_strict = financial_coherence_warnings(annotation, task_id)
                if fin_strict:
                    predictions.append(
                        _build_empty_result(
                            task_id,
                            f"strict_financial_failed:{fin_strict[0][:60]}",
                            score=0.1,
                        )
                    )
                    continue
                ev_strict = evidence_substring_violations(annotation, text)
                if ev_strict:
                    predictions.append(
                        _build_empty_result(
                            task_id,
                            f"strict_evidence_failed:{ev_strict[0][:60]}",
                            score=0.1,
                        )
                    )
                    continue
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
async def webhook_handler(
    request: Request, background_tasks: BackgroundTasks
) -> JSONResponse:
    """Webhook Label Studio — robuste, zéro exception non catchée. Réponse 200 sauf secret KO."""
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("[WEBHOOK] Payload non parsable : %s", type(exc).__name__)
        return JSONResponse({"status": "error", "reason": "invalid_payload"})
    if not _webhook_corpus_secret_ok(request):
        logger.warning("[WEBHOOK] unauthorized — secret mismatch")
        return JSONResponse(
            {"status": "error", "reason": "unauthorized"}, status_code=401
        )
    if isinstance(payload, dict):
        background_tasks.add_task(_run_corpus_webhook, payload)
    action = (
        payload.get("action", "UNKNOWN") if isinstance(payload, dict) else "UNKNOWN"
    )
    logger.info("[WEBHOOK] action=%s", action)
    try:
        if action in ("ANNOTATION_CREATED", "ANNOTATION_UPDATED"):
            t = payload.get("task") if isinstance(payload.get("task"), dict) else {}
            t = t or {}
            a = (
                payload.get("annotation")
                if isinstance(payload.get("annotation"), dict)
                else {}
            )
            a = a or {}
            tid = t.get("id")
            if tid is None and payload.get("task_id") is not None:
                tid = payload.get("task_id")
            logger.info(
                "[WEBHOOK] %s — task_id=%s ann_id=%s",
                action,
                tid if tid is not None else "unknown",
                a.get("id", "N/A"),
            )
    except Exception as exc:
        logger.error("[WEBHOOK] Erreur action=%s : %s", action, type(exc).__name__)
        return JSONResponse({"status": "error", "action": action})
    return JSONResponse({"status": "ok", "action": action})
