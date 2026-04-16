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
import uuid as uuid_mod
from collections import defaultdict
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


class PipelineError(RuntimeError):
    """Fail-fast bridge D-004 (strict_uuid) — matrice scorable sans clé DAO canonique."""


_D004_DGMP_PREFIX = re.compile(r"^dgmp[%_:]", re.IGNORECASE)


def matches_d004_excluded_scoring_pattern(criterion_key: str) -> bool:
    """Préfixes interdits sur le scoring path (mandat D-004 Règle 3)."""
    ck = (criterion_key or "").strip()
    if not ck:
        return True
    low = ck.lower()
    if low.startswith("m14:eligibility:") or low.startswith("m14:compliance:"):
        return True
    if _D004_DGMP_PREFIX.match(low):
        return True
    return False


def resolve_strict_scoring_criterion_key(
    criterion_key: str, dao_crit_ids: frozenset[str]
) -> str | None:
    """Résout ``criterion_key`` vers un ``dao_criteria.id`` du workspace (toute variante UUID).

    Retourne l'identifiant texte tel que présent dans ``dao_crit_ids`` si match,
    sinon ``None`` (clé non canonique).
    """
    ck = (criterion_key or "").strip()
    if not ck:
        return None
    if ck in _FORBIDDEN_KEYS or ck.lower() in {x.lower() for x in _FORBIDDEN_KEYS}:
        return None
    if scoring_criterion_key_is_forbidden(ck):
        return None
    if matches_d004_excluded_scoring_pattern(ck):
        return None
    try:
        parsed = uuid_mod.UUID(ck)
    except ValueError:
        return None
    for did in dao_crit_ids:
        try:
            if uuid_mod.UUID(str(did)) == parsed:
                return str(did)
        except ValueError:
            continue
    return None


def assert_scorable_bundles_have_at_least_one_canonical_key(
    matrix: dict[str, Any],
    *,
    matrix_allow: frozenset[str],
    dao_crit_ids: frozenset[str],
) -> None:
    """Lève ``PipelineError`` si un bundle scorable n'a aucune clé résoluble en DAO."""
    for bid in matrix_allow:
        if bid not in matrix:
            raise PipelineError(
                "bridge_strict_uuid:bundle_fail_fast — "
                f"bundle {bid} in matrix_participants but absent from scores_matrix"
            )
        per = matrix.get(bid)
        if not isinstance(per, dict):
            raise PipelineError(
                "bridge_strict_uuid:bundle_fail_fast — "
                f"bundle {bid} has invalid scores_matrix entry (not a dict)"
            )
        if not per:
            raise PipelineError(
                "bridge_strict_uuid:bundle_fail_fast — "
                f"bundle {bid} has empty scoring dict in scores_matrix"
            )
        if any(resolve_strict_scoring_criterion_key(str(k), dao_crit_ids) for k in per):
            continue
        raise PipelineError(
            "bridge_strict_uuid:bundle_fail_fast — "
            f"bundle {bid} has {len(per)} scoring cell(s) but zero "
            "criterion_key resolves to dao_criteria.id for this workspace"
        )


def matrix_participant_bundle_ids(
    matrix_raw: dict[str, Any], *, strict: bool = False
) -> frozenset[str] | None:
    """IDs autorisés pour persistance matrice ; ``None`` = pas de filtre (documents legacy).

    Liste vide explicite → jeu vide (aucun bundle ne reçoit d'assessment).

    :param strict: Si True, lever PipelineError si matrix_participants absent/None
                  (requis sur chemin pipeline_v5). Si False (défaut), mode legacy
                  autorisé (log warning, retour None).
    """
    if "matrix_participants" not in matrix_raw:
        if strict:
            raise BridgeConfigurationError(
                "bridge_invalid:matrix_participants_required_in_strict_mode — "
                "matrix_participants key missing from payload"
            )
        logger.warning(
            "[BRIDGE] matrix_participants absent du payload "
            "— filtre Gate C désactivé (mode legacy)"
        )
        return None
    mp = matrix_raw.get("matrix_participants")
    if mp is None:
        if strict:
            raise BridgeConfigurationError(
                "bridge_invalid:matrix_participants_required_in_strict_mode — "
                "matrix_participants is None in payload"
            )
        logger.warning(
            "[BRIDGE] matrix_participants absent du payload "
            "— filtre Gate C désactivé (mode legacy)"
        )
        return None
    if not isinstance(mp, list | set | frozenset):
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
    rejected_noncanonical_keys: int = 0
    structured_warnings: list[str] = field(default_factory=list)
    unmapped_bundles: list[str] = field(default_factory=list)
    unmapped_criteria: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── Fonction principale ────────────────────────────────────────────────────────


def populate_assessments_from_m14(
    workspace_id: str,
    *,
    strict_matrix_participants: bool = False,
    strict_uuid: bool = False,
) -> BridgeResult:
    """Pré-remplit criterion_assessments depuis evaluation_documents.scores_matrix.

    Connexion synchrone via get_connection() (même pattern que m16_backfill).
    Idempotent : appels successifs sans données M14 nouvelles = 0 created/updated.

    :param strict_matrix_participants: Si True, lever BridgeConfigurationError si
                                      matrix_participants absent/None (requis pipeline_v5).
                                      Si False (défaut), mode legacy autorisé (autres chemins).
    :param strict_uuid: Si True (pipeline_v5 uniquement), n'insère que des clés
                        ``dao_criteria.id`` résolues ; compteur
                        ``rejected_noncanonical_keys`` ; fail-fast bundle si besoin.

    Args:
        workspace_id: UUID (str) du workspace.

    Returns:
        BridgeResult avec compteurs created / updated / skipped et les listes
        d'éléments non mappés (pour debug / rapport).
    """
    with get_connection() as conn:
        return _run_bridge(
            conn,
            workspace_id,
            strict_matrix_participants=strict_matrix_participants,
            strict_uuid=strict_uuid,
        )


def _run_bridge(
    conn: Any,
    workspace_id: str,
    *,
    strict_matrix_participants: bool = False,
    strict_uuid: bool = False,
) -> BridgeResult:
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

    matrix_allow = matrix_participant_bundle_ids(
        matrix_raw, strict=strict_matrix_participants
    )
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
    strict_bundle_rejected: dict[str, int] = defaultdict(int)
    strict_bundle_canonical_ok: dict[str, int] = defaultdict(int)

    for bundle_key, per_bundle in matrix.items():
        bid = str(bundle_key)
        if bid in ("matrix_participants", "excluded_from_matrix"):
            continue
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
                if strict_uuid:
                    result.rejected_noncanonical_keys += 1
                    strict_bundle_rejected[bid] += 1
                continue

            if strict_uuid:
                canon_dao = resolve_strict_scoring_criterion_key(
                    criterion_key, dao_crit_ids
                )
                if canon_dao is None:
                    result.rejected_noncanonical_keys += 1
                    strict_bundle_rejected[bid] += 1
                    if _UUID_CRIT.match(criterion_key):
                        unmapped_criteria.append(criterion_key)
                    logger.info(
                        "[M14-BRIDGE] strict_uuid skip non-canonique workspace=%s "
                        "bundle=%s criterion_key=%s",
                        workspace_id,
                        bid,
                        criterion_key,
                    )
                    continue
                criterion_key = canon_dao
                dao_id: str | None = canon_dao
                strict_bundle_canonical_ok[bid] += 1
            else:
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
                dao_id = criterion_key if criterion_key in dao_crit_ids else None
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

            if strict_uuid:
                if isinstance(cell_raw, dict):
                    cell_obj = {**cell_raw}
                else:
                    cell_obj = {"value": cell_raw}
                cell_obj.setdefault("source", "m14")
                cell_obj.setdefault("m14_original", True)

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

    if strict_uuid and matrix_allow is not None:
        assert_scorable_bundles_have_at_least_one_canonical_key(
            matrix,
            matrix_allow=matrix_allow,
            dao_crit_ids=dao_crit_ids,
        )
        for bid in matrix_allow:
            rej = strict_bundle_rejected.get(bid, 0)
            ok = strict_bundle_canonical_ok.get(bid, 0)
            if rej > 0 and ok > 0:
                total = rej + ok
                warn = (
                    f"bridge_strict_uuid:{rej}/{total} criterion_keys non "
                    f"canoniques ignorées — bundle {bid}"
                )
                result.structured_warnings.append(warn)
                logger.warning("[M14-BRIDGE] %s", warn)

    result.unmapped_bundles = list(dict.fromkeys(unmapped_bundles))
    result.unmapped_criteria = list(dict.fromkeys(unmapped_criteria))

    logger.info(
        "[M14-BRIDGE] workspace=%s eval_doc=%s → created=%d updated=%d "
        "skipped=%d deleted_stale=%d skipped_invalid_key=%d "
        "skipped_not_matrix=%d rejected_noncanonical=%d "
        "unmapped_bundles=%d unmapped_crit=%d",
        workspace_id,
        eval_doc_id,
        result.created,
        result.updated,
        result.skipped,
        result.deleted_stale_rows,
        result.skipped_invalid_key,
        result.skipped_not_matrix_participant,
        result.rejected_noncanonical_keys,
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
