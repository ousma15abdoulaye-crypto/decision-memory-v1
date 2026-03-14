"""
DMS Annotation ML Backend — Enterprise Grade
Label Studio ML Backend Protocol compatible
Mistral AI integration — Mali Procurement v4.1
"""

import os
import json
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mistralai import Mistral

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DMS Annotation Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_MODEL   = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
LS_URL          = os.environ.get("LS_URL", "")
LS_API_KEY      = os.environ.get("LS_API_KEY", "")

client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return JSONResponse({
        "status": "UP",
        "model": MISTRAL_MODEL,
        "mistral_configured": bool(MISTRAL_API_KEY),
        "api_version": "v2.0",
        "corpus_version": "Mali-3docs-v1"
    })


# ─────────────────────────────────────────────
# SETUP — Label Studio handshake (POST requis)
# ─────────────────────────────────────────────
@app.post("/setup")
async def setup(request: Request):
    """
    Label Studio envoie POST /setup lors de la connexion.
    Retourner model_version pour confirmer la compatibilité.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    logger.info(f"[setup] Label Studio handshake reçu : {body}")
    return JSONResponse({
        "model_version": "dms-mali-v2.0",
        "status": "ok"
    })


# ─────────────────────────────────────────────
# PREDICT — Prédictions batch pour Label Studio
# ─────────────────────────────────────────────
@app.post("/predict")
async def predict(request: Request):
    """
    Label Studio envoie POST /predict avec tasks[].
    On retourne des pré-annotations Mistral pour chaque tâche.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"results": []}, status_code=200)

    tasks = body.get("tasks", [])
    logger.info(f"[predict] {len(tasks)} tâches reçues")

    results = []
    for task in tasks:
        task_id = task.get("id", 0)
        data    = task.get("data", {})
        text    = data.get("text", "") or data.get("content", "") or ""

        if not text.strip() or not client:
            results.append({
                "id": task_id,
                "result": [],
                "score": 0.0
            })
            continue

        try:
            extraction = await _mistral_extract(text)
            result     = _build_ls_result(extraction)
            results.append({
                "id":     task_id,
                "result": result,
                "score":  extraction.get("confidence", 0.75),
                "model_version": "dms-mali-v2.0"
            })
            logger.info(f"[predict] task {task_id} → {extraction.get('doc_type','?')}")
        except Exception as e:
            logger.error(f"[predict] task {task_id} erreur : {e}")
            results.append({"id": task_id, "result": [], "score": 0.0})

    return JSONResponse({"results": results})


# ─────────────────────────────────────────────
# TRAIN — Déclenchement entraînement
# ─────────────────────────────────────────────
@app.post("/train")
async def train(request: Request):
    """
    Label Studio envoie POST /train quand annotations validées.
    On log les annotations reçues pour future fine-tuning.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    annotations = body.get("annotations", [])
    logger.info(f"[train] {len(annotations)} annotations reçues pour fine-tuning")

    # TODO M12 : déclencher fine-tuning Mistral via API
    return JSONResponse({
        "status": "ok",
        "message": f"{len(annotations)} annotations enregistrées",
        "job_id": None
    })


# ─────────────────────────────────────────────
# WEBHOOK — Events Label Studio
# ─────────────────────────────────────────────
@app.post("/webhook")
async def webhook(payload: dict[str, Any]):
    event = payload.get("action", "unknown")
    logger.info(f"[webhook] event={event}")
    return JSONResponse({"status": "received", "event": event})


# ─────────────────────────────────────────────
# MISTRAL EXTRACTION — Procurement Mali v4.1
# ─────────────────────────────────────────────
async def _mistral_extract(text: str) -> dict:
    """
    Appelle Mistral pour extraire les critères procurement Mali.
    Retourne un dict structuré conforme au schema DMS v4.1.
    """
    prompt = _build_extraction_prompt(text)

    response = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1500
    )

    raw = response.choices[0].message.content.strip()
    return _parse_mistral_response(raw)


def _build_extraction_prompt(text: str) -> str:
    return f"""Tu es un expert en procurement UNICEF Mali.
Analyse ce document et extrais les informations suivantes en JSON strict.

DOCUMENT:
{text[:4000]}

RÉPONDRE UNIQUEMENT EN JSON avec cette structure exacte:
{{
  "doc_type": "dao|rfq|rfp_consultance|tdr_consultance_audit|offre_technique|offre_financiere|devis_simple|devis_unique|devis_formel|marketsurvey",
  "criteres_essentiels": ["nif","rccm","rib","sci_conditions","non_sanction","iapg","certificat_non_faillite","quitus_fiscal","piece_identite_representant","statuts_societe","ariba_network","attestation_fiscale"],
  "criteres_commerciaux": ["prix_unitaire","prix_total_ttc","delai_livraison_jours","validite_offre_jours","modalite_paiement","garantie_produit","moins_disant_formule","incoterm","lieu_livraison"],
  "criteres_capacite": ["annees_experience_chef_mission","nb_etudes_similaires_cabinet","methodologie_approche","plan_travail_chronogramme","qualification_diplome","references_clients","presence_zone"],
  "criteres_durabilite": ["impact_environnemental","genre_inclusion_sociale","fournisseur_local_mali","impact_communautaire","certifications_durabilite"],
  "regime_dominant": "AUTOMATIQUE|CONDITIONNEL|PENALITE_FISCALE|MIXTE|AUCUN",
  "ponderation_coherente": "100_exact|non_precisee_dans_doc|incomplete_inferieur_100|incoherente_superieur_100",
  "ambiguites": ["AMBIG-1_montant_absent","AMBIG-2_ponderation_manquante","AMBIG-3_reference_contradictoire"],
  "evidence_hint": "5-10 mots exacts du document justifiant la classification",
  "confidence": 0.85
}}

RÈGLES:
- N'inclure dans chaque liste QUE les critères PRÉSENTS dans le document
- confidence entre 0.60 (OCR dégradé) et 1.00 (texte exact)
- evidence_hint = citation exacte du document
- Si incertain → confidence ≤ 0.70
"""


def _parse_mistral_response(raw: str) -> dict:
    """Parse la réponse JSON de Mistral avec fallback."""
    try:
        # Extraire le JSON même si entouré de texte
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.error(f"[parse] Erreur JSON : {e} — raw={raw[:200]}")

    return {
        "doc_type": "dao",
        "criteres_essentiels": [],
        "criteres_commerciaux": [],
        "criteres_capacite": [],
        "criteres_durabilite": [],
        "regime_dominant": "AUCUN",
        "ponderation_coherente": "non_precisee_dans_doc",
        "ambiguites": [],
        "evidence_hint": "",
        "confidence": 0.60
    }


def _build_ls_result(extraction: dict) -> list[dict]:
    """
    Convertit l'extraction Mistral en format Label Studio result[].
    Chaque champ du formulaire XML devient un result item.
    """
    results = []

    # doc_type
    if extraction.get("doc_type"):
        results.append({
            "type": "choices",
            "from_name": "doc_type",
            "to_name": "document_text",
            "value": {"choices": [extraction["doc_type"]]}
        })

    # criteres_essentiels
    if extraction.get("criteres_essentiels"):
        results.append({
            "type": "choices",
            "from_name": "criteres_essentiels",
            "to_name": "document_text",
            "value": {"choices": extraction["criteres_essentiels"]}
        })

    # criteres_commerciaux
    if extraction.get("criteres_commerciaux"):
        results.append({
            "type": "choices",
            "from_name": "criteres_commerciaux",
            "to_name": "document_text",
            "value": {"choices": extraction["criteres_commerciaux"]}
        })

    # criteres_capacite
    if extraction.get("criteres_capacite"):
        results.append({
            "type": "choices",
            "from_name": "criteres_capacite",
            "to_name": "document_text",
            "value": {"choices": extraction["criteres_capacite"]}
        })

    # criteres_durabilite
    if extraction.get("criteres_durabilite"):
        results.append({
            "type": "choices",
            "from_name": "criteres_durabilite",
            "to_name": "document_text",
            "value": {"choices": extraction["criteres_durabilite"]}
        })

    # regime_dominant
    if extraction.get("regime_dominant"):
        results.append({
            "type": "choices",
            "from_name": "regime_dominant",
            "to_name": "document_text",
            "value": {"choices": [extraction["regime_dominant"]]}
        })

    # ponderation_coherente
    if extraction.get("ponderation_coherente"):
        results.append({
            "type": "choices",
            "from_name": "ponderation_coherente",
            "to_name": "document_text",
            "value": {"choices": [extraction["ponderation_coherente"]]}
        })

    # ambiguites
    if extraction.get("ambiguites"):
        results.append({
            "type": "choices",
            "from_name": "ambiguites",
            "to_name": "document_text",
            "value": {"choices": extraction["ambiguites"]}
        })

    # evidence_hint → textarea notes
    if extraction.get("evidence_hint"):
        results.append({
            "type": "textarea",
            "from_name": "notes",
            "to_name": "document_text",
            "value": {"text": [extraction["evidence_hint"]]}
        })

    return results
