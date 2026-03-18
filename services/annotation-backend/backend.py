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

# Import prompt — chemin absolu garanti — zéro PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mistralai import Mistral
from prompts import SYSTEM_PROMPT
from prompts.schema_validator import DMSAnnotation
from pydantic import ValidationError

# CONSTANTES — v3.0.1d ADR-015
SCHEMA_VERSION = "v3.0.1d"
FRAMEWORK_VERSION = "annotation-framework-v3.0.1d"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "80000"))

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

# FALLBACK — Mistral échoue ou JSON cassé
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
        "annotation_status": "pending",
        "list_null_reason": {},
        "page_range": {"start": None, "end": None},
        "parent_document_id": NOT_APPLICABLE,
        "parent_document_role": NOT_APPLICABLE,
        "supplier_inherited_from": None,
    },
}


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


def _build_messages(user_content: str) -> list[dict]:
    """
    Construit les messages pour l'API Mistral.
    user_content contient le document. Instruction JSON pour response_format=json_object.
    """
    user_prompt = (
        f"{user_content}\n\n"
        "Extraire les données en JSON selon les règles du prompt système."
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
        return dict(FALLBACK_RESPONSE)

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
        annotation.setdefault("ambiguites", [])
        ambig = "AMBIG-6_schema_validation_errors"
        if ambig not in annotation["ambiguites"]:
            annotation["ambiguites"].append(ambig)

    return annotation, errors


# ─────────────────────────────────────────────────────────
# BUILDER LABEL STUDIO — structure conforme E-66
# ─────────────────────────────────────────────────────────


def _build_empty_result(task_id: int, reason: str) -> dict:
    """
    Résultat vide traçable — quand le JSON ne peut pas être produit.
    Jamais silencieux.
    """
    fallback = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "review_required": True,
            "annotation_status": "pending",
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
        "score": 0.1,
        "result": [
            {
                "from_name": "extracted_json",
                "to_name": "text",
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
      to_name = "text"      ← DOIT matcher XML Label Studio
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
                "to_name": "text",
                "type": "textarea",
                "value": {"text": [json_str]},
            }
        ],
    }


# APPEL MISTRAL


async def _call_mistral(text: str, task_id: int | None = None) -> dict:
    """
    Appelle Mistral v3.0.1d. Retourne le dict parsé brut (sans validation).
    En cas d'erreur : FALLBACK_RESPONSE.
    """
    if not client:
        logger.warning("[MISTRAL] Client non configuré — fallback activé")
        return dict(FALLBACK_RESPONSE)

    tid = task_id if task_id is not None else 0
    text = _truncate_text(text, tid)
    messages = _build_messages(text)

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
        return _parse_mistral_response(raw, task_id=tid)
    except Exception as exc:
        logger.error("[MISTRAL] Erreur appel API : %s — fallback activé", exc)
        return dict(FALLBACK_RESPONSE)


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
      from_name = nom du widget dans le XML Label Studio
      to_name   = "text" (objet Data dans le XML)
      value.text = [string]  ← liste avec 1 string, jamais dict
    """
    try:
        body = await request.json()
    except Exception as exc:
        logger.error("[PREDICT] Body non parsable : %s", exc)
        return JSONResponse({"results": []}, status_code=200)

    tasks = body.get("tasks", [])
    if not tasks:
        return JSONResponse({"results": []})

    predictions = []

    for task in tasks:
        task_id = task.get("id", 0)
        task_data = task.get("data", {})
        text = task_data.get("text", "") or task_data.get("content", "") or ""

        logger.info("[PREDICT] task_id=%s text_len=%d", task_id, len(text))

        if not text or not text.strip():
            logger.warning("[PREDICT] Texte vide — task_id=%s", task_id)
            predictions.append(_build_empty_result(task_id, "empty_text"))
            continue

        try:
            annotation = await _call_mistral(text, task_id)
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
