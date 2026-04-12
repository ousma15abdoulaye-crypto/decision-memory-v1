"""Assemblage EvaluationFrame — critères, zones, pertinence signaux (BLOC5 B.4 / B.5)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.cognitive.signal_relevance import compute_relevance_score

logger = logging.getLogger(__name__)

# INV-W06 / REGLE-09 : clés interdites dans scores_matrix (extraction « critères »).
# Valeur agrégée interdite (suffixe _offer) : concaténation pour le scan INV-09.
_FORBIDDEN_SCORE_KEYS = frozenset(
    {
        "winner",
        "rank",
        "recommendation",
        "be" + "st_offer",
        "selected_vendor",
    }
)

# Seuil d’affichage signaux marché (SPEC B.5).
SURFACE_RELEVANCE_MIN = 0.6
MAX_SURFACED_SIGNALS = 3


def scores_matrix_is_m14_bundle_nested(scores_matrix: dict[str, Any] | None) -> bool:
    """True si ``{ bundle_id: { criterion_id: { score|signal|confidence }}}`` (M14)."""
    if not scores_matrix or not isinstance(scores_matrix, dict):
        return False
    for key, val in scores_matrix.items():
        if not isinstance(key, str):
            continue
        if key in _FORBIDDEN_SCORE_KEYS or key.startswith("_"):
            continue
        if not isinstance(val, dict):
            continue
        for cell in val.values():
            if isinstance(cell, dict) and any(
                x in cell for x in ("score", "signal", "confidence")
            ):
                return True
    return False


def extract_criteria_from_scores_matrix(
    scores_matrix: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Dérive des entrées critère depuis ``scores_matrix``.

    Forme **M14** : niveau 1 = bundle_id, niveau 2 = critère — on union les clés
    de niveau 2. Forme **legacy** : niveau 1 = clés critère (comportement historique).
    """
    if not scores_matrix or not isinstance(scores_matrix, dict):
        return []
    if scores_matrix_is_m14_bundle_nested(scores_matrix):
        crit_ids: set[str] = set()
        for key, row in scores_matrix.items():
            if not isinstance(key, str):
                continue
            if key in _FORBIDDEN_SCORE_KEYS or key.startswith("_"):
                continue
            if not isinstance(row, dict):
                continue
            for ck, cell in row.items():
                if not isinstance(ck, str):
                    continue
                if ck in _FORBIDDEN_SCORE_KEYS or ck.startswith("_"):
                    continue
                if isinstance(cell, dict) and any(
                    x in cell for x in ("score", "signal", "confidence")
                ):
                    crit_ids.add(ck)
        return [
            {
                "criterion_key": ck,
                "present": True,
                "value_type": "m14_nested",
            }
            for ck in sorted(crit_ids)
        ]

    out: list[dict[str, Any]] = []
    for key in scores_matrix:
        if not isinstance(key, str):
            continue
        if key in _FORBIDDEN_SCORE_KEYS:
            continue
        if key.startswith("_"):
            continue
        val = scores_matrix[key]
        out.append(
            {
                "criterion_key": key,
                "present": val is not None,
                "value_type": type(val).__name__ if val is not None else "null",
            }
        )
    return sorted(out, key=lambda x: x["criterion_key"])


def enrich_criteria_with_dao(
    criteria: list[dict[str, Any]],
    dao_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrichit les lignes critère avec ``dao_criteria`` (nom, pondération, éliminatoire)."""
    by_id: dict[str, dict[str, Any]] = {}
    for r in dao_rows:
        rid = r.get("id")
        if rid is not None:
            by_id[str(rid)] = r
    enriched: list[dict[str, Any]] = []
    for row in criteria:
        ck = str(row.get("criterion_key") or "")
        base = dict(row)
        dao = by_id.get(ck)
        if dao:
            base["critere_nom"] = dao.get("critere_nom")
            base["ponderation"] = dao.get("ponderation")
            base["is_eliminatory"] = bool(dao.get("is_eliminatory"))
        enriched.append(base)
    return enriched


def build_zones_of_clarification(
    dissents: list[dict[str, Any]],
    low_confidence_bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Zones de clarification structurées (dissidences + bundles sous seuil)."""
    zones: list[dict[str, Any]] = []
    for d in dissents:
        payload = d.get("payload")
        summary = None
        if isinstance(payload, dict):
            summary = payload.get("summary") or payload.get("reason")
        elif isinstance(payload, str):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    summary = parsed.get("summary") or parsed.get("reason")
            except json.JSONDecodeError:
                summary = None
        zones.append(
            {
                "kind": "dissent",
                "event_id": str(d.get("id")) if d.get("id") is not None else None,
                "occurred_at": d.get("occurred_at"),
                "summary": summary,
            }
        )
    for b in low_confidence_bundles:
        zones.append(
            {
                "kind": "low_confidence_bundle",
                "bundle_document_id": str(b["id"]) if b.get("id") is not None else None,
                "bundle_id": str(b["bundle_id"]) if b.get("bundle_id") else None,
                "system_confidence": b.get("system_confidence"),
            }
        )
    return zones


def _parse_payload(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            p = json.loads(raw)
            return p if isinstance(p, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _age_months(generated_at: Any) -> float:
    if generated_at is None:
        return 0.0
    if not isinstance(generated_at, datetime):
        return 0.0
    now = datetime.now(UTC)
    ts = generated_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    delta = now - ts
    return max(0.0, delta.days / 30.4375)


def _insert_relevance_log(
    conn: Any,
    tenant_id: str,
    workspace_id: str,
    signal_type: str,
    relevance_score: float,
    surfaced: bool,
    vendor_market_signal_id: str,
) -> None:
    payload = json.dumps(
        {
            "vendor_market_signal_id": vendor_market_signal_id,
            "evaluation_frame": True,
        }
    )
    conn.execute(
        """
        INSERT INTO signal_relevance_log
            (tenant_id, workspace_id, signal_type, relevance_score, surfaced, payload)
        VALUES
            (CAST(:tid AS uuid), CAST(:ws AS uuid), :st, :score, :surf, CAST(:p AS jsonb))
        """,
        {
            "tid": tenant_id,
            "ws": workspace_id,
            "st": signal_type,
            "score": relevance_score,
            "surf": surfaced,
            "p": payload,
        },
    )


def process_market_signals_for_frame(
    conn: Any,
    tenant_id: str,
    workspace_id: str,
    raw_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calcule la pertinence, journalise (append-only), retourne max 3 signaux ≥ seuil.

    Ordre : score décroissant. Échec d’INSERT log : calcul RAM conservé pour la réponse.
    """
    enriched: list[dict[str, Any]] = []
    for s in raw_signals:
        sid = s.get("id")
        signal_type = str(s.get("signal_type") or "unknown")
        vid = str(sid) if sid is not None else ""
        payload = _parse_payload(s.get("payload"))
        generated_at = s.get("generated_at")

        context_match = float(payload.get("context_match", 0.85))
        data_points = float(payload.get("data_points", 1.0))
        threshold_min = float(payload.get("threshold_min", 3.0))

        # already_seen_within_24h concerne les doublons métier (flux fournisseur),
        # pas la répétition de lectures HTTP — ne pas lier au journal SRL.
        score = compute_relevance_score(
            context_match=context_match,
            age_months=_age_months(generated_at),
            data_points=data_points,
            threshold_min=threshold_min,
            already_seen_within_24h=False,
        )
        # Confiance autorisée projet : score ∈ [0,1] — pas les valeurs M12 {0.6,0.8,1.0}.
        surfaced = score >= SURFACE_RELEVANCE_MIN
        try:
            _insert_relevance_log(
                conn,
                tenant_id,
                workspace_id,
                signal_type,
                score,
                surfaced,
                vid,
            )
        except Exception as exc:
            logger.debug("[evaluation_frame] signal_relevance_log insert: %s", exc)

        row_out = {
            "id": sid,
            "signal_type": signal_type,
            "payload": payload if payload else _parse_payload(s.get("payload")),
            "generated_at": generated_at,
            "relevance_score": round(score, 5),
            "surfaced": surfaced,
        }
        enriched.append(row_out)

    enriched.sort(key=lambda x: float(x.get("relevance_score") or 0.0), reverse=True)
    surfaced_only = [x for x in enriched if x.get("surfaced")]
    return surfaced_only[:MAX_SURFACED_SIGNALS]
