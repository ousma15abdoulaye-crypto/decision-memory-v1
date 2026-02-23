# src/couche_a/committee/service.py
# Logique métier comité — Couche A strictement (zéro HTTP, zéro Couche B).
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .models import (
    AddMemberRequest,
    CommitteeNotFoundError,
    CommitteeStateError,
    CommitteeValidationError,
    CreateCommitteeRequest,
    SealRequest,
    SealResult,
    SetDecisionRequest,
)
from .snapshot import assert_no_forbidden_fields, compute_snapshot_hash

# ------------------------------------------------------------------ helpers internes


def _now() -> datetime:
    return datetime.now(UTC)


def _get_committee_or_raise(committee_id: str, conn) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.committees WHERE committee_id = %s",
            (committee_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise CommitteeNotFoundError(f"committee {committee_id} introuvable")
    return dict(row)


def _get_case_or_raise(case_id: str, conn) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status FROM public.cases WHERE id = %s",
            (case_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise CommitteeStateError(f"case {case_id} introuvable")
    return dict(row)


def _get_decision_candidate_or_raise(committee_id: str, conn) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.committee_decisions "
            "WHERE committee_id = %s AND decision_status NOT IN ('rejected') "
            "ORDER BY created_at DESC LIMIT 1",
            (committee_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise CommitteeStateError(
            f"Aucune décision candidate pour committee {committee_id}"
        )
    return dict(row)


def _count_active_voters(committee_id: str, conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM public.committee_members "
            "WHERE committee_id = %s AND can_vote = true AND status IN ('active','signed')",
            (committee_id,),
        )
        return cur.fetchone()["cnt"]


def _get_mandatory_absent_members(committee_id: str, conn) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_ref FROM public.committee_members "
            "WHERE committee_id = %s AND is_mandatory = true "
            "  AND status NOT IN ('active','signed')",
            (committee_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def _insert_event(
    conn,
    committee_id: str,
    event_type: str,
    payload: dict[str, Any],
    created_by: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_events "
            "(committee_id, event_type, payload, created_by) "
            "VALUES (%s, %s, %s::jsonb, %s)",
            (committee_id, event_type, json.dumps(payload), created_by),
        )


# ------------------------------------------------------------------ préconditions seal


def _assert_committee_sealable(committee_id: str, conn) -> None:
    committee = _get_committee_or_raise(committee_id, conn)

    if committee["status"] not in ("open", "in_review"):
        raise CommitteeStateError(
            f"Seal impossible: committee.status='{committee['status']}' "
            "requis: open|in_review"
        )

    case = _get_case_or_raise(committee["case_id"], conn)
    if case["status"] in ("draft", "cancelled"):
        raise CommitteeStateError(f"Seal impossible: case.status='{case['status']}'")

    decision = _get_decision_candidate_or_raise(committee_id, conn)

    if not decision["rationale"] or len(decision["rationale"].strip()) < 20:
        raise CommitteeValidationError("Rationale insuffisant: minimum 20 caractères")

    if (
        decision["selected_supplier_id"] is None
        and decision["decision_status"] != "no_award"
    ):
        raise CommitteeValidationError(
            "Supplier absent et decision_status != 'no_award'"
        )

    if decision["case_id"] != committee["case_id"]:
        raise CommitteeValidationError(
            f"Incohérence case_id: committee={committee['case_id']} "
            f"decision={decision['case_id']}"
        )

    active_voters = _count_active_voters(committee_id, conn)
    if active_voters < 1:
        raise CommitteeValidationError(
            f"Quorum non atteint: {active_voters} votant(s) actif(s)"
        )

    mandatory_absent = _get_mandatory_absent_members(committee_id, conn)
    if mandatory_absent:
        names = [m["user_ref"] for m in mandatory_absent]
        raise CommitteeValidationError(
            f"Membres obligatoires absents/non signés: {names}"
        )


# ------------------------------------------------------------------ API publique service


def create_committee(req: CreateCommitteeRequest, conn) -> str:
    """Crée un comité draft, retourne committee_id."""
    if req.committee_type not in ("achat", "technique", "mixte"):
        raise CommitteeValidationError(f"committee_type invalide: {req.committee_type}")
    committee_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committees "
            "(committee_id, case_id, org_id, committee_type, created_by) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                committee_id,
                req.case_id,
                req.org_id,
                req.committee_type,
                req.created_by,
            ),
        )
    _insert_event(conn, committee_id, "committee_created", {}, req.created_by)
    return committee_id


def get_committee(committee_id: str, conn) -> dict[str, Any]:
    return _get_committee_or_raise(committee_id, conn)


def open_session(committee_id: str, by: str, conn) -> None:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] != "draft":
        raise CommitteeStateError(
            f"open_session: statut requis draft, actuel {committee['status']}"
        )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.committees SET status='open' WHERE committee_id=%s",
            (committee_id,),
        )
    _insert_event(conn, committee_id, "meeting_opened", {}, by)


def set_in_review(committee_id: str, by: str, conn) -> None:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] != "open":
        raise CommitteeStateError(
            f"set_in_review: statut requis open, actuel {committee['status']}"
        )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.committees SET status='in_review' WHERE committee_id=%s",
            (committee_id,),
        )
    _insert_event(conn, committee_id, "recommendation_set", {}, by)


def add_member(committee_id: str, req: AddMemberRequest, by: str, conn) -> str:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] not in ("draft", "open"):
        raise CommitteeStateError(f"add_member interdit: statut {committee['status']}")
    if req.role not in ("chair", "member", "secretary", "observer", "approver"):
        raise CommitteeValidationError(f"role invalide: {req.role}")
    member_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_members "
            "(member_id, committee_id, user_ref, role, can_vote, can_seal, "
            " can_edit_minutes, is_mandatory, quorum_counted) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                member_id,
                committee_id,
                req.user_ref,
                req.role,
                req.can_vote,
                req.can_seal,
                req.can_edit_minutes,
                req.is_mandatory,
                req.quorum_counted,
            ),
        )
    _insert_event(
        conn,
        committee_id,
        "member_added",
        {"user_ref": req.user_ref, "role": req.role},
        by,
    )
    return member_id


def remove_member(committee_id: str, member_id: str, by: str, conn) -> None:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] != "draft":
        raise CommitteeStateError(
            f"remove_member: uniquement en draft, actuel {committee['status']}"
        )
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM public.committee_members "
            "WHERE member_id=%s AND committee_id=%s",
            (member_id, committee_id),
        )
    _insert_event(
        conn,
        committee_id,
        "member_removed",
        {"member_id": member_id},
        by,
    )


def list_members(committee_id: str, conn) -> list[dict[str, Any]]:
    _get_committee_or_raise(committee_id, conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.committee_members WHERE committee_id=%s "
            "ORDER BY joined_at",
            (committee_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def set_decision_candidate(
    committee_id: str, req: SetDecisionRequest, by: str, conn
) -> str:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] not in ("draft", "open", "in_review"):
        raise CommitteeStateError(
            f"set_decision: interdit en statut {committee['status']}"
        )
    decision_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.committee_decisions "
            "(decision_id, committee_id, case_id, selected_supplier_id, "
            " supplier_name_raw, decision_status, rationale) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                decision_id,
                committee_id,
                req.case_id,
                req.selected_supplier_id,
                req.supplier_name_raw,
                req.decision_status,
                req.rationale,
            ),
        )
    return decision_id


def validate_readiness(committee_id: str, conn) -> dict[str, Any]:
    """Dry-run des préconditions de seal. Ne modifie rien."""
    errors: list[str] = []
    try:
        _assert_committee_sealable(committee_id, conn)
    except (CommitteeStateError, CommitteeValidationError) as exc:
        errors.append(str(exc))
    return {"sealable": len(errors) == 0, "errors": errors}


def seal_committee_decision(committee_id: str, req: SealRequest, conn) -> SealResult:
    """Transaction unique — tout ou rien.

    Ordre canonique (PATCH-1) :
    1. Préconditions
    2. committees.status = 'sealed'  (arme le verrou DB)
    3. committee_decisions.decision_status = 'sealed' (autorisé par trigger intelligent)
    4. Build snapshot + hash + neutralité
    5. INSERT decision_snapshots (idempotence ON CONFLICT DO NOTHING)
    6. Events append-only
    """
    _assert_committee_sealable(committee_id, conn)

    committee = _get_committee_or_raise(committee_id, conn)
    decision = _get_decision_candidate_or_raise(committee_id, conn)

    seal_id = str(uuid.uuid4())
    now = _now()

    # 2) Armer le verrou terminal
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.committees "
            "SET status='sealed', sealed_at=%s, sealed_by=%s "
            "WHERE committee_id=%s",
            (now, req.sealed_by, committee_id),
        )

    # 3) Seal décision (autorisé par enforce_committee_lock via transition)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.committee_decisions "
            "SET decision_status='sealed', sealed_by=%s, seal_id=%s, decision_at=%s "
            "WHERE decision_id=%s",
            (req.sealed_by, seal_id, now, decision["decision_id"]),
        )

    # 4) Build snapshot
    snapshot: dict[str, Any] = {
        "case_id": committee["case_id"],
        "committee_id": committee_id,
        "committee_seal_id": seal_id,
        "decision_at": now,
        "zone": req.zone,
        "currency": req.currency,
        "item_id": req.item_id,
        "alias_raw": req.alias_raw,
        "quantity": req.quantity,
        "unit": req.unit,
        "price_paid": req.price_paid,
        "supplier_id": req.supplier_id,
        "supplier_name_raw": (decision["supplier_name_raw"] or req.alias_raw),
        "source_hashes": req.source_hashes,
        "scoring_meta": req.scoring_meta,
    }
    assert_no_forbidden_fields(snapshot)
    snapshot["snapshot_hash"] = compute_snapshot_hash(snapshot)

    # 5) Insert snapshot idempotent
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.decision_snapshots "
            "(case_id, committee_id, committee_seal_id, decision_at, "
            " zone, currency, item_id, alias_raw, quantity, unit, price_paid, "
            " supplier_id, supplier_name_raw, source_hashes, scoring_meta, snapshot_hash) "
            "VALUES "
            "(%(case_id)s, %(committee_id)s, %(committee_seal_id)s, %(decision_at)s, "
            " %(zone)s, %(currency)s, %(item_id)s, %(alias_raw)s, %(quantity)s, %(unit)s, %(price_paid)s, "
            " %(supplier_id)s, %(supplier_name_raw)s, %(source_hashes)s, %(scoring_meta)s, %(snapshot_hash)s) "
            "ON CONFLICT (case_id, snapshot_hash) DO NOTHING",
            {
                "case_id": snapshot["case_id"],
                "committee_id": snapshot["committee_id"],
                "committee_seal_id": str(snapshot["committee_seal_id"]),
                "decision_at": snapshot["decision_at"],
                "zone": snapshot["zone"],
                "currency": snapshot["currency"],
                "item_id": snapshot["item_id"],
                "alias_raw": snapshot["alias_raw"],
                "quantity": snapshot["quantity"],
                "unit": snapshot["unit"],
                "price_paid": snapshot["price_paid"],
                "supplier_id": snapshot["supplier_id"],
                "supplier_name_raw": snapshot["supplier_name_raw"],
                "source_hashes": json.dumps(req.source_hashes),
                "scoring_meta": json.dumps(req.scoring_meta),
                "snapshot_hash": snapshot["snapshot_hash"],
            },
        )

    # 6) Events
    _insert_event(
        conn, committee_id, "seal_completed", {"seal_id": seal_id}, req.sealed_by
    )
    _insert_event(
        conn,
        committee_id,
        "snapshot_emitted",
        {"snapshot_hash": snapshot["snapshot_hash"]},
        req.sealed_by,
    )

    return SealResult(
        seal_id=seal_id,
        snapshot_hash=snapshot["snapshot_hash"],
    )


def cancel_committee(committee_id: str, reason: str, by: str, conn) -> None:
    committee = _get_committee_or_raise(committee_id, conn)
    if committee["status"] == "sealed":
        raise CommitteeStateError("cancel interdit: comité déjà scellé")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.committees "
            "SET status='cancelled', cancelled_reason=%s "
            "WHERE committee_id=%s",
            (reason, committee_id),
        )
    _insert_event(conn, committee_id, "committee_cancelled", {"reason": reason}, by)


def get_events(committee_id: str, conn) -> list[dict[str, Any]]:
    _get_committee_or_raise(committee_id, conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.committee_events WHERE committee_id=%s "
            "ORDER BY created_at",
            (committee_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_decision_snapshot(committee_id: str, conn) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.decision_snapshots "
            "WHERE committee_id=%s ORDER BY created_at DESC LIMIT 1",
            (committee_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None
