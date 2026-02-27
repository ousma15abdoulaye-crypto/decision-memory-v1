"""Fixtures audit — isolation transactionnelle.

Stratégie : rollback transactionnel uniquement.
Zéro DELETE · zéro TRUNCATE · zéro superuser.
audit_log vide au début de chaque test grâce au rollback.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


# ── Engine ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def db_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, echo=False)
    yield engine
    engine.dispose()


# ── Session avec rollback transactionnel ─────────────────────────────────────


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Session SQLAlchemy wrappée dans une transaction — rollback en fin de test.

    audit_log est vide au début de chaque test sans DELETE explicite.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── Factory d'entrées audit directes ─────────────────────────────────────────


@pytest.fixture
def audit_entry_factory(db_session: Session):
    """Insère une entrée audit avec des valeurs contrôlées (bypass write_event).

    Utilisé dans test_audit_chain.py pour injecter des données connues
    et tester la vérification sur des hashes précalculés.
    """

    def _factory(
        entity: str = "test_entity",
        entity_id: str = "test-id",
        action: str = "CREATE",
        actor_id: str | None = None,
        payload: dict | None = None,
        payload_canonical: str = "",
        prev_hash: str = "GENESIS",
        event_hash: str = "aabbcc",
        chain_seq: int | None = None,
        timestamp: datetime | None = None,
        ip_address: str | None = None,
    ) -> dict:
        if chain_seq is None:
            chain_seq = db_session.execute(
                text("SELECT nextval('audit_log_chain_seq_seq')")
            ).scalar()
        if timestamp is None:
            timestamp = datetime.now(UTC)

        entry_id = str(uuid.uuid4())
        db_session.execute(
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
                "payload": None,
                "payload_canonical": payload_canonical,
                "ip_address": ip_address,
                "timestamp": timestamp,
                "prev_hash": prev_hash,
                "event_hash": event_hash,
            },
        )
        return {
            "id": entry_id,
            "chain_seq": chain_seq,
            "entity": entity,
            "entity_id": entity_id,
            "action": action,
            "actor_id": actor_id,
            "payload_canonical": payload_canonical,
            "ip_address": ip_address,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "event_hash": event_hash,
        }

    return _factory
