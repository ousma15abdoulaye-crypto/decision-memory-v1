#!/usr/bin/env python3
"""Validation POST /committee/seal post-fix — workspace SEAL-TEST-FINAL-* (routes réelles W3)."""

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
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    text = raw.decode(errors="replace")
    try:
        body: object = json.loads(text)
    except json.JSONDecodeError:
        body = text
    return status, body, text


def _sql(sql: str) -> int:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_pg_sql.py"), "-c", sql],
        cwd=str(REPO_ROOT),
    ).returncode


def main() -> int:
    base = (
        (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BLOC4_API_BASE", ""))
        .strip()
        .rstrip("/")
    )
    if not base:
        print(
            "Usage: python scripts/bloc4_seal_validation_postfix.py <railway_base_url>",
            file=sys.stderr,
        )
        return 1

    suf = uuid.uuid4().hex[:8]
    ref = f"SEAL-TEST-FINAL-{suf}"
    pwd = "SealTestFinal123!"
    out: dict = {"reference_code": ref, "steps": []}

    chair = f"seal_chair_{suf}"
    members = [
        (f"seal_sc_{suf}", "supply_chain", True),
        (f"seal_fin_{suf}", "finance", True),
        (f"seal_tech_{suf}", "technical", False),
    ]
    all_users = [chair] + [m[0] for m in members]

    ids: dict[str, int] = {}
    for uname in all_users:
        st, body, raw = _req(
            base,
            "/auth/register",
            method="POST",
            data=json.dumps(
                {
                    "email": f"{uname}@example.com",
                    "username": uname,
                    "password": pwd,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        out["steps"].append({"register": uname, "http": st, "body": body})
        if st not in (200, 201):
            print(json.dumps(out, indent=2, ensure_ascii=False))
            print("RAW:", raw[:2000], file=sys.stderr)
            return 1
        if isinstance(body, dict) and "id" in body:
            ids[uname] = int(body["id"])

    chair_id = ids[chair]
    mid = [ids[m[0]] for m in members]

    tid = "0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe"
    rid = "0f2ea9f1-c5e7-4de9-853c-59dc6c7a89b9"
    _sql(
        f"INSERT INTO user_tenant_roles (id, user_id, tenant_id, role_id, granted_at) "
        f"VALUES (gen_random_uuid(), {chair_id}, '{tid}'::uuid, '{rid}'::uuid, NOW()) "
        f"ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING;"
    )

    import urllib.parse

    form = urllib.parse.urlencode({"username": chair, "password": pwd}).encode()
    st, body, raw = _req(
        base,
        "/auth/token",
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if st != 200:
        out["token_error"] = {"http": st, "raw": raw[:2000]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    token = body["access_token"]  # type: ignore[index]

    ws_payload = {
        "title": "Test seal final post-fix",
        "reference_code": ref,
        "process_type": "devis_simple",
        "humanitarian_context": "none",
    }
    st, body, raw = _req(
        base,
        "/api/workspaces",
        method="POST",
        data=json.dumps(ws_payload).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["create_workspace"] = {
        "http": st,
        "body": body,
        "raw_on_fail": raw if st not in (200, 201) else "",
    }
    if st not in (200, 201):
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    workspace_id = body["workspace_id"]  # type: ignore[index]
    out["workspace_id"] = workspace_id

    _sql(
        f"UPDATE process_workspaces SET status = 'analysis_complete', committee_required = TRUE "
        f"WHERE reference_code = '{ref}';"
    )

    st, body, raw = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/open-session",
        method="POST",
        data=json.dumps({"committee_type": "standard", "min_members": 3}).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["open_session"] = {"http": st, "body": body}
    if st != 201:
        out["open_session"]["raw"] = raw[:4000]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    session_id = body["session_id"]  # type: ignore[index]
    out["session_id"] = session_id

    for (uname_tpl, role, voting), uid in zip(members, mid):
        st, body, raw = _req(
            base,
            f"/api/workspaces/{workspace_id}/committee/add-member",
            method="POST",
            data=json.dumps(
                {"user_id": uid, "role_in_committee": role, "is_voting": voting}
            ).encode(),
            headers={"Content-Type": "application/json"},
            token=token,
        )
        out["steps"].append({"add_member": uname_tpl, "http": st, "body": body})
        if st != 200:
            out["steps"][-1]["raw"] = raw[:4000]
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 1

    st, body, raw = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/seal",
        method="POST",
        data=json.dumps({"seal_comment": "SEAL-TEST-FINAL post-fix"}).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["seal"] = {
        "http": st,
        "body": body,
        "response_text_full": raw if isinstance(body, str) else None,
    }
    if st not in (200, 201):
        out["seal"]["raw"] = raw

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if st in (200, 201) else 2


if __name__ == "__main__":
    raise SystemExit(main())
