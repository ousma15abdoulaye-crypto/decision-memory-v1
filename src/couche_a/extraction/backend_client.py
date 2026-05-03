"""
Annotation backend HTTP client — calls /predict and parses responses.
"""

import json
import logging
import os
import time

import httpx

from src.couche_a.extraction_models import (
    ExtractionField,
    LineItem,
    TDRExtractionResult,
    Tier,
    make_fallback_result,
)

logger = logging.getLogger(__name__)


def _get_router():
    """Import différé : évite de charger llm_router tant qu'aucun appel async / HTTP n'est fait."""
    from src.couche_a.llm_router import router

    return router


async def call_annotation_backend(
    document_id: str,
    text: str,
    document_role: str,
) -> TDRExtractionResult:
    """Appel HTTP annotation-backend /predict."""
    t_start = time.monotonic()

    payload = {
        "tasks": [
            {
                "id": 1,
                "data": {
                    "text": text,
                    "document_role": document_role,
                },
            }
        ],
        "document_id": document_id,
        "document_role": document_role,
    }

    try:
        r = _get_router()
        # TLS proxy SCI: HTTPX_VERIFY_SSL=0 désactive verify (dev/local uniquement)
        verify_ssl = os.getenv("HTTPX_VERIFY_SSL", "1") != "0"
        async with httpx.AsyncClient(timeout=r.timeout, verify=verify_ssl) as client:
            response = await client.post(
                f"{r.backend_url}/predict",
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
    """Déduit le tier effectivement utilisé à partir de l'annotation."""
    routing = annotation.get("couche_1_routing", {}) or {}
    meta = annotation.get("_meta", {}) or {}

    tier_value = (
        routing.get("tier_used")
        or meta.get("tier_used")
        or meta.get("llm_tier")
        or meta.get("mistral_tier")
    )

    if isinstance(tier_value, Tier):
        return tier_value

    if isinstance(tier_value, str):
        normalized = tier_value.strip().upper()
        if not normalized.startswith("T"):
            normalized = f"T{normalized}"
        return getattr(Tier, normalized, Tier.T1)

    return Tier.T1


def _ambiguity_codes(ambiguites: list) -> set[str]:
    """Normalise ambiguites (str ou dict avec clé code) en ensemble de codes."""
    codes: set[str] = set()
    for item in ambiguites or []:
        if isinstance(item, str):
            codes.add(item)
        elif isinstance(item, dict):
            c = item.get("code")
            if c is not None:
                codes.add(str(c))
    return codes


def _build_result(
    annotation: dict,
    document_id: str,
    document_role: str,
    latency_ms: float,
) -> TDRExtractionResult:
    """Construit TDRExtractionResult depuis JSON DMS v3.0.1d."""
    routing = annotation.get("couche_1_routing", {}) or {}
    meta = annotation.get("_meta", {}) or {}
    couche_4 = annotation.get("couche_4_atomic", {}) or {}
    financier = couche_4.get("financier", {}) or {}
    tier_used = _infer_tier_used(annotation)
    fields = extract_fields(annotation, tier_used=tier_used)
    line_items = extract_line_items(financier)
    ambiguites = list(annotation.get("ambiguites", []) or [])

    routing_vals = [
        routing.get("procurement_family_main", "ABSENT"),
        routing.get("procurement_family_sub", "ABSENT"),
        routing.get("taxonomy_core", "ABSENT"),
    ]
    routing_absent_count = sum(1 for v in routing_vals if v in (None, "", "ABSENT"))
    schema_ok = routing_absent_count < 3

    identifiants = annotation.get("identifiants", {}) or {}
    supplier_absent = not identifiants.get(
        "supplier_name_raw"
    ) and not identifiants.get("supplier_name_normalized")

    financial_layout = couche_4.get("financial_layout_mode", "") or ""
    items_empty = len(line_items) == 0 and financial_layout == "structured_table"

    critical_ambig_codes = {
        "AMBIG-3_critical",
        "AMBIG-4_unresolvable",
        "AMBIG-7_schema_failure",
    }
    has_critical_ambig = bool(critical_ambig_codes & _ambiguity_codes(ambiguites))

    critical_violation = supplier_absent or items_empty or has_critical_ambig
    extraction_ok = schema_ok and not critical_violation
    review_required_flag = bool(meta.get("review_required", False)) or not extraction_ok

    return TDRExtractionResult(
        document_id=document_id,
        document_role=document_role,
        family_main=routing.get("procurement_family_main", "ABSENT"),
        family_sub=routing.get("procurement_family_sub", "ABSENT"),
        taxonomy_core=routing.get("taxonomy_core", "ABSENT"),
        fields=fields,
        line_items=line_items,
        gates=annotation.get("couche_5_gates", []),
        ambiguites=ambiguites,
        tier_used=tier_used,
        latency_ms=latency_ms,
        extraction_ok=extraction_ok,
        review_required=review_required_flag,
        schema_version=meta.get("schema_version", "v3.0.1d"),
        raw_annotation=annotation,
    )


def extract_fields(annotation: dict, tier_used: Tier) -> list[ExtractionField]:
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


def extract_line_items(financier: dict) -> list[LineItem]:
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
