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

# CONSTANTES — v3.0.1d ADR-015
SCHEMA_VERSION = "v3.0.1d"
FRAMEWORK_VERSION = "annotation-framework-v3.0.1d"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "80000"))

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
    allow_origins=["*"],
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
    # Protéger contre les types inattendus renvoyés par le LLM (string/list/null, etc.)
    if not isinstance(identifiants, dict):
        identifiants = {}

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


# APPEL MISTRAL


async def _mistral_extract(text: str, task_id: int | None = None) -> dict:
    """Appelle Mistral v3.0.1d. Retourne le dict parsé ou FALLBACK_RESPONSE."""
    if not client:
        logger.warning("[MISTRAL] Client non configuré — fallback activé")
        return FALLBACK_RESPONSE

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
        return FALLBACK_RESPONSE


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
    """Label Studio → pré-annotations Mistral. 1 tâche = 1 document."""
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
            parsed = await _mistral_extract(text, task_id=task_id)

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
