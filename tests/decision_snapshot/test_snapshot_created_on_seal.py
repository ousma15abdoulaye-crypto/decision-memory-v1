"""T6b — Snapshot créé lors du seal: champs obligatoires non-null."""

import uuid

from src.couche_a.committee import service
from src.couche_a.committee.models import SealRequest


def _build_sealable_committee(case_factory, committee_factory, db_conn):
    case_id = case_factory(status="active")
    committee_id = committee_factory(case_id=case_id, status="open")
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_members "
            "(member_id, committee_id, user_ref, role, can_vote, status) "
            "VALUES (%s, %s, 'voter', 'member', true, 'active')",
            (str(uuid.uuid4()), committee_id),
        )
        cur.execute(
            "INSERT INTO public.committee_decisions "
            "(decision_id, committee_id, case_id, selected_supplier_id, "
            " supplier_name_raw, decision_status, rationale) "
            "VALUES (%s, %s, %s, 'sup-1', 'ETS KONATÉ SARL', 'proposed', %s)",
            (
                str(uuid.uuid4()),
                committee_id,
                case_id,
                "Fournisseur retenu après analyse rigoureuse des critères techniques et financiers",
            ),
        )
    return committee_id, case_id


class TestSnapshotCreatedOnSeal:
    def test_snapshot_non_null_required_fields(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        committee_id, case_id = _build_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        req = SealRequest(
            sealed_by="alice",
            zone="Bamako",
            currency="XOF",
            alias_raw="Rame papier A4 80g",
            quantity=500,
            unit="rame",
            price_paid=1250.0,
            supplier_id="sup-1",
        )
        service.seal_committee_decision(committee_id, req, db_conn)
        snap = service.get_decision_snapshot(committee_id, db_conn)

        assert snap is not None
        # Champs non-null requis (§T6b)
        assert snap["alias_raw"] is not None and snap["alias_raw"] != ""
        assert snap["supplier_name_raw"] is not None and snap["supplier_name_raw"] != ""
        assert snap["zone"] is not None and snap["zone"] != ""
        assert snap["currency"] is not None and snap["currency"] != ""
        assert snap["snapshot_hash"] is not None and len(snap["snapshot_hash"]) == 64
        assert snap["decision_at"] is not None

    def test_snapshot_hash_is_deterministic(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        """Le même payload produit le même hash."""
        from datetime import UTC, datetime

        from src.couche_a.committee.snapshot import compute_snapshot_hash

        fixed_dt = datetime(2026, 2, 23, 10, 0, 0, tzinfo=UTC)
        data = {
            "case_id": "case-det-001",
            "committee_id": "comm-det-001",
            "decision_at": fixed_dt,
            "supplier_name_raw": "ETS KONATÉ",
            "alias_raw": "Rame A4",
            "currency": "XOF",
            "zone": "Bamako",
        }
        h1 = compute_snapshot_hash(data)
        h2 = compute_snapshot_hash(data)
        assert h1 == h2
        assert len(h1) == 64

    def test_snapshot_committee_id_matches(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        committee_id, _ = _build_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        req = SealRequest(
            sealed_by="bob",
            zone="Mopti",
            currency="XOF",
            alias_raw="Carburant gasoil",
            quantity=1000,
            unit="litre",
            price_paid=750.0,
        )
        service.seal_committee_decision(committee_id, req, db_conn)
        snap = service.get_decision_snapshot(committee_id, db_conn)
        assert str(snap["committee_id"]) == str(committee_id)
