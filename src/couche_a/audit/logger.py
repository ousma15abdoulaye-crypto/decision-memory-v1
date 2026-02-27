"""AuditLogger — moteur d'écriture et de vérification de la chaîne d'audit.

Contrats immuables (ADR-M1B-001) :
  - Contrat 1 : ordre des champs dans event_hash
  - Contrat 2 : payload_canonical = json.dumps(sort_keys, separators, ensure_ascii)
  - Contrat 3 : timestamp_canonical = UTC ISO 8601 microsecondes suffixe Z
  - Contrat 4 : event_hash = SHA-256 hexdigest
  - Contrat 5 : prev_hash = "GENESIS" si première entrée
  - Contrat 6 : mono-insert — nextval() → calcul → INSERT unique, zéro UPDATE post-insert

Zéro touche à src/auth.py · src/couche_a/auth/ · token_blacklist (RÈGLE-ORG-07).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class AuditAction:
    """Actions auditables — extensible, ne jamais redéfinir les existants."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ACCESS = "ACCESS"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass
class AuditLogEntry:
    """Entrée audit retournée par write_event()."""

    id: str
    chain_seq: int
    entity: str
    entity_id: str
    action: str
    actor_id: str | None
    payload: dict | None
    payload_canonical: str
    ip_address: str | None
    timestamp: datetime
    prev_hash: str
    event_hash: str


def _payload_canonical(payload: dict | None) -> str:
    """Contrat 2 — représentation canonique immuable du payload."""
    if not payload:
        return ""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _timestamp_canonical(ts: datetime) -> str:
    """Contrat 3 — format UTC ISO 8601 avec microsecondes et suffixe Z."""
    ts_utc = ts.astimezone(UTC)
    return ts_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts_utc.microsecond:06d}Z"


def _compute_event_hash(
    entity: str,
    entity_id: str,
    action: str,
    actor_id: str | None,
    payload_canonical: str,
    timestamp_canonical: str,
    chain_seq: int,
    prev_hash: str,
) -> str:
    """Contrat 4 — SHA-256 des champs dans l'ordre exact du Contrat 1."""
    raw = (
        entity
        + entity_id
        + action
        + (actor_id or "")
        + payload_canonical
        + timestamp_canonical
        + str(chain_seq)
        + prev_hash
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_event(
    entity: str,
    entity_id: str,
    action: str,
    db: Session,
    actor_id: str | None = None,
    payload: dict | None = None,
    ip_address: str | None = None,
) -> AuditLogEntry:
    """Écrit un événement dans audit_log avec chaînage cryptographique.

    Séquence mono-insert (Contrat 6) :
      1. nextval() → chain_seq connu avant l'INSERT
      2. Calculer payload_canonical, timestamp_canonical, prev_hash, event_hash
      3. INSERT unique et complet — zéro UPDATE post-insert

    Atomicité : tout dans la même transaction que l'opération métier appelante.
    Si write_event() échoue → rollback de l'opération métier.

    Sécurité : zéro secret dans payload (token, password, clé).
    Masquer AVANT d'appeler write_event().
    """
    # ── 1. chain_seq via nextval — connu avant INSERT ────────────────────────
    chain_seq: int = db.execute(
        text("SELECT nextval('audit_log_chain_seq_seq')")
    ).scalar()

    # ── 2. Canonicalisation ──────────────────────────────────────────────────
    p_canonical = _payload_canonical(payload)
    ts = datetime.now(UTC)
    ts_canonical = _timestamp_canonical(ts)

    # ── 3. prev_hash — Contrat 5 ─────────────────────────────────────────────
    row = db.execute(
        text("SELECT event_hash FROM audit_log ORDER BY chain_seq DESC LIMIT 1")
    ).fetchone()
    prev_hash = row[0] if row else "GENESIS"

    # ── 4. event_hash — Contrats 1 + 4 ──────────────────────────────────────
    event_hash = _compute_event_hash(
        entity=entity,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        payload_canonical=p_canonical,
        timestamp_canonical=ts_canonical,
        chain_seq=chain_seq,
        prev_hash=prev_hash,
    )

    # ── 5. INSERT unique et complet — zéro UPDATE post-insert ────────────────
    entry_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO audit_log (
                id, chain_seq, entity, entity_id, action,
                actor_id, payload, payload_canonical,
                ip_address, timestamp, prev_hash, event_hash
            ) VALUES (
                :id, :chain_seq, :entity, :entity_id, :action,
                :actor_id, CAST(:payload AS jsonb), :payload_canonical,
                CAST(:ip_address AS inet), :timestamp, :prev_hash, :event_hash
            )
        """),
        {
            "id": entry_id,
            "chain_seq": chain_seq,
            "entity": entity,
            "entity_id": entity_id,
            "action": action,
            "actor_id": actor_id,
            "payload": json.dumps(payload) if payload is not None else None,
            "payload_canonical": p_canonical,
            "ip_address": ip_address,
            "timestamp": ts,
            "prev_hash": prev_hash,
            "event_hash": event_hash,
        },
    )

    return AuditLogEntry(
        id=entry_id,
        chain_seq=chain_seq,
        entity=entity,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        payload=payload,
        payload_canonical=p_canonical,
        ip_address=ip_address,
        timestamp=ts,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )


def verify_chain(
    db: Session,
    from_seq: int | None = None,
    to_seq: int | None = None,
) -> bool:
    """Vérifie l'intégrité cryptographique de la chaîne audit_log.

    Délègue à fn_verify_audit_chain() côté DB (pgcrypto + to_char UTC).

    Args:
        db: session SQLAlchemy active.
        from_seq: chain_seq de début (inclusif). None → 0.
        to_seq: chain_seq de fin (inclusif). None → BIGINT MAX.

    Returns:
        True si la chaîne est intègre, False si rupture détectée.
    """
    p_from = from_seq if from_seq is not None else 0
    p_to = to_seq if to_seq is not None else 9223372036854775807

    result = db.execute(
        text("SELECT fn_verify_audit_chain(:p_from, :p_to)"),
        {"p_from": p_from, "p_to": p_to},
    ).scalar()
    return bool(result)
