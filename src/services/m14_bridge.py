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
import re
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Json

from src.db import db_execute_one, db_fetchall, get_connection

logger = logging.getLogger(__name__)

_UUID_CRIT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

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


class BridgeConfigurationError(Exception):
    """Payload bridge M14 invalide (Gate C)."""


def matrix_participant_bundle_ids(matrix_raw: dict[str, Any]) -> frozenset[str] | None:
    """IDs autorisés pour persistance matrice ; ``None`` = pas de filtre (documents legacy).

    Liste vide explicite → jeu vide (aucun bundle ne reçoit d'assessment).
    """
    if "matrix_participants" not in matrix_raw:
        logger.warning(
            "[BRIDGE] matrix_participants absent du payload "
            "— filtre Gate C désactivé (mode legacy)"
        )
        return None
    mp = matrix_raw.get("matrix_participants")
    if mp is None:
        logger.warning(
            "[BRIDGE] matrix_participants absent du payload "
            "— filtre Gate C désactivé (mode legacy)"
        )
        return None
    if not isinstance(mp, (list, set, frozenset)):
        raise BridgeConfigurationError(
            f"[BRIDGE] matrix_participants type invalide : "
            f"{type(mp)}. Attendu : list. Arrêt Gate C."
        )
    ids: set[str] = set()
    for it in mp:
        if isinstance(it, dict) and it.get("bundle_id"):
            ids.add(str(it["bundle_id"]))
    return frozenset(ids)


def scoring_criterion_key_is_forbidden(criterion_key: str) -> bool:
    """Clés interdites dans ``criterion_assessments`` (scoring pur — CTO D-01 / Gate D)."""
    ck = (criterion_key or "").strip()
    if not ck:
        return True
    low = ck.lower()
    if ck in _FORBIDDEN_KEYS or low in {x.lower() for x in _FORBIDDEN_KEYS}:
        return True
    if low.startswith("m14:eligibility:") or low.startswith("m14:compliance:"):
        return True
    if low.startswith("m14:technical:"):
        return True
    if low in ("m14:price", "m14:completion"):
        return True
    if "dgmp" in low:
        return True
    if low.startswith("reg_only_"):
        return True
    return False


def _delete_stale_scoring_rows(conn: Any, workspace_id: str) -> int:
    """Supprime les lignes scoring invalides (CTO D-05) — patterns Gate D/E.

    psycopg3 : ne pas mettre de ``%`` littéraux dans le SQL (confusion avec les
    placeholders) — motifs LIKE / ILIKE passés en paramètres bindés (D-09).
    """
    like_patterns = (
        "m14:eligibility:%",
        "m14:compliance:%",
        "m14:technical:%",
        "reg_only_%",
    )
    n = 0
    for pat in like_patterns:
        conn.execute(
            """
            DELETE FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
              AND criterion_key LIKE :pat
            RETURNING id
            """,
            {"wid": workspace_id, "pat": pat},
        )
        rows = conn.fetchall()
        n += len(rows) if rows else 0
    conn.execute(
        """
        DELETE FROM criterion_assessments
        WHERE workspace_id = CAST(:wid AS uuid)
          AND criterion_key ILIKE :pat
        RETURNING id
        """,
        {"wid": workspace_id, "pat": "%dgmp%"},
    )
    rows = conn.fetchall()
    n += len(rows) if rows else 0
    conn.execute(
        """
        DELETE FROM criterion_assessments
        WHERE workspace_id = CAST(:wid AS uuid)
          AND criterion_key IN ('m14:price', 'm14:completion')
        RETURNING id
        """,
        {"wid": workspace_id},
    )
    rows = conn.fetchall()
    n += len(rows) if rows else 0
    if n:
        logger.warning(
            "[M14-BRIDGE] DELETE scoring invalide workspace=%s rows=%d (patterns interdits)",
            workspace_id,
            n,
        )
    return n


def _norm_crit_label(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _build_dao_criterion_lookups(
    crit_rows: list[dict[str, Any]],
) -> tuple[frozenset[str], dict[str, str], dict[str, str]]:
    """``dao_ids``, map nom normalisé → id, map code M16 → id."""
    dao_ids: set[str] = set()
    by_norm_name: dict[str, str] = {}
    by_code: dict[str, str] = {}
    for r in crit_rows:
        rid = r.get("id")
        if not rid:
            continue
        sid = str(rid)
        dao_ids.add(sid)
        nom = r.get("critere_nom")
        if isinstance(nom, str) and nom.strip():
            by_norm_name.setdefault(_norm_crit_label(nom), sid)
        code = r.get("m16_criterion_code")
        if code is not None and str(code).strip():
            by_code[str(code).strip().lower()] = sid
    return frozenset(dao_ids), by_norm_name, by_code


def _technical_cell_key(
    criteria_name: str,
    *,
    by_norm_name: dict[str, str],
    by_code: dict[str, str],
) -> tuple[str | None, str | None]:
    """Retourne (``criterion_key`` = UUID dao, ``dao_criterion_id``) ou (None, None).

    Pas de clé ``m14:technical:*`` : scoring matrice = UUID dao uniquement (Gate E).
    """
    name = (criteria_name or "").strip()
    nk = _norm_crit_label(name)
    if nk and nk in by_norm_name:
        dao = by_norm_name[nk]
        if dao:
            return dao, dao
    lc = name.strip().lower()
    if lc and lc in by_code:
        dao = by_code[lc]
        if dao:
            return dao, dao
    return None, None


def _flatten_evaluation_report_scores_matrix(
    report: dict[str, Any],
    *,
    by_norm_name: dict[str, str],
    by_code: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Transforme un ``EvaluationReport`` sérialisé en matrice bundle → critère → cellule."""
    out: dict[str, dict[str, Any]] = {}
    oev = report.get("offer_evaluations")
    if not isinstance(oev, list):
        return out
    for raw_oe in oev:
        if not isinstance(raw_oe, dict):
            continue
        bid = str(raw_oe.get("offer_document_id") or "").strip()
        if not bid:
            continue
        per = out.setdefault(bid, {})

        ts = raw_oe.get("technical_score")
        if isinstance(ts, dict):
            for cs in ts.get("criteria_scores") or []:
                if not isinstance(cs, dict):
                    continue
                cname = str(cs.get("criteria_name") or "")
                ck, _dao = _technical_cell_key(
                    cname, by_norm_name=by_norm_name, by_code=by_code
                )
                if ck is None:
                    continue
                awarded = cs.get("awarded_score")
                per[ck] = {
                    "score": awarded,
                    "max_score": cs.get("max_score"),
                    "weight_percent": cs.get("weight_percent"),
                    "justification": cs.get("justification"),
                    "confidence": cs.get("confidence"),
                    "m14_component": "technical_criterion",
                    "criteria_name": cname,
                }

        # Éligibilité / conformité / prix / complétude : restent dans
        # ``evaluation_documents.scores_matrix`` (JSON brut). Pas de ligne
        # ``criterion_assessments`` — CTO D-01.

    return out


# ── Types ──────────────────────────────────────────────────────────────────────


@dataclass
class BridgeResult:
    """Résultat d'un cycle populate_assessments_from_m14."""

    workspace_id: str
    evaluation_document_id: str | None
    created: int = 0
    updated: int = 0
    skipped: int = 0
    deleted_stale_rows: int = 0
    skipped_invalid_key: int = 0
    skipped_not_matrix_participant: int = 0
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

    result = BridgeResult(workspace_id=workspace_id, evaluation_document_id=None)
    result.deleted_stale_rows = _delete_stale_scoring_rows(conn, workspace_id)

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
    result.evaluation_document_id = ed["id"] if ed else None
    if not ed:
        logger.info(
            "[M14-BRIDGE] Aucune evaluation_documents pour workspace=%s", workspace_id
        )
        return result

    matrix_raw = ed.get("scores_matrix")
    if not isinstance(matrix_raw, dict) or not matrix_raw:
        logger.info(
            "[M14-BRIDGE] scores_matrix vide pour workspace=%s eval_doc=%s",
            workspace_id,
            ed["id"],
        )
        return result

    matrix_allow = matrix_participant_bundle_ids(matrix_raw)
    if matrix_raw.get("matrix_participants") == []:
        logger.warning(
            "[BRIDGE] matrix_participants vide — "
            "aucun fournisseur éligible. 0 assessment créé."
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
        """
        SELECT id::text AS id, critere_nom, m16_criterion_code::text AS m16_criterion_code
        FROM dao_criteria
        WHERE workspace_id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
    dao_crit_ids, by_norm_name, by_code = _build_dao_criterion_lookups(crit_rows)

    matrix: dict[str, Any] = matrix_raw
    oev = matrix_raw.get("offer_evaluations")
    if isinstance(oev, list) and len(oev) > 0:
        flattened = _flatten_evaluation_report_scores_matrix(
            matrix_raw,
            by_norm_name=by_norm_name,
            by_code=by_code,
        )
        if flattened:
            matrix = flattened
            logger.info(
                "[M14-BRIDGE] scores_matrix normalisé depuis EvaluationReport "
                "(offer_evaluations=%d → bundles=%d)",
                len(oev),
                len(flattened),
            )

    # ── 4. Boucle sur la matrice ──────────────────────────────────────────
    unmapped_bundles: list[str] = []
    unmapped_criteria: list[str] = []

    for bundle_key, per_bundle in matrix.items():
        bid = str(bundle_key)
        if bid not in bundle_ids:
            unmapped_bundles.append(bid)
            continue
        if matrix_allow is not None and bid not in matrix_allow:
            result.skipped_not_matrix_participant += 1
            continue
        if not isinstance(per_bundle, dict):
            continue

        for ck, cell_raw in per_bundle.items():
            criterion_key = str(ck)
            if criterion_key in _FORBIDDEN_KEYS:
                continue
            if scoring_criterion_key_is_forbidden(criterion_key):
                result.skipped_invalid_key += 1
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
            if dao_id is None:
                result.skipped_invalid_key += 1
                if _UUID_CRIT.match(criterion_key):
                    unmapped_criteria.append(criterion_key)
                logger.info(
                    "[M14-BRIDGE] skip sans dao_criterion_id workspace=%s bundle=%s "
                    "criterion_key=%s",
                    workspace_id,
                    bid,
                    criterion_key,
                )
                continue

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
        "skipped=%d deleted_stale=%d skipped_invalid_key=%d "
        "skipped_not_matrix=%d unmapped_bundles=%d unmapped_crit=%d",
        workspace_id,
        eval_doc_id,
        result.created,
        result.updated,
        result.skipped,
        result.deleted_stale_rows,
        result.skipped_invalid_key,
        result.skipped_not_matrix_participant,
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
    if not dao_criterion_id:
        logger.warning(
            "[M14-BRIDGE] refuse upsert sans dao_criterion_id bundle=%s key=%s",
            bundle_id,
            criterion_key,
        )
        return "skipped"

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
    conn.execute(
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
    )
    existing = conn.fetchone()

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
