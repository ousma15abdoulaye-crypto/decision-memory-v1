#!/usr/bin/env python3
"""BLOC 4 mandat — orchestration API + SQL (Railway / prod-like).

Usage ::
  python scripts/bloc4_committee_mandate_run.py https://<app>.up.railway.app

Prérequis : variables DB pour ``scripts/run_pg_sql.py`` (RAILWAY_DATABASE_URL) ;
RBAC ``procurement_director`` injecté par SQL pour le comité « chair » après register.

Ne modifie pas le schéma ; idempotent partiel (reference_code unique par run).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.local", override=True)
    load_dotenv(REPO_ROOT / ".env.railway.local", override=True)
except ImportError:
    pass


def _req(
    base: str,
    path: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    token: str | None = None,
):
    import urllib.error
    import urllib.request

    url = f"{base.rstrip('/')}{path}"
    h = dict(headers or {})
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        r = urllib.request.Request(url, data=data, method=method)
        for k, v in h.items():
            r.add_header(k, v)
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    try:
        body = json.loads(raw.decode())
    except json.JSONDecodeError:
        body = raw.decode(errors="replace")[:500]
    return status, body


def _sql(sql: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_pg_sql.py"),
            "-c",
            sql,
        ],
        check=False,
        cwd=str(REPO_ROOT),
    )


def main() -> int:
    base = (
        (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BLOC4_API_BASE", ""))
        .strip()
        .rstrip("/")
    )
    if not base:
        print(
            "Usage: python scripts/bloc4_committee_mandate_run.py <base_url>\n"
            "  BLOC4_API_BASE=https://....up.railway.app",
            file=sys.stderr,
        )
        return 1

    suffix = uuid.uuid4().hex[:10]
    ref = f"PILOT-COMITE-001-{suffix}"
    pwd = "Bloc4MandateTest123!"
    out: dict = {"base": base, "reference_code": ref, "steps": []}

    # --- Register chair + 5 members (distinct user_ids) ---
    chair_user = f"bloc4_chair_{suffix}"
    member_specs = [
        ("bloc4_sc1_{suffix}", "supply_chain", True),
        ("bloc4_sec_{suffix}", "secretary", True),
        ("bloc4_fin_{suffix}", "finance", True),
        ("bloc4_bh_{suffix}", "budget_holder", True),
        ("bloc4_tech_{suffix}", "technical", False),
    ]
    users_to_reg = [(chair_user, pwd)] + [
        (name.format(suffix=suffix), pwd) for name, _, _ in member_specs
    ]

    ids: dict[str, int] = {}
    for uname, pw in users_to_reg:
        st, body = _req(
            base,
            "/auth/register",
            method="POST",
            data=json.dumps(
                {
                    "email": f"{uname}@example.com",
                    "username": uname,
                    "password": pw,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        out["steps"].append({"register": uname, "status": st, "body": body})
        if st not in (200, 201):
            print(json.dumps(out, indent=2, default=str))
            return 1
        ids[uname] = int(body["id"])

    chair_id = ids[chair_user]
    member_ids = [ids[name.format(suffix=suffix)] for name, _, _ in member_specs]

    # RBAC procurement_director + tenant sci_mali
    tid = "0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe"
    rid = "0f2ea9f1-c5e7-4de9-853c-59dc6c7a89b9"  # procurement_director
    sql_rbac = f"""
    INSERT INTO user_tenant_roles (id, user_id, tenant_id, role_id, granted_at)
    VALUES (gen_random_uuid(), {chair_id}, '{tid}'::uuid, '{rid}'::uuid, NOW())
    ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING;
    """
    _sql(sql_rbac)
    out["chair_user_id"] = chair_id
    out["member_user_ids"] = dict(
        zip([m[0].format(suffix=suffix) for m in member_specs], member_ids)
    )

    # Token chair
    import urllib.parse

    form = urllib.parse.urlencode({"username": chair_user, "password": pwd}).encode()
    st, body = _req(
        base,
        "/auth/token",
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    out["steps"].append(
        {"token": st, "body": body if st != 200 else {"token_type": "bearer"}}
    )
    if st != 200:
        print(json.dumps(out, indent=2, default=str))
        return 1
    token = body["access_token"]

    # Create workspace
    ws_payload = {
        "title": "Test comité BLOC 4 — DAO Construction École",
        "reference_code": ref,
        "process_type": "appel_offres_ouvert",
        "humanitarian_context": "cat2",
    }
    st, body = _req(
        base,
        "/api/workspaces",
        method="POST",
        data=json.dumps(ws_payload).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["steps"].append({"create_workspace": st, "body": body})
    if st not in (200, 201):
        print(json.dumps(out, indent=2, default=str))
        return 1
    workspace_id = body["workspace_id"]
    out["workspace_id"] = workspace_id

    # SQL: analysis_complete + committee_required
    sql_ws = f"""
    UPDATE process_workspaces
    SET status = 'analysis_complete', committee_required = TRUE
    WHERE id = '{workspace_id}'::uuid;
    """
    _sql(sql_ws)

    # Open committee session
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/open-session",
        method="POST",
        data=json.dumps({"committee_type": "standard", "min_members": 5}).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["steps"].append({"open_session": st, "body": body})
    if st != 201:
        print(json.dumps(out, indent=2, default=str))
        return 1
    session_id = body.get("session_id")
    out["session_id"] = session_id

    # Add 5 members
    for (uname_tpl, role, voting), uid in zip(
        [m for m in member_specs],
        member_ids,
    ):
        st, body = _req(
            base,
            f"/api/workspaces/{workspace_id}/committee/add-member",
            method="POST",
            data=json.dumps(
                {"user_id": uid, "role_in_committee": role, "is_voting": voting}
            ).encode(),
            headers={"Content-Type": "application/json"},
            token=token,
        )
        out["steps"].append(
            {"add_member": uname_tpl.format(suffix=suffix), "status": st, "body": body}
        )
        if st != 200:
            print(json.dumps(out, indent=2, default=str))
            return 1

    # Seal
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/seal",
        method="POST",
        data=json.dumps({"seal_comment": "BLOC4 mandat run"}).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["steps"].append({"seal": st, "body": body})
    out["seal_response"] = body

    print(json.dumps(out, indent=2, default=str))
    return 0 if st == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
