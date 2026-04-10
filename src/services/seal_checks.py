"""Pré-vérifications unifiées avant scellement W3 — DMS V5.2.

Collecte TOUTES les erreurs bloquantes avant de lever une exception.
L'utilisateur voit l'intégralité des problèmes d'un seul appel.

Invariants vérifiés :
  INV-W01 : Quorum ≥ 4 membres actifs dont ≥ 1 par rôle critique
  INV-W03 : Somme poids non-éliminatoires = 100 % (± 0.5 %)
  INV-W04 : Critères éliminatoires à poids 0
  INV-FLAG : Tous les flags assessment_comments résolus

Invariants optionnels (WARNING) :
  INV-M14C : Comité Couche A non scellé si legacy_case_id existe

Réutilise quorum_service.check_quorum et weight_validator.validate_criteria_weights.
Ne contient aucune logique métier propre.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.db import db_execute_one, db_fetchall
from src.services.quorum_service import check_quorum
from src.services.weight_validator import validate_criteria_weights

logger = logging.getLogger(__name__)

# Mapping rôles V4.x legacy → rôles V5.2 (miroir guard.py _LEGACY_ROLE_MAP).
# Utilisé pour normaliser les rôles workspace_memberships avant check_quorum.
_LEGACY_ROLE_MAP: dict[str, str] = {
    "committee_chair": "supply_chain",
    "committee_member": "supply_chain",
    "procurement_lead": "supply_chain",
    "technical_reviewer": "technical",
    "finance_reviewer": "finance",
    "auditor": "admin",
}


@dataclass
class SealCheckResult:
    """Résultat agrégé de toutes les pré-vérifications de scellement."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run_all_seal_checks(conn: Any, workspace_id: str) -> SealCheckResult:
    """Exécute toutes les pré-vérifications de scellement W3.

    Connexion attendue : _ConnectionWrapper synchrone (src/db/core.py).
    La fonction ne commit/rollback jamais — lecture pure.

    Args:
        conn: Connexion DB synchrone exposant execute/fetchone/fetchall.
        workspace_id: UUID du workspace à sceller.

    Returns:
        SealCheckResult avec passed=True uniquement si AUCUNE erreur.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── CHECK 1 — Quorum INV-W01 ──────────────────────────────────────────────
    try:
        raw_members = db_fetchall(
            conn,
            """
            SELECT role
            FROM workspace_memberships
            WHERE workspace_id = CAST(:ws AS uuid)
              AND revoked_at IS NULL
            """,
            {"ws": workspace_id},
        )
        # Normalise les rôles V4.x avant d'envoyer à check_quorum
        normalized = [
            {
                "role": _LEGACY_ROLE_MAP.get(
                    str(m.get("role") or ""), str(m.get("role") or "")
                )
            }
            for m in raw_members
        ]
        quorum = check_quorum(normalized)
        if not quorum.met:
            errors.extend(quorum.blockers)
    except Exception:
        logger.exception(
            "[SEAL-CHECK] Erreur lecture quorum workspace=%s", workspace_id
        )
        errors.append("Erreur interne lors de la vérification du quorum (INV-W01).")

    # ── CHECK 2 — Poids critères INV-W03 / INV-W04 ───────────────────────────
    try:
        weight_result = validate_criteria_weights(conn, workspace_id)
        if not weight_result["valid"]:
            errors.extend(weight_result["errors"])
        elif weight_result["criteria_count"] == 0:
            warnings.append(
                "Aucun critère dao_criteria trouvé pour ce workspace — "
                "les poids n'ont pas pu être vérifiés (INV-W03). "
                "Si M14 n'a pas tourné, la validation sera effectuée manuellement."
            )
    except Exception:
        logger.exception("[SEAL-CHECK] Erreur lecture poids workspace=%s", workspace_id)
        errors.append(
            "Erreur interne lors de la vérification des poids critères (INV-W03)."
        )

    # ── CHECK 3 — Flags non résolus ───────────────────────────────────────────
    try:
        flag_row = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::bigint AS n
            FROM assessment_comments
            WHERE workspace_id = CAST(:ws AS uuid)
              AND is_flag = true
              AND resolved = false
            """,
            {"ws": workspace_id},
        )
        open_flags = int((flag_row or {}).get("n") or 0)
        if open_flags > 0:
            errors.append(
                f"{open_flags} signalement(s) non résolu(s) bloquent le scellement. "
                "Tous les flags doivent être résolus avant de sceller (INV-FLAG)."
            )
    except Exception:
        logger.exception("[SEAL-CHECK] Erreur lecture flags workspace=%s", workspace_id)
        errors.append("Erreur interne lors de la vérification des flags non résolus.")

    # ── CHECK 4 — Cohérence Couche A (WARNING uniquement) ────────────────────
    try:
        ws_row = db_execute_one(
            conn,
            "SELECT legacy_case_id FROM process_workspaces WHERE id = CAST(:ws AS uuid)",
            {"ws": workspace_id},
        )
        legacy_case_id = (ws_row or {}).get("legacy_case_id")
        if legacy_case_id:
            committee_row = db_execute_one(
                conn,
                "SELECT status FROM public.committees WHERE case_id = CAST(:cid AS uuid) LIMIT 1",
                {"cid": str(legacy_case_id)},
            )
            if committee_row and str(committee_row.get("status") or "") != "sealed":
                warnings.append(
                    f"Le comité Couche A (case_id={legacy_case_id}) n'est pas encore scellé "
                    f"(status={committee_row.get('status')!r}). "
                    "Les données M14 pourraient évoluer après le scellement W3."
                )
    except Exception:
        # La table committees peut ne pas exister en contexte purement V5.2
        logger.debug(
            "[SEAL-CHECK] Check cohérence M14 non applicable workspace=%s", workspace_id
        )

    passed = len(errors) == 0
    if not passed:
        logger.warning(
            "[SEAL-CHECK] workspace=%s BLOQUÉ — %d erreur(s) : %s",
            workspace_id,
            len(errors),
            errors,
        )
    else:
        logger.info(
            "[SEAL-CHECK] workspace=%s OK — %d warning(s)",
            workspace_id,
            len(warnings),
        )

    return SealCheckResult(passed=passed, errors=errors, warnings=warnings)
