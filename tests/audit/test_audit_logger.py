"""Tests AuditLogger — écriture, hash, chaînage.

Chaque test vérifie un invariant précis selon les Contrats 1-6 (ADR-M1B-001).
Zéro assertion implicite. Zéro appel API réel (RÈGLE-21).
"""

from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy.orm import Session

from src.couche_a.audit.logger import (
    AuditAction,
    _payload_canonical,
    _timestamp_canonical,
    write_event,
)


class TestPremièreEntrée:
    def test_premiere_entree_prev_hash_genesis(self, db_session: Session) -> None:
        """Première entrée → prev_hash == 'GENESIS'."""
        entry = write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        assert entry.prev_hash == "GENESIS"

    def test_deuxieme_entree_prev_hash_est_event_hash_premiere(
        self, db_session: Session
    ) -> None:
        """Deuxième entrée → prev_hash == event_hash de la première."""
        e1 = write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        e2 = write_event("case", "c-001", AuditAction.UPDATE, db=db_session)
        assert e2.prev_hash == e1.event_hash

    def test_chain_seq_croissant(self, db_session: Session) -> None:
        """chain_seq de la deuxième entrée > chain_seq de la première."""
        e1 = write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        e2 = write_event("case", "c-002", AuditAction.CREATE, db=db_session)
        assert e2.chain_seq > e1.chain_seq

    def test_deux_write_event_chaine_coherente(self, db_session: Session) -> None:
        """Deux write_event consécutifs → chaîne cohérente."""
        e1 = write_event("vendor", "v-001", AuditAction.CREATE, db=db_session)
        e2 = write_event("vendor", "v-001", AuditAction.UPDATE, db=db_session)
        assert e2.prev_hash == e1.event_hash
        assert e2.chain_seq > e1.chain_seq


class TestEventHash:
    def test_event_hash_recalcule_manuellement(self, db_session: Session) -> None:
        """event_hash stocké == event_hash recalculé manuellement (Contrat 4)."""
        entry = write_event(
            entity="case",
            entity_id="c-hash-test",
            action=AuditAction.CREATE,
            db=db_session,
            actor_id="user-123",
            payload={"amount": 1000},
        )

        ts_canonical = _timestamp_canonical(entry.timestamp)
        raw = (
            entry.entity
            + entry.entity_id
            + entry.action
            + (entry.actor_id or "")
            + entry.payload_canonical
            + ts_canonical
            + str(entry.chain_seq)
            + entry.prev_hash
        )
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert entry.event_hash == expected

    def test_event_hash_est_hex_sha256(self, db_session: Session) -> None:
        """event_hash est un hexdigest SHA-256 valide (64 chars hex)."""
        entry = write_event("case", "c-001", AuditAction.ACCESS, db=db_session)
        assert len(entry.event_hash) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", entry.event_hash)


class TestPayloadCanonical:
    def test_payload_none_canonical_vide(self, db_session: Session) -> None:
        """payload None → payload_canonical == ''."""
        entry = write_event("case", "c-001", AuditAction.ACCESS, db=db_session)
        assert entry.payload_canonical == ""

    def test_payload_dict_canonical_json(self, db_session: Session) -> None:
        """payload dict → payload_canonical == json.dumps(sort_keys, separators, ensure_ascii)."""
        payload = {"z_key": 2, "a_key": 1}
        entry = write_event(
            "case", "c-001", AuditAction.CREATE, db=db_session, payload=payload
        )
        expected = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        assert entry.payload_canonical == expected

    def test_payload_canonical_sort_keys(self, db_session: Session) -> None:
        """payload_canonical respecte sort_keys — ordre alphabétique."""
        payload = {"z": 1, "a": 2, "m": 3}
        canonical = _payload_canonical(payload)
        assert canonical == '{"a":2,"m":3,"z":1}'

    def test_payload_vide_canonical_vide(self) -> None:
        """payload {} → payload_canonical == ''."""
        assert _payload_canonical({}) == ""

    def test_payload_unicode_ensure_ascii_false(self) -> None:
        """payload avec caractères non-ASCII → pas d'échappement unicode."""
        payload = {"ville": "Mopti"}
        canonical = _payload_canonical(payload)
        assert "Mopti" in canonical
        assert "\\u" not in canonical


class TestActorId:
    def test_actor_id_none_accepte(self, db_session: Session) -> None:
        """actor_id None → accepté sans erreur."""
        entry = write_event(
            "case", "c-001", AuditAction.CREATE, db=db_session, actor_id=None
        )
        assert entry.actor_id is None

    def test_actor_id_dans_hash(self, db_session: Session) -> None:
        """actor_id est inclus dans le calcul du hash."""
        e_with = write_event(
            "case", "c-001", AuditAction.CREATE, db=db_session, actor_id="user-A"
        )
        e_without = write_event(
            "case", "c-002", AuditAction.CREATE, db=db_session, actor_id=None
        )
        assert e_with.event_hash != e_without.event_hash


class TestIpAddress:
    def test_ip_address_none_accepte(self, db_session: Session) -> None:
        """ip_address None → accepté sans erreur."""
        entry = write_event(
            "case", "c-001", AuditAction.ACCESS, db=db_session, ip_address=None
        )
        assert entry.ip_address is None

    def test_ip_address_stockee(self, db_session: Session) -> None:
        """ip_address fournie → stockée dans l'entrée retournée."""
        entry = write_event(
            "case",
            "c-001",
            AuditAction.ACCESS,
            db=db_session,
            ip_address="192.168.1.1",
        )
        assert entry.ip_address == "192.168.1.1"


class TestRetour:
    def test_write_event_retourne_tous_les_champs(self, db_session: Session) -> None:
        """write_event() retourne une entrée avec tous les champs renseignés."""
        entry = write_event(
            entity="offer",
            entity_id="o-001",
            action=AuditAction.CREATE,
            db=db_session,
            actor_id="user-1",
            payload={"price": 500},
            ip_address="10.0.0.1",
        )
        assert entry.id
        assert entry.chain_seq > 0
        assert entry.entity == "offer"
        assert entry.entity_id == "o-001"
        assert entry.action == AuditAction.CREATE
        assert entry.actor_id == "user-1"
        assert entry.payload_canonical != ""
        assert entry.ip_address == "10.0.0.1"
        assert entry.timestamp is not None
        assert entry.prev_hash
        assert entry.event_hash


class TestTimestampCanonical:
    def test_timestamp_canonical_format(self, db_session: Session) -> None:
        """timestamp_canonical respecte le format YYYY-MM-DDTHH:MM:SS.ffffffZ."""
        entry = write_event("case", "c-001", AuditAction.CREATE, db=db_session)
        ts_canonical = _timestamp_canonical(entry.timestamp)
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
        assert re.fullmatch(
            pattern, ts_canonical
        ), f"Format inattendu : {ts_canonical!r}"
