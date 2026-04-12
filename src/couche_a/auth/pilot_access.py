"""Pilote terrain — accès complet derrière feature flag + liste explicite d’utilisateurs.

Aucun email ou id codé en dur : ``DMS_PILOT_USER_IDS`` et/ou ``DMS_PILOT_USER_EMAILS``
(Railway / env). Si le flag est actif mais les listes sont vides, **personne** n’est pilote.
"""

from __future__ import annotations

import logging
import uuid

from src.core.config import get_settings
from src.couche_a.auth.dependencies import UserClaims
from src.db import db_execute_one, get_connection

logger = logging.getLogger(__name__)

_resolved_emails_key: str = ""
_resolved_email_ids: frozenset[int] = frozenset()
_default_tenant_uuid_cache: str | None = None


def _parse_id_csv(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def _resolved_email_user_ids() -> set[int]:
    """Résout une fois par valeur d’env ``DMS_PILOT_USER_EMAILS`` (cache process)."""
    global _resolved_emails_key, _resolved_email_ids
    raw = get_settings().DMS_PILOT_USER_EMAILS.strip()
    if raw == _resolved_emails_key:
        return set(_resolved_email_ids)

    _resolved_emails_key = raw
    emails = [e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()]
    if not emails:
        _resolved_email_ids = frozenset()
        return set()

    found: set[int] = set()
    unresolved = 0
    with get_connection() as conn:
        for em in emails:
            row = db_execute_one(
                conn,
                "SELECT id FROM users WHERE lower(trim(email)) = :em LIMIT 1",
                {"em": em},
            )
            if row and row.get("id") is not None:
                found.add(int(row["id"]))
            else:
                unresolved += 1
    if unresolved:
        logger.warning(
            "DMS_PILOT_USER_EMAILS: %s entrée(s) sans correspondance users.id "
            "(emails non loggés — éviter PII en logs)",
            unresolved,
        )
    _resolved_email_ids = frozenset(found)
    return set(_resolved_email_ids)


def pilot_terrain_allowed_user_ids() -> set[int]:
    """Ensemble fusionné ids explicites + ids résolus depuis les emails."""
    if not get_settings().DMS_PILOT_TERRAIN_FULL_ACCESS:
        return set()
    allowed = _parse_id_csv(get_settings().DMS_PILOT_USER_IDS)
    allowed |= _resolved_email_user_ids()
    return allowed


def is_pilot_terrain_user_id(user_id: int) -> bool:
    if not get_settings().DMS_PILOT_TERRAIN_FULL_ACCESS:
        return False
    allowed = pilot_terrain_allowed_user_ids()
    if not allowed:
        return False
    return user_id in allowed


def is_pilot_terrain_user_claims(user: UserClaims) -> bool:
    try:
        uid = int(user.user_id)
    except (TypeError, ValueError):
        return False
    return is_pilot_terrain_user_id(uid)


def default_tenant_uuid_for_pilot_rls() -> str:
    """UUID texte du tenant pour RLS si JWT sans tenant_id (pilote uniquement).

    Préférer ``DMS_PILOT_DEFAULT_TENANT_UUID`` en prod/async pour éviter un SELECT
    synchrone au premier appel ; sinon résolution via ``DEFAULT_TENANT_CODE``.
    """
    global _default_tenant_uuid_cache
    if _default_tenant_uuid_cache:
        return _default_tenant_uuid_cache
    raw = get_settings().DMS_PILOT_DEFAULT_TENANT_UUID.strip()
    if raw:
        try:
            validated = str(uuid.UUID(raw))
        except ValueError as exc:
            msg = "DMS_PILOT_DEFAULT_TENANT_UUID doit être un UUID valide."
            logger.error("%s Reçu : %r", msg, raw[:36])
            raise RuntimeError(msg) from exc
        _default_tenant_uuid_cache = validated
        return validated
    code = get_settings().DEFAULT_TENANT_CODE.strip() or "sci_mali"
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            "SELECT id::text AS id FROM tenants WHERE code = :c LIMIT 1",
            {"c": code},
        )
    if not row or not row.get("id"):
        msg = (
            f"Pilote terrain : impossible de résoudre tenants.id pour code={code!r}. "
            "Vérifiez DEFAULT_TENANT_CODE / table tenants."
        )
        logger.error(msg)
        raise RuntimeError(msg)
    _default_tenant_uuid_cache = str(row["id"]).strip()
    return _default_tenant_uuid_cache


def rls_tenant_id_for_agent(user: UserClaims) -> str:
    """Tenant pour ``acquire_with_rls`` : claim JWT ou défaut réservé au pilote."""
    tid = user.tenant_id
    if tid and str(tid).strip():
        return str(tid).strip()
    if is_pilot_terrain_user_claims(user):
        return default_tenant_uuid_for_pilot_rls()
    raise ValueError("tenant_id manquant dans le JWT.")


def reset_pilot_access_cache_for_tests() -> None:
    """Réinitialise les caches module (pytest uniquement)."""
    global _resolved_emails_key, _resolved_email_ids, _default_tenant_uuid_cache
    _resolved_emails_key = ""
    _resolved_email_ids = frozenset()
    _default_tenant_uuid_cache = None
