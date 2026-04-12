"""Persistance JSONB — table evaluation_documents (migration 056+).

ADR-M14-001. Post-migration 074 : ``case_id`` supprimé — écriture via ``workspace_id``
résolu depuis ``process_workspaces.legacy_case_id`` ou ``process_workspaces.id``.
RLS tenant_scoped via cases (chemins legacy) / workspace.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import Any

import psycopg.errors
from psycopg.types.json import Json

from src.db.core import db_fetchall, get_connection

logger = logging.getLogger(__name__)

_MAX_INSERT_RETRIES = 5


def _is_rls_denied(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "row-level security" in msg or "violates row-level security" in msg


def _build_assessment_matrix_from_report(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Transforme EvaluationReport en matrice bundle×critère pour M16 bridge.

    Format sortie: {bundle_id: {criterion_key: {score, confidence, justification}}}

    Cette matrice est exploitable par populate_assessments_from_m14() qui attend
    une structure {bundle_id: {criterion_key: cell_data}}.
    """
    matrix: dict[str, dict[str, Any]] = {}

    offer_evals = payload.get("offer_evaluations") or []
    for offer in offer_evals:
        if not isinstance(offer, dict):
            continue

        # offer_document_id = bundle_id dans le contexte pipeline V5
        bundle_id = str(offer.get("offer_document_id", ""))
        if not bundle_id:
            continue

        bundle_matrix: dict[str, Any] = {}

        # Extraction des scores techniques
        tech_score = offer.get("technical_score")
        if isinstance(tech_score, dict):
            criteria_scores = tech_score.get("criteria_scores") or []
            for crit in criteria_scores:
                if not isinstance(crit, dict):
                    continue

                crit_name = str(crit.get("criteria_name", "unknown"))
                awarded = crit.get("awarded_score")
                max_score = crit.get("max_score")
                justif = crit.get("justification", "")
                conf = crit.get("confidence", 0.6)

                # Construction cell_json compatible M16
                bundle_matrix[crit_name] = {
                    "score": awarded,
                    "max_score": max_score,
                    "justification": justif,
                    "confidence": conf,
                    "source": "m14",
                }

        # Extraction éligibilité (peut devenir critère éliminatoire)
        eligibility = offer.get("eligibility_results") or []
        for check in eligibility:
            if not isinstance(check, dict):
                continue
            if not check.get("is_eliminatory"):
                continue

            check_id = str(check.get("check_id", ""))
            check_name = str(check.get("check_name", "eligibility"))
            result = check.get("result", "INDETERMINATE")
            conf = check.get("confidence", 0.6)

            # Score binaire : PASS=1, FAIL=0, autre=0.5
            if result == "PASS":
                score_val = 1.0
            elif result == "FAIL":
                score_val = 0.0
            else:
                score_val = 0.5

            key = check_id if check_id else check_name
            bundle_matrix[key] = {
                "score": score_val,
                "max_score": 1.0,
                "justification": f"Eligibility: {result}",
                "confidence": conf,
                "source": "m14",
                "check_type": "eligibility",
            }

        # Extraction analyse prix (optionnel)
        price_analysis = offer.get("price_analysis")
        if isinstance(price_analysis, dict):
            total_price = price_analysis.get("total_price_declared")
            if total_price is not None:
                bundle_matrix["price_total"] = {
                    "score": total_price,
                    "max_score": None,
                    "justification": f"Currency: {price_analysis.get('currency', 'unknown')}",
                    "confidence": price_analysis.get("confidence", 0.6),
                    "source": "m14",
                    "check_type": "price",
                }

        if bundle_matrix:
            matrix[bundle_id] = bundle_matrix

    logger.info(
        "[M14-REPO] assessment_matrix built — %d bundles, %d total criteria",
        len(matrix),
        sum(len(v) for v in matrix.values()),
    )

    return matrix


def _apply_scores_matrix_dao_fallback(
    workspace_id: str,
    matrix: dict[str, dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Complète ``scores_matrix`` quand M14 n'a émis aucune cellule critère.

    Sans grille bundle×critère, ``populate_assessments_from_m14`` ne peut pas
    INSERT (cas fréquent : pipeline V5 + M12 bootstrap sans ``scoring_structure``).

    On ajoute uniquement les couples manquants : clés = ``dao_criteria.id`` (texte
    UUID), comme attendu par ``m14_bridge.populate_assessments_from_m14`` /
    ``resolve_criterion_id_sync`` — pas les libellés ``critere_nom``.
    """
    offer_evals = payload.get("offer_evaluations") or []
    bundle_ids: list[str] = []
    for offer in offer_evals:
        if not isinstance(offer, dict):
            continue
        bid = str(offer.get("offer_document_id") or "").strip()
        if bid:
            bundle_ids.append(bid)
    bundle_ids = list(dict.fromkeys(bundle_ids))
    if not bundle_ids:
        return matrix

    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id, critere_nom
            FROM dao_criteria
            WHERE workspace_id = CAST(:wid AS uuid)
            ORDER BY ordre_affichage NULLS LAST, critere_nom NULLS LAST, id
            """,
            {"wid": workspace_id},
        )
    criterion_ids = [str(r["id"]).strip() for r in rows if r.get("id")]
    if not criterion_ids:
        return matrix

    out: dict[str, dict[str, Any]] = {k: dict(v) for k, v in matrix.items()}
    id_to_label = {
        str(r["id"]).strip(): str(r.get("critere_nom") or "").strip()
        for r in rows
        if r.get("id")
    }

    for bid in bundle_ids:
        existing = out.get(bid)
        if not isinstance(existing, dict):
            existing = {}
        merged = dict(existing)
        for dao_id in criterion_ids:
            if dao_id not in merged:
                label = id_to_label.get(dao_id, "")
                justification = (
                    "M14 shell — scoring_structure absent ou vide ; "
                    "cellule bootstrap pour le bridge DAO (pipeline V5)."
                )
                if label:
                    justification = f"{justification} (critère: {label})"
                merged[dao_id] = {
                    "score": 0.6,
                    "max_score": 1.0,
                    "justification": justification,
                    "confidence": 0.6,
                    "source": "m14",
                }
        if merged:
            out[bid] = merged

    return out


class M14EvaluationRepository:
    """CRUD sur evaluation_documents (migration 056)."""

    def _resolve_committee_id(self, case_id: str) -> str | None:
        """Lookup le premier committee_id rattaché au case. None si absent."""
        try:
            with get_connection() as conn:
                conn.execute(
                    "SELECT committee_id::text AS cid FROM public.committees "
                    "WHERE case_id = :case_id LIMIT 1",
                    {"case_id": case_id},
                )
                row = conn.fetchone()
                return str(row["cid"]) if row else None
        except Exception as exc:
            logger.warning("committee_id lookup failed for case %s: %s", case_id, exc)
            return None

    def _resolve_workspace_id_for_case(self, case_id: str) -> str | None:
        """Résout process_workspaces.id depuis legacy_case_id ou UUID workspace."""
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS wid FROM public.process_workspaces
                    WHERE legacy_case_id = :cid
                    LIMIT 1
                    """,
                    {"cid": case_id},
                )
                row = conn.fetchone()
                if row and row.get("wid"):
                    return str(row["wid"])
            try:
                uuid_mod.UUID(case_id)
            except ValueError:
                return None
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS wid FROM public.process_workspaces
                    WHERE id = CAST(:cid AS uuid)
                    LIMIT 1
                    """,
                    {"cid": case_id},
                )
                row = conn.fetchone()
                return str(row["wid"]) if row and row.get("wid") else None
        except Exception as exc:
            logger.warning(
                "workspace_id resolve failed for case_id=%s: %s", case_id, exc
            )
            return None

    def save_evaluation(
        self,
        *,
        case_id: str,
        payload: dict[str, Any],
        committee_id: str | None = None,
        version: int | None = None,
    ) -> str | None:
        """Insère un nouveau draft. Retourne l'id UUID, ou None si erreur.

        ``committee_id`` est NOT NULL + FK en DB. Si non fourni, le repository
        résout le premier comité rattaché au case (table ``committees``).
        ``workspace_id`` est résolu via ``process_workspaces`` (legacy_case_id).
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            logger.warning(
                "evaluation_documents save skipped: no workspace for case_id=%s",
                case_id,
            )
            return None

        cid = committee_id or self._resolve_committee_id(case_id)
        if cid is None:
            logger.warning(
                "evaluation_documents save skipped: no committee found for case %s",
                case_id,
            )
            return None

        # FIX M16 BRIDGE: Transformer payload en assessment_matrix exploitable
        assessment_matrix = _build_assessment_matrix_from_report(payload)
        assessment_matrix = _apply_scores_matrix_dao_fallback(
            workspace_id, assessment_matrix, payload
        )

        for attempt in range(_MAX_INSERT_RETRIES):
            try:
                with get_connection() as conn:
                    conn.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 AS v "
                        "FROM public.evaluation_documents "
                        "WHERE workspace_id = CAST(:wid AS uuid)",
                        {"wid": workspace_id},
                    )
                    row = conn.fetchone()
                    ver = int(row["v"]) if row and row.get("v") is not None else 1
                    if version is not None:
                        ver = version
                    conn.execute(
                        """
                        INSERT INTO public.evaluation_documents
                        (workspace_id, committee_id, version, scores_matrix, status)
                        VALUES (
                            CAST(:workspace_id AS uuid),
                            CAST(:committee_id AS uuid),
                            :ver,
                            :matrix,
                            'draft'
                        )
                        RETURNING id::text AS id
                        """,
                        {
                            "workspace_id": workspace_id,
                            "committee_id": cid,
                            "ver": ver,
                            "matrix": Json(assessment_matrix),
                        },
                    )
                    out = conn.fetchone()
                    return str(out["id"]) if out else None
            except psycopg.errors.UniqueViolation:
                if version is not None or attempt + 1 >= _MAX_INSERT_RETRIES:
                    logger.warning(
                        "evaluation_documents unique violation (version=%s, attempt=%s/%s)",
                        version,
                        attempt + 1,
                        _MAX_INSERT_RETRIES,
                    )
                    return None
                continue
            except Exception as exc:
                if _is_rls_denied(exc):
                    logger.error(
                        "evaluation_documents RLS denied (check app.tenant_id / case): %s",
                        exc,
                    )
                else:
                    logger.warning("evaluation_documents save failed: %s", exc)
                return None
        return None

    def get_latest(self, *, case_id: str) -> dict[str, Any] | None:
        """Récupère le dernier résultat d'évaluation pour un case (clé API).

        ``case_id`` identifie le dossier logique ; la ligne DB est résolue via
        ``workspace_id``.
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            return None
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS id, version,
                           scores_matrix, justifications, status,
                           created_at
                    FROM public.evaluation_documents
                    WHERE workspace_id = CAST(:wid AS uuid)
                    ORDER BY version DESC NULLS LAST, created_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    {"wid": workspace_id},
                )
                row = conn.fetchone()
                if row is None:
                    return None
                result = dict(row)
                result["case_id"] = case_id
                ca = result.get("created_at")
                if ca is not None and not isinstance(ca, str):
                    result["created_at"] = (
                        ca.isoformat() if hasattr(ca, "isoformat") else str(ca)
                    )
                if result.get("scores_matrix") is None:
                    result["scores_matrix"] = {}
                if result.get("justifications") is None:
                    result["justifications"] = {}
                return result
        except Exception as exc:
            if _is_rls_denied(exc):
                logger.error("evaluation_documents get_latest RLS denied: %s", exc)
            else:
                logger.warning("evaluation_documents get_latest failed: %s", exc)
            return None

    def save_m14_audit(self, *, case_id: str, report: Any) -> None:
        """Écrit score_history et elimination_log (migration 059+). Append-only.

        Colonnes post-074 : ``workspace_id`` (plus de ``case_id`` sur ces tables).
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            logger.warning(
                "save_m14_audit skipped: no workspace for case_id=%s", case_id
            )
            return

        data = (
            report.model_dump(mode="json") if hasattr(report, "model_dump") else report
        )
        offers = data.get("offer_evaluations") or []
        try:
            with get_connection() as conn:
                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    oid = str(offer.get("offer_document_id") or "")
                    if not oid:
                        continue
                    ts = offer.get("technical_score") or {}
                    for c in ts.get("criteria_scores") or []:
                        if not isinstance(c, dict):
                            continue
                        ck = str(c.get("criteria_name") or "unknown")
                        conn.execute(
                            """
                            INSERT INTO public.score_history (
                                workspace_id, offer_document_id, criterion_key,
                                score_value, max_score, confidence, evidence, scored_by
                            ) VALUES (
                                CAST(:wid AS uuid), :oid, :ck,
                                :sv, :mx, :conf, :ev, 'system:m14'
                            )
                            """,
                            {
                                "wid": workspace_id,
                                "oid": oid,
                                "ck": ck,
                                "sv": c.get("awarded_score"),
                                "mx": c.get("max_score"),
                                "conf": float(c.get("confidence") or 0.6),
                                "ev": (c.get("justification") or "")[:8000],
                            },
                        )
                    for ev in offer.get("eligibility_results") or []:
                        if not isinstance(ev, dict):
                            continue
                        if not ev.get("is_eliminatory"):
                            continue
                        if ev.get("result") != "FAIL":
                            continue
                        reason = (
                            "; ".join(ev.get("evidence") or []) or "eliminatory_fail"
                        )
                        conn.execute(
                            """
                            INSERT INTO public.elimination_log (
                                workspace_id, offer_document_id,
                                check_id, check_name, reason
                            ) VALUES (
                                CAST(:wid AS uuid), :oid, :cid, :cname, :reason
                            )
                            """,
                            {
                                "wid": workspace_id,
                                "oid": oid,
                                "cid": str(ev.get("check_id") or ""),
                                "cname": str(ev.get("check_name") or ""),
                                "reason": reason[:8000],
                            },
                        )
        except Exception as exc:
            err = str(exc).lower()
            if "undefinedtable" in err or "does not exist" in err:
                logger.warning(
                    "save_m14_audit skipped (tables missing — run migration 059): %s",
                    exc,
                )
            elif _is_rls_denied(exc):
                logger.error("save_m14_audit RLS denied: %s", exc)
            else:
                logger.warning("save_m14_audit failed: %s", exc)
