"""Test database-level triggers for extraction_corrections append-only."""

import json
import uuid

import psycopg
import pytest


@pytest.fixture
def setup_trigger_test_data(db_conn):
    cur = db_conn.cursor()
    case_id = f"trig-{uuid.uuid4().hex[:12]}"
    offer_id = f"offer-{uuid.uuid4().hex[:12]}"
    doc_id = str(uuid.uuid4())
    ext_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            f"trigger_{uuid.uuid4().hex[:8]}@test.com",
            f"triguser_{uuid.uuid4().hex[:8]}",
            "hash",
            "Test",
            True,
            False,
            1,
            "2026-02-21",
        ),
    )
    row = cur.fetchone()
    user_id = str(row["id"])
    cur.execute(
        "INSERT INTO cases (id, case_type, title, created_at, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (case_id, "TRIG_TEST", "Fixture triggers", "2026-02-21", "active"),
    )
    cur.execute(
        "INSERT INTO offers (id, case_id, supplier_name, offer_type, submitted_at, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (offer_id, case_id, "Test", "technical", "2026-02-21", "2026-02-21"),
    )
    cur.execute(
        "INSERT INTO documents (id, case_id, offer_id, filename, path, uploaded_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            doc_id,
            case_id,
            offer_id,
            "trigger_test.pdf",
            "/tmp/trigger.pdf",
            "2026-02-21",
        ),
    )
    cur.execute(
        "INSERT INTO extractions (id, case_id, document_id, structured_data, confidence_score, data_json, extraction_type, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            ext_id,
            case_id,
            doc_id,
            json.dumps({"trigger": "test"}),
            0.7,
            "{}",
            "native_pdf",
            "2026-02-21",
        ),
    )
    db_conn.commit()
    return user_id, ext_id


def test_trigger_enforce_corrections_append_only_blocks_update(
    db_conn, setup_trigger_test_data
):
    cur = db_conn.cursor()
    user_id, ext_id = setup_trigger_test_data
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"status": "draft"}), user_id),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute(
            "UPDATE extraction_corrections SET structured_data = %s WHERE id = %s",
            (json.dumps({"status": "published"}), cor_id),
        )
        db_conn.commit()
    error_msg = str(exc_info.value).lower()
    assert "append-only" in error_msg or "inv-6" in error_msg
    db_conn.rollback()


def test_trigger_enforce_corrections_append_only_blocks_delete(
    db_conn, setup_trigger_test_data
):
    cur = db_conn.cursor()
    user_id, ext_id = setup_trigger_test_data
    cor_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO extraction_corrections (id, extraction_id, structured_data, corrected_by) VALUES (%s, %s, %s, %s)",
        (cor_id, ext_id, json.dumps({"status": "draft"}), user_id),
    )
    db_conn.commit()
    with pytest.raises(psycopg.Error) as exc_info:
        cur.execute("DELETE FROM extraction_corrections WHERE id = %s", (cor_id,))
        db_conn.commit()
    error_msg = str(exc_info.value).lower()
    assert "append-only" in error_msg or "inv-6" in error_msg
    db_conn.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Committee Lock Trigger (M-COMMITTEE-CORE #9)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def committee_trigger_data(db_conn):
    """Crée case + committee + membre + décision candidate.

    Retourne (committee_id, case_id, member_id, decision_id).
    Nettoyage : DELETE seulement sur tables non-append-only.
    """
    from datetime import UTC, datetime

    case_id = f"trig-comm-{uuid.uuid4().hex[:10]}"
    committee_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    decision_id = str(uuid.uuid4())

    cur = db_conn.cursor()
    # case
    cur.execute(
        "INSERT INTO public.cases (id, case_type, title, created_at, status, currency) "
        "VALUES (%s, 'TEST', 'Trigger comité', %s, 'active', 'XOF') ON CONFLICT DO NOTHING",
        (case_id, datetime.now(UTC).isoformat()),
    )
    # committee
    cur.execute(
        "INSERT INTO public.committees "
        "(committee_id, case_id, org_id, committee_type, created_by, status) "
        "VALUES (%s, %s, 'org-trig', 'achat', 'test-trig', 'open')",
        (committee_id, case_id),
    )
    cur.execute(
        "INSERT INTO public.committee_events "
        "(committee_id, event_type, payload, created_by) "
        "VALUES (%s, 'committee_created', '{}', 'test-trig')",
        (committee_id,),
    )
    # membre votant actif
    cur.execute(
        "INSERT INTO public.committee_members "
        "(member_id, committee_id, user_ref, role, can_vote, status) "
        "VALUES (%s, %s, 'voter-trig', 'member', true, 'active')",
        (member_id, committee_id),
    )
    # décision candidate
    cur.execute(
        "INSERT INTO public.committee_decisions "
        "(decision_id, committee_id, case_id, selected_supplier_id, "
        " supplier_name_raw, decision_status, rationale) "
        "VALUES (%s, %s, %s, 'sup-trig', 'ETS TRIG', 'proposed', %s)",
        (
            decision_id,
            committee_id,
            case_id,
            "Rationale suffisamment longue pour passer la validation requise du seal",
        ),
    )
    db_conn.commit()
    yield committee_id, case_id, member_id, decision_id

    # Cleanup (order important: FK)
    try:
        cur2 = db_conn.cursor()
        cur2.execute(
            "DELETE FROM public.committee_members WHERE committee_id=%s",
            (committee_id,),
        )
        cur2.execute(
            "DELETE FROM public.committee_decisions WHERE committee_id=%s",
            (committee_id,),
        )
        cur2.execute(
            "DELETE FROM public.committees WHERE committee_id=%s", (committee_id,)
        )
        cur2.execute("DELETE FROM public.cases WHERE id=%s", (case_id,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()


class TestCommitteeLockTrigger:
    def test_trigger_allows_member_insert_before_seal(
        self, db_conn, committee_trigger_data
    ):
        """INSERT membre autorisé avant seal."""
        committee_id, *_ = committee_trigger_data
        new_member_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.committee_members "
                "(member_id, committee_id, user_ref, role) "
                "VALUES (%s, %s, 'pre-seal-user', 'observer')",
                (new_member_id, committee_id),
            )
        db_conn.commit()
        # Cleanup
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.committee_members WHERE member_id=%s",
                (new_member_id,),
            )
        db_conn.commit()

    def test_trigger_blocks_member_insert_after_seal(
        self, db_conn, committee_trigger_data
    ):
        """INSERT membre bloqué après seal (DB-level)."""
        committee_id, *_ = committee_trigger_data
        # Sceller le comité directement (bypass service pour isoler le trigger)
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.committees SET status='sealed' WHERE committee_id=%s",
                (committee_id,),
            )
        db_conn.commit()

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO public.committee_members "
                    "(member_id, committee_id, user_ref, role) "
                    "VALUES (%s, %s, 'post-seal-intrus', 'observer')",
                    (str(uuid.uuid4()), committee_id),
                )
            db_conn.commit()
        assert (
            "sealed" in str(exc_info.value).lower()
            or "lock" in str(exc_info.value).lower()
        )
        db_conn.rollback()

    def test_trigger_allows_decision_seal_transition_update(
        self, db_conn, committee_trigger_data
    ):
        """UPDATE de sealing sur committee_decisions autorisé même après seal (PATCH-1)."""
        committee_id, case_id, _, decision_id = committee_trigger_data
        seal_id = str(uuid.uuid4())
        from datetime import UTC, datetime

        # Sceller le comité (arme le verrou)
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.committees SET status='sealed' WHERE committee_id=%s",
                (committee_id,),
            )
        db_conn.commit()

        # UPDATE de sealing sur committee_decisions → doit passer
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.committee_decisions "
                "SET decision_status='sealed', sealed_by='alice', "
                "    seal_id=%s, decision_at=%s "
                "WHERE decision_id=%s",
                (seal_id, datetime.now(UTC), decision_id),
            )
        db_conn.commit()  # Ne doit pas lever

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT decision_status FROM public.committee_decisions WHERE decision_id=%s",
                (decision_id,),
            )
            assert cur.fetchone()["decision_status"] == "sealed"

    def test_trigger_blocks_decision_update_after_seal(
        self, db_conn, committee_trigger_data
    ):
        """UPDATE non-sealing sur committee_decisions bloqué après seal (DB-level)."""
        committee_id, _, __, decision_id = committee_trigger_data
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.committees SET status='sealed' WHERE committee_id=%s",
                (committee_id,),
            )
        db_conn.commit()

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.committee_decisions SET rationale='modif illicite' "
                    "WHERE decision_id=%s",
                    (decision_id,),
                )
            db_conn.commit()
        assert (
            "sealed" in str(exc_info.value).lower()
            or "lock" in str(exc_info.value).lower()
        )
        db_conn.rollback()

    def test_trigger_blocks_committee_unlock_from_sealed(
        self, db_conn, committee_trigger_data
    ):
        """Transition sealed→open bloquée au niveau DB (PATCH-5)."""
        committee_id, *_ = committee_trigger_data
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE public.committees SET status='sealed' WHERE committee_id=%s",
                (committee_id,),
            )
        db_conn.commit()

        with pytest.raises(psycopg.Error) as exc_info:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.committees SET status='open' WHERE committee_id=%s",
                    (committee_id,),
                )
            db_conn.commit()
        msg = str(exc_info.value).lower()
        assert "terminal-status" in msg or "sealed" in msg
        db_conn.rollback()
