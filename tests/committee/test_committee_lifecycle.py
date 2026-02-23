"""T3 — Cycle de vie committee: transitions d'état, membres, annulation."""

import uuid

import psycopg
import pytest

from src.couche_a.committee import service
from src.couche_a.committee.models import (
    AddMemberRequest,
    CommitteeStateError,
    CreateCommitteeRequest,
)

# ------------------------------------------------------------------ helpers locaux


def _add_voter(committee_id: str, db_conn) -> str:
    req = AddMemberRequest(
        user_ref=f"u-{uuid.uuid4().hex[:8]}",
        role="member",
        can_vote=True,
        status="active",
    )
    with db_conn.cursor() as cur:
        member_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO public.committee_members "
            "(member_id, committee_id, user_ref, role, can_vote, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (member_id, committee_id, req.user_ref, req.role, True, "active"),
        )
        cur.execute(
            "INSERT INTO public.committee_events (committee_id, event_type, payload, created_by) "
            "VALUES (%s, 'member_added', '{}', 'test-user')",
            (committee_id,),
        )
    return member_id


# ------------------------------------------------------------------ T3 tests


class TestCommitteeLifecycle:
    def test_create_committee_draft(self, db_conn, _tx, case_factory):
        case_id = case_factory(status="active")
        req = CreateCommitteeRequest(
            case_id=case_id, org_id="org1", committee_type="achat", created_by="alice"
        )
        committee_id = service.create_committee(req, db_conn)
        c = service.get_committee(committee_id, db_conn)
        assert c["status"] == "draft"
        assert c["case_id"] == case_id

    def test_open_session_from_draft(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        service.open_session(committee_id, "alice", db_conn)
        c = service.get_committee(committee_id, db_conn)
        assert c["status"] == "open"

    def test_open_session_from_non_draft_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        with pytest.raises(CommitteeStateError):
            service.open_session(committee_id, "alice", db_conn)

    def test_set_in_review_from_open(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        service.set_in_review(committee_id, "alice", db_conn)
        c = service.get_committee(committee_id, db_conn)
        assert c["status"] == "in_review"

    def test_add_member_in_draft(self, db_conn, _tx, case_factory, committee_factory):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        req = AddMemberRequest(user_ref="bob", role="member", can_vote=True)
        member_id = service.add_member(committee_id, req, "alice", db_conn)
        members = service.list_members(committee_id, db_conn)
        assert any(str(m["member_id"]) == member_id for m in members)

    def test_add_member_in_open(self, db_conn, _tx, case_factory, committee_factory):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        req = AddMemberRequest(user_ref="carol", role="chair", can_vote=True)
        member_id = service.add_member(committee_id, req, "alice", db_conn)
        assert member_id is not None

    def test_add_member_in_review_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="in_review")
        req = AddMemberRequest(user_ref="dan", role="member")
        with pytest.raises(CommitteeStateError):
            service.add_member(committee_id, req, "alice", db_conn)

    def test_remove_member_in_draft(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        req = AddMemberRequest(user_ref="eve", role="member")
        member_id = service.add_member(committee_id, req, "alice", db_conn)
        service.remove_member(committee_id, member_id, "alice", db_conn)
        members = service.list_members(committee_id, db_conn)
        assert not any(str(m["member_id"]) == member_id for m in members)

    def test_remove_member_after_open_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="open")
        _add_voter(committee_id, db_conn)
        members = service.list_members(committee_id, db_conn)
        m_id = str(members[0]["member_id"])
        with pytest.raises(CommitteeStateError):
            service.remove_member(committee_id, m_id, "alice", db_conn)

    def test_cancel_from_draft(self, db_conn, _tx, case_factory, committee_factory):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        service.cancel_committee(committee_id, "test cancel", "alice", db_conn)
        c = service.get_committee(committee_id, db_conn)
        assert c["status"] == "cancelled"

    def test_cancel_from_sealed_raises(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="sealed")
        with pytest.raises(CommitteeStateError):
            service.cancel_committee(committee_id, "illegal", "alice", db_conn)

    def test_sealed_to_open_transition_blocked_db_level(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        """DB-level: transition sealed→open doit lever une exception."""
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id, status="sealed")
        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.committees SET status='open' WHERE committee_id=%s",
                    (committee_id,),
                )
        assert (
            "terminal-status" in str(exc_info.value).lower()
            or "sealed" in str(exc_info.value).lower()
        )

    def test_events_appended_on_lifecycle(
        self, db_conn, _tx, case_factory, committee_factory
    ):
        case_id = case_factory(status="active")
        committee_id = committee_factory(case_id=case_id)
        service.open_session(committee_id, "alice", db_conn)
        events = service.get_events(committee_id, db_conn)
        event_types = [e["event_type"] for e in events]
        assert "committee_created" in event_types
        assert "meeting_opened" in event_types
