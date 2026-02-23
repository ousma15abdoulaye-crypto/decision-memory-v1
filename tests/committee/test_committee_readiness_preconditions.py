"""T4 — Préconditions readiness/seal: validation avant scellement."""

import uuid

import pytest

from src.couche_a.committee import service
from src.couche_a.committee.models import (
    CommitteeStateError,
)

# ------------------------------------------------------------------ helpers


def _insert_decision(
    committee_id: str,
    case_id: str,
    rationale: str,
    supplier_id: str | None,
    status: str,
    db_conn,
) -> str:
    decision_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_decisions "
            "(decision_id, committee_id, case_id, selected_supplier_id, "
            " supplier_name_raw, decision_status, rationale) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                decision_id,
                committee_id,
                case_id,
                supplier_id,
                "Fournisseur Test" if supplier_id else None,
                status,
                rationale,
            ),
        )
    return decision_id


def _insert_voter(committee_id: str, db_conn) -> str:
    member_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_members "
            "(member_id, committee_id, user_ref, role, can_vote, status) "
            "VALUES (%s, %s, %s, 'member', true, 'active')",
            (member_id, committee_id, f"u-{uuid.uuid4().hex[:8]}"),
        )
    return member_id


# ------------------------------------------------------------------ T4 tests


class TestReadinessPreconditions:
    def test_rationale_trop_court_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        _insert_voter(committee_id, db_conn)
        _insert_decision(committee_id, case_id, "court", "sup-1", "proposed", db_conn)
        result = service.validate_readiness(committee_id, db_conn)
        assert not result["sealable"]
        assert any("rationale" in e.lower() or "20" in e for e in result["errors"])

    def test_no_decision_candidate_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        """Sans décision candidate, la readiness échoue."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        _insert_voter(committee_id, db_conn)
        # Pas de décision insérée → CommitteeStateError
        result = service.validate_readiness(committee_id, db_conn)
        assert not result["sealable"]
        assert len(result["errors"]) > 0

    def test_no_award_explicite_valide(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        _insert_voter(committee_id, db_conn)
        _insert_decision(
            committee_id,
            case_id,
            "Aucun fournisseur ne satisfait les critères requis pour ce dossier",
            None,
            "no_award",
            db_conn,
        )
        result = service.validate_readiness(committee_id, db_conn)
        assert result["sealable"] or all(
            "no_award" not in e.lower() for e in result["errors"]
        )

    def test_quorum_insuffisant_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        # Pas de membre votant actif
        _insert_decision(
            committee_id,
            case_id,
            "Rationale suffisamment longue pour passer la validation",
            "sup-1",
            "proposed",
            db_conn,
        )
        result = service.validate_readiness(committee_id, db_conn)
        assert not result["sealable"]
        assert any(
            "quorum" in e.lower() or "votant" in e.lower() for e in result["errors"]
        )

    def test_case_status_draft_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="draft")
        committee_id = committee_factory(case_id=case_id, status="open")
        _insert_voter(committee_id, db_conn)
        _insert_decision(
            committee_id,
            case_id,
            "Rationale valide et suffisamment longue pour le seal",
            "sup-1",
            "proposed",
            db_conn,
        )
        result = service.validate_readiness(committee_id, db_conn)
        assert not result["sealable"]
        assert any(
            "case" in e.lower() or "draft" in e.lower() for e in result["errors"]
        )

    def test_committee_status_sealed_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="sealed")
        with pytest.raises(CommitteeStateError):
            service._assert_committee_sealable(committee_id, db_conn)

    def test_committee_status_draft_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="draft")
        with pytest.raises(CommitteeStateError):
            service._assert_committee_sealable(committee_id, db_conn)

    def test_incoh_case_id_raises(self, db_conn, _tx, case_factory, committee_factory):
        case_id = case_factory(status="active")
        other_case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        _insert_voter(committee_id, db_conn)
        # Decision avec case_id différent
        _insert_decision(
            committee_id,
            other_case_id,
            "Rationale valide et suffisamment longue pour passer validation",
            "sup-1",
            "proposed",
            db_conn,
        )
        result = service.validate_readiness(committee_id, db_conn)
        assert not result["sealable"]
        assert any(
            "case_id" in e.lower() or "incohérence" in e.lower()
            for e in result["errors"]
        )
