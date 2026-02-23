"""T5 — Transaction de seal : atomicité, snapshot, idempotence, blocages post-seal."""

import uuid

import psycopg
import pytest

from src.couche_a.committee import service
from src.couche_a.committee.models import (
    CommitteeStateError,
    CommitteeValidationError,
    SealRequest,
)

# ------------------------------------------------------------------ helpers


def _setup_sealable_committee(case_factory, committee_factory, db_conn):
    """Crée un comité prêt à être scellé.

    Retourne (committee_id, case_id).
    """
    case_id = case_factory(status="active")
    committee_id = committee_factory(case_id=case_id, status="open")

    # Ajouter un votant actif
    member_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_members "
            "(member_id, committee_id, user_ref, role, can_vote, status) "
            "VALUES (%s, %s, 'voter-1', 'member', true, 'active')",
            (member_id, committee_id),
        )

    # Décision candidate valide
    decision_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_decisions "
            "(decision_id, committee_id, case_id, selected_supplier_id, "
            " supplier_name_raw, decision_status, rationale) "
            "VALUES (%s, %s, %s, 'sup-001', 'ETS KONATÉ SARL', 'proposed', %s)",
            (
                decision_id,
                committee_id,
                case_id,
                "Fournisseur retenu après analyse des critères techniques et financiers",
            ),
        )
    return committee_id, case_id


def _seal_req(zone: str = "Bamako", currency: str = "XOF") -> SealRequest:
    return SealRequest(
        sealed_by="alice",
        zone=zone,
        currency=currency,
        alias_raw="Rame papier A4 80g",
        quantity=100,
        unit="rame",
        price_paid=1250.0,
        supplier_id="sup-001",
        source_hashes={"score_run_id": str(uuid.uuid4())},
        scoring_meta={"version": "v0.2"},
    )


# ------------------------------------------------------------------ T5 tests


class TestCommitteeSealTransaction:
    def test_seal_creates_snapshot_atomically(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        committee_id, case_id = _setup_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        result = service.seal_committee_decision(committee_id, _seal_req(), db_conn)

        assert result.seal_id is not None
        assert result.snapshot_hash is not None

        snap = service.get_decision_snapshot(committee_id, db_conn)
        assert snap is not None
        assert snap["snapshot_hash"] == result.snapshot_hash

        c = service.get_committee(committee_id, db_conn)
        assert c["status"] == "sealed"

    def test_seal_without_decision_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        """Seal sans décision candidate → CommitteeStateError."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.committee_members "
                "(member_id, committee_id, user_ref, role, can_vote, status) "
                "VALUES (%s, %s, 'v1', 'member', true, 'active')",
                (str(uuid.uuid4()), committee_id),
            )
        # Aucune décision insérée
        with pytest.raises((CommitteeStateError, CommitteeValidationError)):
            service.seal_committee_decision(committee_id, _seal_req(), db_conn)

    def test_seal_without_rationale_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.committee_members "
                "(member_id, committee_id, user_ref, role, can_vote, status) "
                "VALUES (%s, %s, 'v1', 'member', true, 'active')",
                (str(uuid.uuid4()), committee_id),
            )
            decision_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO public.committee_decisions "
                "(decision_id, committee_id, case_id, selected_supplier_id, "
                " supplier_name_raw, decision_status, rationale) "
                "VALUES (%s, %s, %s, 'sup-1', 'Test Sup', 'proposed', 'court')",
                (decision_id, committee_id, case_id),
            )
        with pytest.raises((CommitteeStateError, CommitteeValidationError)):
            service.seal_committee_decision(committee_id, _seal_req(), db_conn)

    def test_seal_with_no_award_valid(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.committee_members "
                "(member_id, committee_id, user_ref, role, can_vote, status) "
                "VALUES (%s, %s, 'v1', 'member', true, 'active')",
                (str(uuid.uuid4()), committee_id),
            )
            decision_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO public.committee_decisions "
                "(decision_id, committee_id, case_id, selected_supplier_id, "
                " supplier_name_raw, decision_status, rationale) "
                "VALUES (%s, %s, %s, NULL, NULL, 'no_award', %s)",
                (
                    decision_id,
                    committee_id,
                    case_id,
                    "Aucun fournisseur ne satisfait les critères techniques et financiers requis",
                ),
            )
        result = service.seal_committee_decision(committee_id, _seal_req(), db_conn)
        assert result.seal_id is not None

    def test_sealed_committee_blocks_member_insert(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        committee_id, _ = _setup_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        service.seal_committee_decision(committee_id, _seal_req(), db_conn)

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO public.committee_members "
                    "(member_id, committee_id, user_ref, role) "
                    "VALUES (%s, %s, 'intrus', 'observer')",
                    (str(uuid.uuid4()), committee_id),
                )
        assert (
            "sealed" in str(exc_info.value).lower()
            or "lock" in str(exc_info.value).lower()
        )

    def test_sealed_committee_blocks_decision_update(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        committee_id, _ = _setup_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        service.seal_committee_decision(committee_id, _seal_req(), db_conn)

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT decision_id FROM public.committee_decisions WHERE committee_id=%s",
                (committee_id,),
            )
            row = cur.fetchone()
        decision_id = str(row["decision_id"])

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.committee_decisions SET rationale='modif illicite' "
                    "WHERE decision_id=%s",
                    (decision_id,),
                )
        assert (
            "sealed" in str(exc_info.value).lower()
            or "lock" in str(exc_info.value).lower()
        )

    def test_double_seal_idempotent_via_snapshot_hash(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        """ON CONFLICT DO NOTHING sur (case_id, snapshot_hash) assure l'idempotence."""
        committee_id, case_id = _setup_sealable_committee(
            case_factory, committee_factory, db_conn
        )
        result1 = service.seal_committee_decision(committee_id, _seal_req(), db_conn)

        # Deuxième INSERT avec le même hash → DO NOTHING
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.decision_snapshots "
                "(case_id, committee_id, decision_at, zone, currency, "
                " alias_raw, supplier_name_raw, source_hashes, scoring_meta, snapshot_hash) "
                "VALUES (%s, %s, NOW(), 'Bamako', 'XOF', 'Rame', 'ETS KONATÉ', '{}', '{}', %s) "
                "ON CONFLICT (case_id, snapshot_hash) DO NOTHING",
                (case_id, committee_id, result1.snapshot_hash),
            )
        # Pas d'exception : idempotence garantie
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM public.decision_snapshots "
                "WHERE case_id=%s AND snapshot_hash=%s",
                (case_id, result1.snapshot_hash),
            )
            assert cur.fetchone()["cnt"] == 1
