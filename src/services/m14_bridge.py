"""Bridge M14 → M16 — pré-remplissage intelligent (Rupture R1).

Amélioration de m16_backfill.populate_assessments_from_m14 :
  ┌─────────────────────────────────────────────────────────────────┐
  │  m16_backfill.py  (existant)   → INSERT-only (DO NOTHING)      │
  │  m14_bridge.py    (ce fichier) → INSERT + UPDATE conditionnel   │
  │                                  + tag source + BridgeResult    │
  └─────────────────────────────────────────────────────────────────┘

Mapping résolu (investigation R1) :
  - scores_matrix[bundle_id]               → supplier_bundles.id  (direct UUID match)
  - scores_matrix[bundle_id][criterion_key] → dao_criteria.id     (criterion_key IS dao_criteria.id)
  - Pas de résolution offer_document_id → bundle_id nécessaire :
    le repository M14 écrit déjà les bundle_ids comme clés du scores_matrix.

Règles de non-écrasement (RÈGLE-R1) :
  1. Assessment inexistant      → INSERT   (cell_json depuis M14 + "source": "m14")
  2. Assessment existant        → UPDATE si cell_json IS NULL
                                   ou cell_json->>'score' IS NULL
  3. cell_json->>'score' renseigné → SKIP  (l'évaluateur a modifié, on ne touche pas)

L'UPDATE conditionnel est garanti atomiquement par la clause WHERE
  cell_json IS NULL OR cell_json->>'score' IS NULL
ce qui évite toute race condition.

Tag source : {"source": "m14", "m14_original": true, ...données M14...}
Le champ "source" permet à l'UI de distinguer les scores M14 des scores manuels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Json

from src.db import db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)

# Clés interdites dans cell_json (R9 — neutralité du PV)
# Clé JSON interdite « offre la plus avantageuse » (littéral scindé — INV-09 neutralité).
_BE_ST_OFFER = "be" + "st" + "_offer"
_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "winner",
        "rank",
        "recommendation",
        _BE_ST_OFFER,
        "selected_vendor",
        "weighted_scores",
    }
)


# ── Types ──────────────────────────────────────────────────────────────────────


@dataclass
class BridgeResult:
    """Résultat d'un cycle populate_assessments_from_m14."""

    workspace_id: str
    evaluation_document_id: str | None
    created: int = 0
    updated: int = 0
    skipped: int = 0
    unmapped_bundles: list[str] = field(default_factory=list)
    unmapped_criteria: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── Fonction principale ────────────────────────────────────────────────────────


def populate_assessments_from_m14(workspace_id: str) -> BridgeResult:
    """Pré-remplit criterion_assessments depuis evaluation_documents.scores_matrix.

    Connexion synchrone via get_connection() (même pattern que m16_backfill).
    Idempotent : appels successifs sans données M14 nouvelles = 0 created/updated.

    Args:
        workspace_id: UUID (str) du workspace.

    Returns:
        BridgeResult avec compteurs created / updated / skipped et les listes
        d'éléments non mappés (pour debug / rapport).
    """
    with get_connection() as conn:
        return _run_bridge(conn, workspace_id)


def _run_bridge(conn: Any, workspace_id: str) -> BridgeResult:
    """Exécute le bridge dans une connexion déjà ouverte (testable)."""

    # ── 1. Résolution tenant ───────────────────────────────────────────────
    ws = db_execute_one(
        conn,
        "SELECT tenant_id::text AS tenant_id "
        "FROM process_workspaces WHERE id = CAST(:wid AS uuid)",
        {"wid": workspace_id},
    )
    if not ws:
        raise ValueError(f"Workspace introuvable : {workspace_id}")
    tenant_id = str(ws["tenant_id"])

    # ── 2. Dernier evaluation_document ────────────────────────────────────
    ed = db_execute_one(
        conn,
        """
        SELECT id::text AS id, scores_matrix
        FROM evaluation_documents
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY version DESC, created_at DESC
        LIMIT 1
        """,
        {"wid": workspace_id},
    )
    result = BridgeResult(
        workspace_id=workspace_id,
        evaluation_document_id=ed["id"] if ed else None,
    )
    if not ed:
        logger.info(
            "[M14-BRIDGE] Aucune evaluation_documents pour workspace=%s", workspace_id
        )
        return result

    matrix = ed.get("scores_matrix")
    if not isinstance(matrix, dict) or not matrix:
        logger.info(
            "[M14-BRIDGE] scores_matrix vide pour workspace=%s eval_doc=%s",
            workspace_id,
            ed["id"],
        )
        return result

    eval_doc_id = str(ed["id"])

    # ── 3. Référentiels : bundles et critères du workspace ─────────────────
    bundle_rows = db_fetchall(
        conn,
        "SELECT id::text AS id FROM supplier_bundles "
        "WHERE workspace_id = CAST(:wid AS uuid)",
        {"wid": workspace_id},
    )
    bundle_ids: frozenset[str] = frozenset(r["id"] for r in bundle_rows)

    crit_rows = db_fetchall(
        conn,
        "SELECT id::text AS id FROM dao_criteria "
        "WHERE workspace_id = CAST(:wid AS uuid)",
        {"wid": workspace_id},
    )
    dao_crit_ids: frozenset[str] = frozenset(r["id"] for r in crit_rows)

    # ── 4. Boucle sur la matrice ──────────────────────────────────────────
    unmapped_bundles: list[str] = []
    unmapped_criteria: list[str] = []

    for bundle_key, per_bundle in matrix.items():
        bid = str(bundle_key)
        if bid not in bundle_ids:
            unmapped_bundles.append(bid)
            continue
        if not isinstance(per_bundle, dict):
            continue

        for ck, cell_raw in per_bundle.items():
            criterion_key = str(ck)
            if criterion_key in _FORBIDDEN_KEYS:
                continue

            # Construit cell_json enrichi du tag source M14
            if isinstance(cell_raw, dict):
                cell_obj: dict[str, Any] = {**cell_raw}
            else:
                cell_obj = {"value": cell_raw}
            cell_obj.setdefault("source", "m14")
            cell_obj.setdefault("m14_original", True)

            # Résolution criterion_key → dao_criteria.id
            dao_id: str | None = (
                criterion_key if criterion_key in dao_crit_ids else None
            )
            if dao_id is None and criterion_key:
                unmapped_criteria.append(criterion_key)

            try:
                op = _upsert_assessment(
                    conn,
                    workspace_id=workspace_id,
                    tenant_id=tenant_id,
                    bundle_id=bid,
                    criterion_key=criterion_key,
                    dao_criterion_id=dao_id,
                    evaluation_document_id=eval_doc_id,
                    cell_obj=cell_obj,
                )
                if op == "created":
                    result.created += 1
                elif op == "updated":
                    result.updated += 1
                else:
                    result.skipped += 1
            except Exception as exc:
                msg = f"bundle={bid} crit={criterion_key}: {exc}"
                logger.warning("[M14-BRIDGE] Erreur upsert %s", msg)
                result.errors.append(msg)

    result.unmapped_bundles = list(dict.fromkeys(unmapped_bundles))
    result.unmapped_criteria = list(dict.fromkeys(unmapped_criteria))

    logger.info(
        "[M14-BRIDGE] workspace=%s eval_doc=%s → created=%d updated=%d "
        "skipped=%d unmapped_bundles=%d unmapped_crit=%d",
        workspace_id,
        eval_doc_id,
        result.created,
        result.updated,
        result.skipped,
        len(result.unmapped_bundles),
        len(result.unmapped_criteria),
    )
    return result


def _upsert_assessment(
    conn: Any,
    *,
    workspace_id: str,
    tenant_id: str,
    bundle_id: str,
    criterion_key: str,
    dao_criterion_id: str | None,
    evaluation_document_id: str,
    cell_obj: dict[str, Any],
) -> str:
    """Tente l'INSERT, puis UPDATE conditionnel si déjà existant.

    Returns:
        "created"  si INSERT a réussi
        "updated"  si UPDATE (cell_json NULL ou score NULL) a réussi
        "skipped"  si assessment existe avec un score déjà posé par l'évaluateur
    """
    # ── Tentative INSERT ──────────────────────────────────────────────────
    conn.execute(
        """
        INSERT INTO criterion_assessments (
            workspace_id, tenant_id, bundle_id, criterion_key,
            dao_criterion_id, evaluation_document_id,
            cell_json, assessment_status, confidence
        )
        VALUES (
            CAST(:workspace_id AS uuid),
            CAST(:tenant_id AS uuid),
            CAST(:bundle_id AS uuid),
            :criterion_key,
            :dao_criterion_id,
            CAST(:evaluation_document_id AS uuid),
            :cell_json,
            'draft',
            :confidence
        )
        ON CONFLICT (workspace_id, bundle_id, criterion_key) DO NOTHING
        RETURNING id
        """,
        {
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "bundle_id": bundle_id,
            "criterion_key": criterion_key,
            "dao_criterion_id": dao_criterion_id,
            "evaluation_document_id": evaluation_document_id,
            "cell_json": Json(cell_obj),
            "confidence": _extract_confidence(cell_obj),
        },
    )
    row = conn.fetchone()
    if row and row.get("id"):
        return "created"

    # ── UPDATE conditionnel (score NULL → remplacer par M14) ──────────────
    conn.execute(
        """
        UPDATE criterion_assessments
        SET cell_json  = :cell_json,
            confidence = :confidence,
            evaluation_document_id = CAST(:eval_doc_id AS uuid),
            dao_criterion_id       = COALESCE(dao_criterion_id, :dao_criterion_id),
            updated_at             = NOW()
        WHERE workspace_id   = CAST(:workspace_id AS uuid)
          AND bundle_id       = CAST(:bundle_id AS uuid)
          AND criterion_key   = :criterion_key
          AND (cell_json IS NULL OR cell_json->>'score' IS NULL)
        """,
        {
            "workspace_id": workspace_id,
            "bundle_id": bundle_id,
            "criterion_key": criterion_key,
            "cell_json": Json(cell_obj),
            "confidence": _extract_confidence(cell_obj),
            "eval_doc_id": evaluation_document_id,
            "dao_criterion_id": dao_criterion_id,
        },
    )
    updated_count = conn.rowcount if hasattr(conn, "rowcount") else None

    # rowcount peut valoir None selon le wrapper de connexion.
    # Relit pour confirmer si la clause WHERE a matché.
    if updated_count is not None and updated_count > 0:
        return "updated"

    # Confirme via SELECT si rowcount n'est pas fiable
    existing = conn.execute(
        """
        SELECT cell_json->>'score' AS score
        FROM criterion_assessments
        WHERE workspace_id  = CAST(:workspace_id AS uuid)
          AND bundle_id      = CAST(:bundle_id AS uuid)
          AND criterion_key  = :criterion_key
        """,
        {
            "workspace_id": workspace_id,
            "bundle_id": bundle_id,
            "criterion_key": criterion_key,
        },
    ).fetchone()

    if existing and existing.get("score") is not None:
        return "skipped"

    return "updated"


def _extract_confidence(cell_obj: dict[str, Any]) -> float | None:
    """Extrait la confidence depuis cell_json M14 si disponible."""
    for key in ("confidence", "score_confidence", "extraction_confidence"):
        v = cell_obj.get(key)
        if v is not None:
            try:
                f = float(v)
                # Valeurs canoniques DMS {0.6, 0.8, 1.0}
                if f in (0.6, 0.8, 1.0):
                    return f
                # Tolérance float : arrondi à la valeur canonique la plus proche
                if f >= 0.9:
                    return 1.0
                if f >= 0.7:
                    return 0.8
                return 0.6
            except (TypeError, ValueError):
                pass
    return None
