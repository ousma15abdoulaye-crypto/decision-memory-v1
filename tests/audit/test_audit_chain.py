"""Tests vérification cryptographique de la chaîne audit_log.

Vérifie fn_verify_audit_chain() DB + verify_chain() Python.
Test croisé Python ↔ DB : valide l'identité timestamp_canonical.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.couche_a.audit.logger import (
    AuditAction,
    _timestamp_canonical,
    verify_chain,
    write_event,
)


class TestVerifyChainDB:
    def test_chaine_une_entree_integre(self, db_session: Session) -> None:
        """Chaîne d'une entrée → fn_verify_audit_chain() = True."""
        write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        assert verify_chain(db_session) is True

    def test_chaine_cinq_entrees_integre(self, db_session: Session) -> None:
        """Chaîne de 5 entrées non altérées → fn_verify_audit_chain() = True."""
        for i in range(5):
            write_event("case", f"c-{i:03d}", AuditAction.CREATE, db=db_session)
        assert verify_chain(db_session) is True

    def test_event_hash_altere_detecte(
        self, db_session: Session, audit_entry_factory
    ) -> None:
        """event_hash altéré manuellement → fn_verify_audit_chain() = False."""
        entry = audit_entry_factory(
            entity="case",
            entity_id="c-tampered",
            action="CREATE",
            prev_hash="GENESIS",
            event_hash="deadbeef" * 8,
        )
        result = db_session.execute(
            text(
                "SELECT fn_verify_audit_chain(:p_from, :p_to)",
            ),
            {"p_from": entry["chain_seq"], "p_to": entry["chain_seq"]},
        ).scalar()
        assert result is False

    def test_prev_hash_altere_detecte(
        self, db_session: Session, audit_entry_factory
    ) -> None:
        """prev_hash altéré → fn_verify_audit_chain() = False."""
        e1 = audit_entry_factory(
            entity="case",
            entity_id="c-001",
            action="CREATE",
            prev_hash="GENESIS",
            event_hash="a" * 64,
        )
        audit_entry_factory(
            entity="case",
            entity_id="c-002",
            action="UPDATE",
            prev_hash="wrong_prev_hash",
            event_hash="b" * 64,
        )
        result = db_session.execute(
            text("SELECT fn_verify_audit_chain(:p_from, :p_to)"),
            {"p_from": e1["chain_seq"], "p_to": e1["chain_seq"] + 1},
        ).scalar()
        assert result is False

    def test_payload_canonical_altere_detecte(
        self, db_session: Session, audit_entry_factory
    ) -> None:
        """payload_canonical altéré → fn_verify_audit_chain() = False."""
        from datetime import UTC, datetime

        ts = datetime.now(UTC)
        ts_canonical = _timestamp_canonical(ts)

        real_payload_canonical = '{"amount":100}'
        prev = "GENESIS"
        chain_seq_val = db_session.execute(
            text("SELECT nextval('audit_log_chain_seq_seq')")
        ).scalar()

        real_hash = hashlib.sha256(
            (
                "case"
                + "c-001"
                + "CREATE"
                + ""
                + real_payload_canonical
                + ts_canonical
                + str(chain_seq_val)
                + prev
            ).encode("utf-8")
        ).hexdigest()

        import uuid

        db_session.execute(
            text("""
                INSERT INTO audit_log (
                    id, chain_seq, entity, entity_id, action,
                    actor_id, payload, payload_canonical,
                    ip_address, timestamp, prev_hash, event_hash
                ) VALUES (
                    :id, :chain_seq, 'case', 'c-001', 'CREATE',
                    NULL, NULL, :payload_canonical,
                    NULL, :timestamp, :prev_hash, :event_hash
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "chain_seq": chain_seq_val,
                "payload_canonical": "TAMPERED_CANONICAL",
                "timestamp": ts,
                "prev_hash": prev,
                "event_hash": real_hash,
            },
        )

        result = db_session.execute(
            text("SELECT fn_verify_audit_chain(:p_from, :p_to)"),
            {"p_from": chain_seq_val, "p_to": chain_seq_val},
        ).scalar()
        assert result is False


class TestVerifyChainPython:
    def test_verify_chain_python_appelle_db(self, db_session: Session) -> None:
        """verify_chain() Python délègue à fn_verify_audit_chain() DB → True."""
        write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        assert verify_chain(db_session) is True

    def test_verify_chain_plage_vide_true(self, db_session: Session) -> None:
        """verify_chain() sur plage inexistante (chain_seq très grand) → True."""
        result = verify_chain(db_session, from_seq=999999999, to_seq=999999999)
        assert result is True

    def test_verify_chain_from_to_seq_filtre(self, db_session: Session) -> None:
        """verify_chain() avec from_seq/to_seq filtre correctement."""
        e1 = write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        write_event("case", "c-002", AuditAction.CREATE, db=db_session)
        assert (
            verify_chain(db_session, from_seq=e1.chain_seq, to_seq=e1.chain_seq) is True
        )


class TestCroisePythonDB:
    def test_croise_timestamp_canonical_identique(self, db_session: Session) -> None:
        """Test croisé Python ↔ DB : timestamp_canonical identique des deux côtés.

        Écrit via write_event() Python, puis vérifie que fn_verify_audit_chain() DB
        retourne True. Si les formats timestamp divergent → ce test échoue (STOP-M1B-9).
        """
        entry = write_event(
            entity="case",
            entity_id="c-croise",
            action=AuditAction.CREATE,
            db=db_session,
            actor_id="user-audit",
            payload={"ref": "DMS-2026"},
        )

        ts_canonical_python = _timestamp_canonical(entry.timestamp)

        raw = (
            entry.entity
            + entry.entity_id
            + entry.action
            + (entry.actor_id or "")
            + entry.payload_canonical
            + ts_canonical_python
            + str(entry.chain_seq)
            + entry.prev_hash
        )
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert entry.event_hash == expected_hash, (
            f"Hash Python diverge : calculé={expected_hash!r}, "
            f"stocké={entry.event_hash!r}"
        )

        db_valid = verify_chain(
            db_session,
            from_seq=entry.chain_seq,
            to_seq=entry.chain_seq,
        )
        assert db_valid is True, (
            "fn_verify_audit_chain() DB retourne False — "
            "timestamp_canonical Python ≠ to_char PostgreSQL (STOP-M1B-9)"
        )
