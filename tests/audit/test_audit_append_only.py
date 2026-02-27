"""Tests trigger append-only audit_log.

Vérifie que DELETE, UPDATE et TRUNCATE sont bloqués par les triggers.
INSERT reste autorisé.
Architecture DB : psycopg uniquement (ADR-0003).
Isolation : rollback transactionnel — zéro données persistantes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from src.couche_a.audit.logger import AuditAction, write_event


def _insert_direct(db: psycopg.Connection) -> dict:
    """Insère une entrée minimale valide directement en SQL psycopg."""
    with db.cursor() as cur:
        cur.execute("SELECT nextval('audit_log_chain_seq_seq') AS chain_seq")
        chain_seq = cur.fetchone()["chain_seq"]
        entry_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO audit_log (
                id, chain_seq, entity, entity_id, action,
                payload_canonical, timestamp, prev_hash, event_hash
            ) VALUES (
                %s, %s, 'test_entity', 'test-id', 'CREATE',
                '', %s, 'GENESIS', %s
            )
            """,
            (entry_id, chain_seq, datetime.now(UTC), "a" * 64),
        )
    return {"id": entry_id, "chain_seq": chain_seq}


class TestTriggerDelete:
    def test_delete_rejete_par_trigger(self, db_audit: psycopg.Connection) -> None:
        """DELETE sur audit_log → exception · message contient 'append-only'."""
        entry = _insert_direct(db_audit)
        with pytest.raises(psycopg.errors.RaiseException) as exc_info:
            with db_audit.cursor() as cur:
                cur.execute("DELETE FROM audit_log WHERE id = %s", (entry["id"],))
        assert "append-only" in str(exc_info.value).lower()


class TestTriggerUpdate:
    def test_update_rejete_par_trigger(self, db_audit: psycopg.Connection) -> None:
        """UPDATE sur audit_log → exception · message contient 'append-only'."""
        entry = _insert_direct(db_audit)
        with pytest.raises(psycopg.errors.RaiseException) as exc_info:
            with db_audit.cursor() as cur:
                cur.execute(
                    "UPDATE audit_log SET entity = 'tampered' WHERE id = %s",
                    (entry["id"],),
                )
        assert "append-only" in str(exc_info.value).lower()


class TestTriggerTruncate:
    def test_truncate_rejete_par_trigger(self, db_audit: psycopg.Connection) -> None:
        """TRUNCATE sur audit_log → exception · message contient 'append-only'."""
        _insert_direct(db_audit)
        with pytest.raises(psycopg.errors.RaiseException) as exc_info:
            with db_audit.cursor() as cur:
                cur.execute("TRUNCATE audit_log")
        assert "append-only" in str(exc_info.value).lower()


class TestInsertAutorise:
    def test_insert_autorise(self, db_audit: psycopg.Connection) -> None:
        """INSERT sur audit_log → autorisé (trigger ne bloque pas INSERT)."""
        entry = write_event(
            entity="case",
            entity_id="c-append-test",
            action=AuditAction.CREATE,
            db=db_audit,
        )
        assert entry.id is not None
        assert entry.chain_seq > 0
