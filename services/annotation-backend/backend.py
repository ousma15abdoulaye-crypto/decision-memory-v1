"""
ML Backend — DMS Annotation Service
Milestone    : M11-bis / M12
Référence    : MANDAT-LS-002-v1
Auteur       : CTO / AO — Abdoulaye Ousmane
Date         : 2026-03-14

Règle R-05   : zéro stockage document — transit uniquement
Règle R-10   : mistralai>=1.0.0 — API v1.x uniquement
RÈGLE-19     : value + confidence + evidence_hint partout
Corpus Mali  : 3 docs référence — types et régimes figés
"""

import json
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from mistralai import Mistral

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("dms-annotation-backend")

app = FastAPI(
    title="DMS Annotation ML Backend",
    version="1.2.0",
    docs_url=None,
)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")


# ── Modèles ──────────────────────────────────────────────────────


class AnnotationTask(BaseModel):
    id: int
    data: dict[str, Any]


class PredictionRequest(BaseModel):
    tasks: list[AnnotationTask]
    model_version: str | None = None
    project: int | None = None


# ── Healthcheck ──────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {
        "status": "UP",
        "model": MISTRAL_MODEL,
        "mistral_configured": bool(MISTRAL_API_KEY),
        "api_version": "v1.x",
        "corpus_version": "Mali-3docs-v1",
    }


@app.get("/setup")
async def setup():
    return {
        "model_version": "dms-mistral-v1.2",
        "status": "ready",
    }


# ── Prédiction ───────────────────────────────────────────────────


@app.post("/predict")
async def predict(request: PredictionRequest):
    if not MISTRAL_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="MISTRAL_API_KEY non configurée",
        )

    client = Mistral(api_key=MISTRAL_API_KEY)
    predictions = []

    for task in request.tasks:
        text = (
            task.data.get("text")
            or task.data.get("content")
            or task.data.get("document", "")
        )

        if not text:
            predictions.append({"id": task.id, "result": [], "score": 0.0})
            continue

        try:
            prompt = _build_extraction_prompt(text)
            response = client.chat.complete(
                model=MISTRAL_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content
            result = _parse_mistral_response(raw, task.id)

            predictions.append({
                "id": task.id,
                "result": result,
                "score": 0.80,
                "model_version": "dms-mistral-v1.2",
            })

        except Exception as e:
            logger.error("Task %s failed: %s", task.id, e)
            predictions.append({"id": task.id, "result": [], "score": 0.0})

    return JSONResponse({"results": predictions})


@app.post("/webhook")
async def webhook(payload: dict[str, Any]):
    action = payload.get("action", "unknown")
    logger.info("Webhook reçu : action=%s", action)
    return {"status": "received", "action": action}


# ── Helpers ──────────────────────────────────────────────────────


def _build_extraction_prompt(text: str) -> str:
    return f"""Tu es un extracteur de données procurement Mali — Save the Children International.
Retourne UNIQUEMENT un JSON valide, sans texte autour.

FORMAT :
{{
  "doc_type": "rfp_consultance|devissimple|devisunique|devisformel|autre",
  "doc_type_confidence": 1.0,
  "doc_type_evidence": "texte exact du document justifiant le type",

  "regime_dominant": "AUTOMATIQUE|CONDITIONNEL|PENALITE_FISCALE|MIXTE|AUCUN",

  "criteres_admin": {{
    "sci":                        {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "iapg":                       {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "non_sanction":               {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "rccm":                       {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "nif":                        {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "certificat_non_faillite":    {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "quitus_fiscal":              {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "rib":                        {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "piece_identite_representant":{{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "statuts":                    {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}},
    "ariba_network":              {{"requis": false, "regime": "AUCUN",        "confidence": 1.0, "evidence_hint": ""}}
  }},

  "champs_extractibles": {{
    "reference_dossier":      {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "date_limite_soumission": {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "entite_emettrice":       {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "zone_geo":               {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "montant_estimatif":      {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "devise":                 {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "delai_execution":        {{"value": null, "confidence": 1.0, "evidence_hint": ""}},
    "langue":                 {{"value": null, "confidence": 1.0, "evidence_hint": ""}}
  }},

  "ambiguites": [],
  "confiance_globale": 1.0
}}

RÈGLES STRICTES :
- confidence : 1.0 (certain) | 0.80 (déduit) | 0.60 (flou) — jamais autre valeur
- evidence_hint : 5-10 mots exacts du document — jamais inventé
- Valeur absente = null — jamais chaîne vide
- Dates : YYYY-MM-DD uniquement
- Montants : chiffres purs sans espaces ni virgules
- regime élimination : lire CHAMP PAR CHAMP — jamais généraliser depuis doc_type
- AUTOMATIQUE = mot "entrainera" ou "exclusion immédiate"
- CONDITIONNEL = mot "peut engendrer" + "à l'appréciation du comité"
- PENALITE_FISCALE = retenue 15% BIC — contractualisation possible
- MIXTE = plusieurs régimes dans le même document
- Ne jamais inventer un critère absent du document

DOCUMENT :
{text[:4000]}
"""


def _parse_mistral_response(raw: str, task_id: int) -> list[dict]:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return []

        data = json.loads(raw[start:end])
        results = []

        # doc_type → choices Label Studio
        if data.get("doc_type") and data["doc_type"] != "inconnu":
            results.append({
                "type": "choices",
                "value": {"choices": [data["doc_type"]]},
                "from_name": "doc_type",
                "to_name": "document_text",
                "origin": "prediction",
                "score": data.get("doc_type_confidence", 0.80),
            })

        # criteres_admin → choices Label Studio
        criteres_presents = [
            k for k, v in data.get("criteres_admin", {}).items()
            if isinstance(v, dict) and v.get("requis") is True
        ]
        if criteres_presents:
            results.append({
                "type": "choices",
                "value": {"choices": criteres_presents},
                "from_name": "criteres_admin",
                "to_name": "document_text",
                "origin": "prediction",
                "score": 0.80,
            })

        # regime_dominant → choices Label Studio
        if data.get("regime_dominant"):
            results.append({
                "type": "choices",
                "value": {"choices": [data["regime_dominant"]]},
                "from_name": "regime_dominant",
                "to_name": "document_text",
                "origin": "prediction",
                "score": 0.80,
            })

        # confiance_globale → rating Label Studio
        confiance = data.get("confiance_globale", 0.60)
        if confiance >= 1.0:
            rating = 3
        elif confiance >= 0.80:
            rating = 2
        else:
            rating = 1
        results.append({
            "type": "rating",
            "value": {"rating": rating},
            "from_name": "confidence",
            "to_name": "document_text",
            "origin": "prediction",
        })

        # ambiguites → notes Label Studio
        ambiguites = data.get("ambiguites", [])
        if ambiguites:
            results.append({
                "type": "textarea",
                "value": {"text": ambiguites},
                "from_name": "notes",
                "to_name": "document_text",
                "origin": "prediction",
            })

        return results

    except Exception as e:
        logger.warning("Parse failed task %s: %s", task_id, e)
        return []
