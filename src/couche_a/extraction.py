"""
Extraction documentaire – M3A: Typed criterion extraction.
"""

import asyncio
import concurrent.futures
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from src.couche_a.extraction_models import (
    ExtractionField,
    LineItem,
    TDRExtractionResult,
    Tier,
    make_fallback_result,
)
from src.couche_a.llm_router import router
from src.db import db_execute, get_connection

logger = logging.getLogger(__name__)

# ── Mapping offer_type → document_role DMS ───────────────────
_OFFER_TYPE_TO_ROLE: dict[str, str] = {
    "technique": "technical_offer",
    "financiere": "financial_offer",
    "administrative": "supporting_doc",
    "registre": "supporting_doc",
}

# ADR-0010 D3 -- no evaluation import in couche_a; values inlined from procurement rules
_MIN_WEIGHTS: dict[str, float] = {"commercial": 0.40, "sustainability": 0.10}


# ------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------
@dataclass
class DaoCriterion:
    """Structure d'un critère DAO brut."""

    categorie: str
    critere_nom: str
    description: str
    ponderation: float
    type_reponse: str = "text"
    seuil_elimination: float = None
    ordre_affichage: int = 0


# ------------------------------------------------------------
# TEXT EXTRACTION
# ------------------------------------------------------------
def extract_text_any(filepath: str) -> str:
    """Extract text from PDF, DOCX, or other supported formats."""
    from docx import Document as DocxDocument
    from pypdf import PdfReader

    path = Path(filepath)
    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        elif suffix in {".docx", ".doc"}:
            doc = DocxDocument(str(path))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        else:
            return path.read_text(errors="ignore")
    except Exception as e:
        logger.error(f"[EXTRACTION] Failed to extract text from {filepath}: {e}")
        return ""


# ------------------------------------------------------------
# CRITERION CLASSIFICATION
# ------------------------------------------------------------
def classify_criterion(text: str) -> str:
    """
    Détecte la catégorie d'un critère à partir de mots-clés.
    Retourne : 'essential', 'commercial', 'capacity', 'sustainability'.
    """
    text_lower = text.lower()

    # Essential (éliminatoire)
    essential_kw = [
        "obligatoire",
        "requis",
        "must",
        "exigé",
        "exige",
        "impératif",
        "imperatif",
        "imperativement",
        "impérativement",
        "essentiel",
        "conditions générales",
        "conditions generales",
        "certifie",
        "sanctions",
        "terrorisme",
        "admissibilité",
        "admissibilite",
        "admis",
        "déclaration sur l'honneur",
        "declaration sur l'honneur",
    ]
    if any(k in text_lower for k in essential_kw):
        return "essential"

    # Commercial (prix, délai, paiement)
    commercial_kw = [
        "prix",
        "coût",
        "montant",
        "tarif",
        "délai",
        "livraison",
        "paiement",
        "financial",
        "cost",
        "price",
        "budget",
        "payment",
    ]
    if any(k in text_lower for k in commercial_kw):
        return "commercial"

    # Capacity (expérience, références, qualité)
    capacity_kw = [
        "expérience",
        "références",
        "qualification",
        "certification",
        "capacité",
        "personnel",
        "equipment",
        "facilities",
        "qualité",
        "experience",
        "quality",
        "certified",
        "staff",
    ]
    if any(k in text_lower for k in capacity_kw):
        return "capacity"

    # Sustainability (environnement, social)
    sustain_kw = [
        "environnement",
        "social",
        "durabilité",
        "durabilite",
        "durable",
        "rse",
        "éthique",
        "ethique",
        "développement durable",
        "developpement durable",
        "sustainable",
        "green",
        "eco",
        "environmental",
        "ethical",
        "gender",
        "diversity",
        "child labor",
    ]
    if any(k in text_lower for k in sustain_kw):
        return "sustainability"

    # Fallback
    return "capacity"


# ------------------------------------------------------------
# WEIGHTING VALIDATION
# ------------------------------------------------------------
def validate_criterion_weightings(criteria: list[dict]) -> tuple[bool, list[str]]:
    """
    Valide les pondérations minimales (commercial ≥40%, durabilité ≥10%).
    Retourne (is_valid, liste_erreurs).
    """
    min_weights = _MIN_WEIGHTS
    errors = []

    # Somme des poids par catégorie
    cat_weights = {"commercial": 0.0, "sustainability": 0.0}
    for c in criteria:
        cat = c.get("criterion_category")
        weight = c.get("ponderation", 0.0)
        if cat in cat_weights:
            cat_weights[cat] += weight

    # Vérification
    if cat_weights["commercial"] < min_weights["commercial"] * 100:
        errors.append(
            f"Pondération commerciale trop faible: {cat_weights['commercial']:.1f}% "
            f"(min {min_weights['commercial'] * 100}%)"
        )
    if cat_weights["sustainability"] < min_weights["sustainability"] * 100:
        errors.append(
            f"Pondération durabilité trop faible: {cat_weights['sustainability']:.1f}% "
            f"(min {min_weights['sustainability'] * 100}%)"
        )

    return len(errors) == 0, errors


# ------------------------------------------------------------
# STRUCTURED DAO EXTRACTION (stub for now)
# ------------------------------------------------------------
def extract_dao_criteria_structured(text: str) -> list[DaoCriterion]:
    """
    Extract structured criteria from DAO text.
    This is a simplified stub - in production, this would use more sophisticated parsing.
    """
    criteria = []

    # Simple regex-based extraction (placeholder logic)
    # In a real implementation, this would use proper document parsing
    lines = text.split("\n")
    current_category = "Général"

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Detect category headers
        if any(
            keyword in line_lower for keyword in ["critère", "criteria", "évaluation"]
        ):
            # Try to extract criterion info
            if "prix" in line_lower or "coût" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Prix",
                        description=line.strip(),
                        ponderation=50.0,
                        ordre_affichage=len(criteria),
                    )
                )
            elif "expérience" in line_lower or "référence" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Expérience",
                        description=line.strip(),
                        ponderation=30.0,
                        ordre_affichage=len(criteria),
                    )
                )
            elif "durabilité" in line_lower or "environnement" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Durabilité",
                        description=line.strip(),
                        ponderation=10.0,
                        ordre_affichage=len(criteria),
                    )
                )

    # If no criteria found, create default ones
    if not criteria:
        criteria = [
            DaoCriterion(
                "Général", "Prix", "Prix total de l'offre", 50.0, ordre_affichage=0
            ),
            DaoCriterion(
                "Général",
                "Capacité technique",
                "Expérience et références",
                30.0,
                ordre_affichage=1,
            ),
            DaoCriterion(
                "Général",
                "Durabilité",
                "Politique environnementale et sociale",
                10.0,
                ordre_affichage=2,
            ),
        ]

    return criteria


# ------------------------------------------------------------
# TYPED EXTRACTION
# ------------------------------------------------------------
def extract_dao_criteria_typed(
    case_id: str, extracted_criteria: list[dict]
) -> list[dict]:
    """
    Enrichit les critères extraits avec catégories, drapeau éliminatoire,
    et valide les pondérations.
    """
    enriched = []

    for crit in extracted_criteria:
        description = crit.get("description", "")
        category = classify_criterion(description)
        is_eliminatory = category == "essential"

        enriched.append(
            {
                "case_id": case_id,
                "categorie": crit.get("categorie", "Général"),
                "critere_nom": crit["critere_nom"],
                "description": description,
                "criterion_category": category,
                "is_eliminatory": is_eliminatory,
                "ponderation": crit.get("ponderation", 0.0),
                "type_reponse": crit.get("type_reponse", "text"),
                "seuil_elimination": crit.get("seuil_elimination"),
                "ordre_affichage": crit.get("ordre_affichage", 0),
            }
        )

    # Validation
    is_valid, errors = validate_criterion_weightings(enriched)

    # Enregistrer la validation
    with get_connection() as conn:
        comm_weight = sum(
            c["ponderation"]
            for c in enriched
            if c["criterion_category"] == "commercial"
        )
        sust_weight = sum(
            c["ponderation"]
            for c in enriched
            if c["criterion_category"] == "sustainability"
        )
        db_execute(
            conn,
            """
            INSERT INTO criteria_weighting_validation
            (case_id, commercial_weight, sustainability_weight, is_valid, validation_errors, created_at)
            VALUES (:cid, :comm, :sust, :valid, :errors, :ts)
            """,
            {
                "cid": case_id,
                "comm": comm_weight,
                "sust": sust_weight,
                "valid": is_valid,
                "errors": "\n".join(errors) if errors else None,
                "ts": datetime.now(UTC).isoformat(),
            },
        )

    if not is_valid:
        logger.warning(
            f"[VALIDATION] Case {case_id} – Pondérations non conformes: {errors}"
        )

    return enriched


# ------------------------------------------------------------
# MAIN EXTRACTION FUNCTIONS
# ------------------------------------------------------------
def extract_dao_content(case_id: str, artifact_id: str, filepath: str):
    """
    Extraction DAO avec typage des critères (M3A).
    """
    try:
        # 1. Extraire le texte du fichier
        text_content = extract_text_any(filepath)

        # 2. Extraire les critères bruts
        raw_criteria = extract_dao_criteria_structured(text_content)

        # 3. Convertir en liste de dicts pour le typage
        raw_dicts = [asdict(c) for c in raw_criteria]

        # 4. Enrichir avec catégories
        typed_criteria = extract_dao_criteria_typed(case_id, raw_dicts)

        # 5. Insérer en base
        with get_connection() as conn:
            for crit in typed_criteria:
                db_execute(
                    conn,
                    """
                    INSERT INTO dao_criteria
                    (id, case_id, categorie, critere_nom, description,
                     criterion_category, is_eliminatory, ponderation,
                     type_reponse, seuil_elimination, ordre_affichage, created_at)
                    VALUES (:id, :cid, :cat, :nom, :desc,
                            :criterion_category, :is_eliminatory, :ponderation,
                            :type_reponse, :seuil, :ordre, :ts)
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "cid": case_id,
                        "cat": crit["categorie"],
                        "nom": crit["critere_nom"],
                        "desc": crit["description"],
                        "criterion_category": crit["criterion_category"],
                        "is_eliminatory": crit["is_eliminatory"],
                        "ponderation": crit["ponderation"],
                        "type_reponse": crit["type_reponse"],
                        "seuil": crit["seuil_elimination"],
                        "ordre": crit["ordre_affichage"],
                        "ts": datetime.now(UTC).isoformat(),
                    },
                )

        logger.info(
            f"[EXTRACTION] Case {case_id} – {len(typed_criteria)} critères typés et validés"
        )

    except Exception as e:
        logger.error(
            f"[EXTRACTION] Échec pour case {case_id}, artifact {artifact_id}: {e}"
        )
        raise


def extract_offer_content(
    case_id: str,
    artifact_id: str,
    filepath: str,
    offer_type: str,
) -> None:
    """
    Point d'entrée pipeline — appelé par routers.py via
    background_tasks.add_task().
    Signature conservée — compatibilité routers.py garantie.

    Mandat 4 : stub remplacé par appel réel.
    Lit le fichier via extract_text_any() (PDF/DOCX/texte).
    Délègue à extract_offer_content_async() via asyncio.

    Fonction de tâche de fond : ne retourne pas de valeur utile
    (retourne None) et gère les erreurs en interne (journalisation,
    éventuels fallbacks), sans propager d'exception.
    """
    logger.info(
        "[EXTRACT] Début — case=%s artifact=%s type=%s",
        case_id,
        artifact_id,
        offer_type,
    )

    # ── 1. Extraire le texte du fichier ──────────────────────
    # extract_text_any() gère PDF (pypdf), DOCX, texte brut
    try:
        text = extract_text_any(filepath)
        logger.info("[EXTRACT] Texte extrait : %d chars", len(text))
    except Exception as exc:
        logger.error("[EXTRACT] Lecture fichier KO : %s", exc)
        return make_fallback_result(
            document_id=artifact_id,
            document_role=str(offer_type),
            error_reason=f"file_read_{type(exc).__name__}",
        )

    if not text or not text.strip():
        logger.warning(
            "[EXTRACT] Texte vide après extraction — doc=%s",
            artifact_id,
        )
        return make_fallback_result(
            document_id=artifact_id,
            document_role=str(offer_type),
            error_reason="empty_text_after_extraction",
        )

    # ── 2. Mapper offer_type → document_role DMS ─────────────
    document_role = _OFFER_TYPE_TO_ROLE.get(str(offer_type).lower(), "supporting_doc")

    # ── 3. Dispatcher vers async via thread pool ─────────────
    # FastAPI background_tasks exécute les fonctions sync
    # dans un thread. asyncio.run() crée une nouvelle loop
    # dans ce thread — compatible avec background_tasks.
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                extract_offer_content_async(
                    document_id=artifact_id,
                    text=text,
                    document_role=document_role,
                ),
            )
            result = future.result(timeout=router.timeout + 15)
        logger.info(
            "[EXTRACT] Terminé — case=%s ok=%s latency=%.0fms",
            case_id,
            result.extraction_ok,
            result.latency_ms,
        )
        return result

    except concurrent.futures.TimeoutError:
        logger.error("[EXTRACT] Timeout dispatch — case=%s", case_id)
        return make_fallback_result(
            document_id=artifact_id,
            document_role=document_role,
            error_reason="dispatch_timeout",
        )
    except Exception as exc:
        logger.error(
            "[EXTRACT] Dispatch KO — %s — case=%s",
            type(exc).__name__,
            case_id,
            exc_info=True,
        )
        return make_fallback_result(
            document_id=artifact_id,
            document_role=document_role,
            error_reason=f"dispatch_{type(exc).__name__}",
        )


async def extract_offer_content_async(
    document_id: str,
    text: str,
    document_role: str = "financial_offer",
) -> TDRExtractionResult:
    """
    Extraction documentaire réelle — async.
    Appelle annotation-backend /predict.
    Fallback traçable si backend KO.
    """
    tier = router.select_tier()

    if tier == Tier.T4_OFFLINE:
        logger.warning("[EXTRACT] TIER 4 offline — doc=%s", document_id)
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason="tier4_offline_no_api_key",
            tier=Tier.T4_OFFLINE,
        )

    return await _call_annotation_backend(
        document_id=document_id,
        text=text,
        document_role=document_role,
    )


async def _call_annotation_backend(
    document_id: str,
    text: str,
    document_role: str,
) -> TDRExtractionResult:
    """Appel HTTP annotation-backend /predict."""
    t_start = time.monotonic()

    payload = {
        "tasks": [{"id": 1, "data": {"text": text}}],
        "document_id": document_id,
        "document_role": document_role,
    }

    try:
        async with httpx.AsyncClient(timeout=router.timeout) as client:
            response = await client.post(
                f"{router.backend_url}/predict",
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()

        latency_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "[EXTRACT] Backend OK — doc=%s %.0fms",
            document_id,
            latency_ms,
        )
        return _parse_backend_response(
            raw=raw,
            document_id=document_id,
            document_role=document_role,
            latency_ms=latency_ms,
        )

    except httpx.TimeoutException:
        latency_ms = (time.monotonic() - t_start) * 1000
        logger.error(
            "[EXTRACT] Timeout %.0fms — doc=%s",
            latency_ms,
            document_id,
        )
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason="backend_timeout",
        )

    except httpx.HTTPStatusError as exc:
        logger.error(
            "[EXTRACT] HTTP %s — doc=%s",
            exc.response.status_code,
            document_id,
        )
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason=f"http_{exc.response.status_code}",
        )

    except httpx.RequestError as exc:
        logger.error(
            "[EXTRACT] Connexion KO — %s — doc=%s",
            type(exc).__name__,
            document_id,
        )
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason=f"connection_{type(exc).__name__}",
        )

    except Exception as exc:
        logger.error(
            "[EXTRACT] Inattendu — %s — doc=%s",
            type(exc).__name__,
            document_id,
            exc_info=True,
        )
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason=f"unexpected_{type(exc).__name__}",
        )


def _parse_backend_response(
    raw: dict,
    document_id: str,
    document_role: str,
    latency_ms: float,
) -> TDRExtractionResult:
    """Parse réponse /predict → TDRExtractionResult."""
    try:
        results = raw.get("results", [])
        if not results:
            raise ValueError("results[] vide")

        result_list = results[0].get("result", [])

        json_block = next(
            (r for r in result_list if r.get("from_name") == "extracted_json"),
            None,
        ) or next(
            (
                r
                for r in result_list
                if isinstance(r.get("value"), dict) and "text" in r["value"]
            ),
            None,
        )

        if json_block is None:
            raise ValueError("Bloc extracted_json introuvable")

        raw_text = json_block["value"]["text"]
        if isinstance(raw_text, list):
            raw_text = raw_text[0]

        annotation = json.loads(raw_text)
        if not isinstance(annotation, dict):
            # On attend toujours un objet JSON (dict) pour construire le résultat.
            # Toute autre forme (liste, chaîne, etc.) est considérée comme une erreur de parse.
            raise TypeError("annotation must be a dict")

        return _build_result(
            annotation=annotation,
            document_id=document_id,
            document_role=document_role,
            latency_ms=latency_ms,
        )

    except (
        json.JSONDecodeError,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        logger.error(
            "[EXTRACT] Parse KO — %s — doc=%s",
            exc,
            document_id,
        )
        return make_fallback_result(
            document_id=document_id,
            document_role=document_role,
            error_reason=f"parse_{type(exc).__name__}",
        )


def _infer_tier_used(annotation: dict) -> Tier:
    """
    Déduit le tier effectivement utilisé à partir de l'annotation.

    On tente d'abord de lire une information explicite (routing / _meta),
    puis on mappe éventuellement une chaîne vers l'enum Tier. En cas
    d'absence ou d'erreur, on retombe sur Tier.T1 pour conserver le
    comportement actuel par défaut.
    """
    routing = annotation.get("couche_1_routing", {}) or {}
    meta = annotation.get("_meta", {}) or {}

    tier_value = (
        routing.get("tier_used")
        or meta.get("tier_used")
        or meta.get("llm_tier")
        or meta.get("mistral_tier")
    )

    # Si c'est déjà un enum Tier, on le renvoie tel quel.
    if isinstance(tier_value, Tier):
        return tier_value

    # Sinon, on tente un mapping à partir d'une chaîne.
    if isinstance(tier_value, str):
        normalized = tier_value.strip().upper()
        # Autoriser "1" / "2" / "3" ou "T1" / "T2" / "T3"
        if not normalized.startswith("T"):
            normalized = f"T{normalized}"
        return getattr(Tier, normalized, Tier.T1)

    # Fallback conservateur.
    return Tier.T1


def _build_result(
    annotation: dict,
    document_id: str,
    document_role: str,
    latency_ms: float,
) -> TDRExtractionResult:
    """Construit TDRExtractionResult depuis JSON DMS v3.0.1d."""
    routing = annotation.get("couche_1_routing", {})
    meta = annotation.get("_meta", {})
    financier = annotation.get("couche_4_atomic", {}).get("financier", {})
    tier_used = _infer_tier_used(annotation)
    return TDRExtractionResult(
        document_id=document_id,
        document_role=document_role,
        family_main=routing.get("procurement_family_main", "ABSENT"),
        family_sub=routing.get("procurement_family_sub", "ABSENT"),
        taxonomy_core=routing.get("taxonomy_core", "ABSENT"),
        fields=_extract_fields(annotation, tier_used=tier_used),
        line_items=_extract_line_items(financier),
        gates=annotation.get("couche_5_gates", []),
        ambiguites=annotation.get("ambiguites", []),
        tier_used=tier_used,
        latency_ms=latency_ms,
        extraction_ok=True,
        review_required=bool(meta.get("review_required", False)),
        schema_version=meta.get("schema_version", "v3.0.1d"),
        raw_annotation=annotation,
    )


def _extract_fields(annotation: dict, tier_used: Tier) -> list[ExtractionField]:
    """Extrait ExtractionField depuis couche_2_core."""
    fields: list[ExtractionField] = []
    for name, data in annotation.get("couche_2_core", {}).items():
        if not isinstance(data, dict):
            continue
        conf = data.get("confidence", 0.6)
        if conf not in {0.6, 0.8, 1.0}:
            conf = 0.6
        try:
            fields.append(
                ExtractionField(
                    field_name=name,
                    value=data.get("value"),
                    confidence=float(conf),
                    evidence=str(data.get("evidence") or "ABSENT"),
                    tier_used=tier_used,
                )
            )
        except ValueError as exc:
            logger.warning("[EXTRACT] Champ '%s' ignoré : %s", name, exc)
    return fields


def _extract_line_items(financier: dict) -> list[LineItem]:
    """Extrait LineItem depuis couche_4_atomic.financier."""
    items: list[LineItem] = []
    for i, raw in enumerate(financier.get("line_items", []), 1):
        if not isinstance(raw, dict):
            continue
        try:
            conf = raw.get("confidence", 0.8)
            if conf not in {0.6, 0.8, 1.0}:
                conf = 0.8
            items.append(
                LineItem(
                    item_line_no=int(raw.get("item_line_no", i)),
                    item_description_raw=str(raw.get("item_description_raw", "ABSENT")),
                    unit_raw=str(raw.get("unit_raw", "") or "non_precise"),
                    quantity=float(raw.get("quantity", 0) or 0),
                    unit_price=float(raw.get("unit_price", 0) or 0),
                    line_total=float(raw.get("line_total", 0) or 0),
                    line_total_check="NON_VERIFIABLE",
                    confidence=float(conf),
                    evidence=str(raw.get("evidence") or "ABSENT"),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("[EXTRACT] LineItem ignoré : %s", exc)
    return items
