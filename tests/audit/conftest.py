"""Fixtures audit — isolation transactionnelle psycopg.

Stratégie : rollback transactionnel uniquement.
Zéro DELETE · zéro TRUNCATE · zéro superuser.
audit_log vide au début de chaque test grâce au rollback.

Architecture DB : psycopg uniquement (ADR-0003 §3.1).
Réutilise db_conn depuis tests/conftest.py — zéro SQLAlchemy, zéro sessionmaker.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest

# ── Session psycopg avec rollback transactionnel ──────────────────────────────


@pytest.fixture
def db_audit(db_conn: psycopg.Connection):
    """Connexion psycopg wrappée dans une transaction — rollback en fin de test.

    audit_log est vide au début de chaque test sans DELETE explicite.
    Réutilise db_conn du root conftest (zéro duplication DATABASE_URL).
    """
    original_autocommit = db_conn.autocommit
    db_conn.autocommit = False
    try:
        yield db_conn
    finally:
        db_conn.rollback()
        db_conn.autocommit = original_autocommit


# ── Factory d'entrées audit directes ─────────────────────────────────────────


@pytest.fixture
def audit_entry_factory(db_audit: psycopg.Connection):
    """Insère une entrée audit avec des valeurs contrôlées (bypass write_event).

    Utilisé dans test_audit_chain.py pour injecter des données connues
    et tester la vérification sur des hashes précalculés.

    Le paramètre payload est utilisé tel quel (json.dumps si dict).
    """

    def _factory(
        entity: str = "test_entity",
        entity_id: str = "test-id",
        action: str = "CREATE",
        actor_id: str | None = None,
        payload: dict | None = None,
        payload_canonical: str = "",
        prev_hash: str = "GENESIS",
        event_hash: str = "aabbcc" + "00" * 29,
        chain_seq: int | None = None,
        timestamp: datetime | None = None,
        ip_address: str | None = None,
    ) -> dict:
        if timestamp is None:
            timestamp = datetime.now(UTC)

        payload_json = json.dumps(payload) if payload is not None else None

        with db_audit.cursor() as cur:
            if chain_seq is None:
                cur.execute("SELECT nextval('audit_log_chain_seq_seq') AS chain_seq")
                chain_seq = cur.fetchone()["chain_seq"]

            entry_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO audit_log (
                    id, chain_seq, entity, entity_id, action,
                    actor_id, payload, payload_canonical,
                    ip_address, timestamp, prev_hash, event_hash
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s::jsonb, %s,
                    %s::inet, %s, %s, %s
                )
                """,
                (
                    entry_id,
                    chain_seq,
                    entity,
                    entity_id,
                    action,
                    actor_id,
                    payload_json,
                    payload_canonical,
                    ip_address,
                    timestamp,
                    prev_hash,
                    event_hash,
                ),
            )

        return {
            "id": entry_id,
            "chain_seq": chain_seq,
            "entity": entity,
            "entity_id": entity_id,
            "action": action,
            "actor_id": actor_id,
            "payload": payload,
            "payload_canonical": payload_canonical,
            "ip_address": ip_address,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "event_hash": event_hash,
        }

    return _factory
