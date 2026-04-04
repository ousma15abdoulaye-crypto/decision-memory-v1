"""Helpers de contexte workspace — Phase dual-write V4.2.0.

Pendant la période dual-write (Phase 2 → Phase 3), le code existant écrit
à la fois case_id ET workspace_id. Ces helpers permettent de résoudre
le workspace_id depuis un case_id sans modifier la logique métier des
modules existants.

Après migration 074 (DROP case_id), ce module sera simplifié pour
ne retourner que le workspace_id depuis le contexte requête.

Référence : Plan V4.2.0 Phase 2 — Pattern dual-write
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_workspace_id_for_case(conn, case_id: str) -> str | None:
    """Résout le workspace_id correspondant à un case_id existant.

    Utilisé pendant la période dual-write pour enrichir les INSERTs
    dans les tables canon (documents, evaluation_criteria, etc.).

    Returns:
        UUID workspace_id sous forme de string, ou None si non trouvé
        (case migré ou migration 069 non encore appliquée).
    """
    try:
        conn.execute(
            "SELECT id FROM process_workspaces WHERE legacy_case_id = :cid LIMIT 1",
            {"cid": case_id},
        )
        row = conn.fetchone()
        if row:
            return str(row["id"])
    except Exception as exc:
        logger.debug(
            "[DUAL-WRITE] workspace_id lookup pour case %s échoué : %s",
            case_id,
            exc,
        )
    return None


def enrich_insert_with_workspace_id(
    params: dict,
    conn,
    case_id_key: str = "case_id",
    workspace_id_key: str = "workspace_id",
) -> dict:
    """Ajoute workspace_id dans un dict de params INSERT si disponible.

    Pattern dual-write : si workspace_id absent et case_id présent,
    résout et injecte workspace_id.

    Args:
        params: dictionnaire de paramètres SQL (modifié en place).
        conn: connexion DB (src.db.core._ConnectionWrapper).
        case_id_key: clé du case_id dans params.
        workspace_id_key: clé du workspace_id à injecter.

    Returns:
        params (dict modifié en place, workspace_id ajouté si résolu).
    """
    if workspace_id_key in params and params[workspace_id_key]:
        return params

    case_id = params.get(case_id_key)
    if not case_id:
        return params

    workspace_id = get_workspace_id_for_case(conn, str(case_id))
    if workspace_id:
        params[workspace_id_key] = workspace_id
        logger.debug(
            "[DUAL-WRITE] case %s -> workspace %s enrichi.",
            case_id,
            workspace_id,
        )
    return params
