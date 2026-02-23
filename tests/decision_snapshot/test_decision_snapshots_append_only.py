"""T6a — Trigger append-only decision_snapshots: UPDATE/DELETE bloqués."""

import uuid
from datetime import UTC, datetime

import psycopg
import pytest


def _insert_snapshot(case_id: str, committee_id: str, db_conn) -> str:
    from src.couche_a.committee.snapshot import compute_snapshot_hash

    data = {
        "case_id": case_id,
        "committee_id": committee_id,
        "decision_at": datetime.now(UTC),
        "supplier_name_raw": "ETS TEST",
        "alias_raw": "Rame papier A4",
        "currency": "XOF",
        "zone": "Bamako",
    }
    snap_hash = compute_snapshot_hash(data)
    snap_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.decision_snapshots "
            "(snapshot_id, case_id, committee_id, decision_at, zone, currency, "
            " alias_raw, supplier_name_raw, source_hashes, scoring_meta, snapshot_hash) "
            "VALUES (%s, %s, %s, %s, 'Bamako', 'XOF', 'Rame', 'ETS TEST', '{}', '{}', %s)",
            (snap_id, case_id, committee_id, datetime.now(UTC), snap_hash),
        )
    return snap_id


class TestDecisionSnapshotsAppendOnly:
    def test_insert_allowed(self, db_conn, case_factory, committee_factory):
        """INSERT doit fonctionner."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        snap_id = _insert_snapshot(case_id, committee_id, db_conn)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT snapshot_id FROM public.decision_snapshots WHERE snapshot_id=%s",
                (snap_id,),
            )
            assert cur.fetchone() is not None

    def test_update_blocked(self, db_conn, case_factory, committee_factory):
        """UPDATE doit lever une exception append-only."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        snap_id = _insert_snapshot(case_id, committee_id, db_conn)

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.decision_snapshots SET zone='Tombouctou' WHERE snapshot_id=%s",
                    (snap_id,),
                )
        assert "append-only" in str(exc_info.value).lower()
        db_conn.rollback()

    def test_delete_blocked(self, db_conn, case_factory, committee_factory):
        """DELETE doit lever une exception append-only."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        snap_id = _insert_snapshot(case_id, committee_id, db_conn)

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.decision_snapshots WHERE snapshot_id=%s",
                    (snap_id,),
                )
        assert "append-only" in str(exc_info.value).lower()
        db_conn.rollback()
