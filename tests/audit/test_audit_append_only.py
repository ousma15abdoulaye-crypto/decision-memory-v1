"""Tests trigger append-only audit_log.

Vérifie que DELETE, UPDATE et TRUNCATE sont bloqués par les triggers.
INSERT reste autorisé.
Isolation : rollback transactionnel — zéro données persistantes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from src.couche_a.audit.logger import AuditAction, write_event


def _insert_direct(db_session: Session) -> dict:
    """Insère une entrée minimale valide directement en SQL."""
    chain_seq = db_session.execute(
        text("SELECT nextval('audit_log_chain_seq_seq')")
    ).scalar()
    entry_id = str(uuid.uuid4())
    db_session.execute(
        text("""
            INSERT INTO audit_log (
                id, chain_seq, entity, entity_id, action,
                payload_canonical, timestamp, prev_hash, event_hash
            ) VALUES (
                :id, :chain_seq, 'test_entity', 'test-id', 'CREATE',
                '', :timestamp, 'GENESIS', :event_hash
            )
        """),
        {
            "id": entry_id,
            "chain_seq": chain_seq,
            "timestamp": datetime.now(UTC),
            "event_hash": "a" * 64,
        },
    )
    return {"id": entry_id, "chain_seq": chain_seq}


class TestTriggerDelete:
    def test_delete_rejete_par_trigger(self, db_session: Session) -> None:
        """DELETE sur audit_log → exception · message contient 'append-only'."""
        entry = _insert_direct(db_session)
        with pytest.raises(ProgrammingError) as exc_info:
            db_session.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": entry["id"]},
            )
        assert "append-only" in str(exc_info.value).lower()


class TestTriggerUpdate:
    def test_update_rejete_par_trigger(self, db_session: Session) -> None:
        """UPDATE sur audit_log → exception · message contient 'append-only'."""
        entry = _insert_direct(db_session)
        with pytest.raises(ProgrammingError) as exc_info:
            db_session.execute(
                text("UPDATE audit_log SET entity = 'tampered' WHERE id = :id"),
                {"id": entry["id"]},
            )
        assert "append-only" in str(exc_info.value).lower()


class TestTriggerTruncate:
    def test_truncate_rejete_par_trigger(self, db_session: Session) -> None:
        """TRUNCATE sur audit_log → exception · message contient 'append-only'."""
        _insert_direct(db_session)
        with pytest.raises(ProgrammingError) as exc_info:
            db_session.execute(text("TRUNCATE audit_log"))
        assert "append-only" in str(exc_info.value).lower()


class TestInsertAutorise:
    def test_insert_autorise(self, db_session: Session) -> None:
        """INSERT sur audit_log → autorisé (trigger ne bloque pas INSERT)."""
        entry = write_event(
            entity="case",
            entity_id="c-append-test",
            action=AuditAction.CREATE,
            db=db_session,
        )
        assert entry.id is not None
        assert entry.chain_seq > 0
