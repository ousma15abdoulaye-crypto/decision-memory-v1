#!/usr/bin/env python3
"""BLOC 6 pilote SCI Mali — orchestration API + SQL lecture/écriture (Railway).

Réplique le chemin BLOC4 (RBAC SQL + transitions SQL documentées) et ajoute :
  - workspace référence pilote DAO-2026-MOPTI-017-* ;
  - POST source-package (multipart) ;
  - GET evaluation-frame + scan kill list sur la réponse JSON ;
  - GET /bundles ;
  - scellement + preuve irréversibilité (POST open-session → 409) ;
  - SQL lecture : pv_snapshot, committee_deliberation_events (append-only) ;
  - SQL lecture : vendor_market_signals post-seal (projection partielle ou 0 ligne).

Usage ::
  python scripts/bloc6_pilot_sci_mali_run.py https://<app>.up.railway.app

Prérequis : ``scripts/run_pg_sql.py`` avec RAILWAY_DATABASE_URL / DATABASE_URL
(.env.railway.local). Les écritures SQL hors API sont explicitement celles du
mandat BLOC4 (statuts comité) — à reporter dans BLOC6_PILOT_SCI_MALI_REPORT.md.
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

KILL_LIST_SUBSTRINGS = (
    '"winner"',
    '"rank"',
    '"recommendation"',
    '"best_offer"',
    '"selected_vendor"',
)


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
        with urllib.request.urlopen(r, timeout=120) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    try:
        body = json.loads(raw.decode())
    except json.JSONDecodeError:
        body = raw.decode(errors="replace")[:2000]
    return status, body


def _multipart_file(
    file_content: bytes,
    filename: str,
    doc_type: str,
) -> tuple[bytes, str]:
    boundary = f"----BLOC6Boundary{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode() + crlf)
    parts.append(b'Content-Disposition: form-data; name="doc_type"' + crlf + crlf)
    parts.append(doc_type.encode() + crlf)
    parts.append(f"--{boundary}".encode() + crlf)
    disp = f'Content-Disposition: form-data; name="file"; filename="{filename}"'
    parts.append(disp.encode() + crlf)
    parts.append(b"Content-Type: text/plain" + crlf + crlf)
    parts.append(file_content + crlf)
    parts.append(f"--{boundary}--".encode() + crlf)
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _sql_capture(sql: str) -> tuple[int, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_pg_sql.py"),
            "-c",
            sql,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


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


def _kill_list_clean(json_text: str) -> tuple[bool, list[str]]:
    hits = [s for s in KILL_LIST_SUBSTRINGS if s in json_text]
    return len(hits) == 0, hits


def main() -> int:
    base = (
        (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BLOC6_API_BASE", ""))
        .strip()
        .rstrip("/")
    )
    if not base:
        print(
            "Usage: python scripts/bloc6_pilot_sci_mali_run.py <base_url>\n"
            "  BLOC6_API_BASE=https://....up.railway.app",
            file=sys.stderr,
        )
        return 1

    suffix = uuid.uuid4().hex[:10]
    ref = f"DAO-2026-MOPTI-017-{suffix}"
    pwd = "Bloc6PilotMali123!"
    out: dict = {
        "base": base,
        "reference_code": ref,
        "pilot_label": "SCI Mali (tenant sci_mali — JWT défaut)",
        "steps": [],
    }

    chair_user = f"bloc6_chair_{suffix}"
    member_specs = [
        ("bloc6_sc1_{suffix}", "supply_chain", True),
        ("bloc6_sec_{suffix}", "secretary", True),
        ("bloc6_fin_{suffix}", "finance", True),
        ("bloc6_bh_{suffix}", "budget_holder", True),
        ("bloc6_tech_{suffix}", "technical", False),
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
        out["steps"].append({"register": uname, "status": st})
        if st not in (200, 201):
            print(json.dumps(out, indent=2, default=str))
            return 1
        ids[uname] = int(body["id"])

    chair_id = ids[chair_user]
    member_ids = [ids[name.format(suffix=suffix)] for name, _, _ in member_specs]
    out["chair_user_id"] = chair_id
    out["member_user_ids"] = dict(
        zip([m[0].format(suffix=suffix) for m in member_specs], member_ids)
    )

    # RBAC procurement_director + tenant sci_mali (aligné bloc4_committee_mandate_run.py)
    tid = "0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe"
    rid = "0f2ea9f1-c5e7-4de9-853c-59dc6c7a89b9"
    sql_rbac = f"""
    INSERT INTO user_tenant_roles (id, user_id, tenant_id, role_id, granted_at)
    VALUES (gen_random_uuid(), {chair_id}, '{tid}'::uuid, '{rid}'::uuid, NOW())
    ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING;
    """
    _sql(sql_rbac)
    out["steps"].append({"rbac_sql": "user_tenant_roles procurement_director"})

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
    out["steps"].append({"token": st})
    if st != 200:
        print(json.dumps(out, indent=2, default=str))
        return 1
    token = body["access_token"]

    # Create workspace
    ws_payload = {
        "title": "Pilote BLOC6 — DAO Mopti infrastructure (SCI Mali)",
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

    # Source package (O2)
    dao_text = (
        "DAO pilote BLOC6 — Mopti — document source minimal pour ingestion.\n"
        "Référence : DAO-2026-MOPTI-017 — usage test terrain contrôlé.\n"
    ).encode()
    mp_body, mp_ct = _multipart_file(dao_text, "dao_mopti_bloc6.txt", "dao")
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/source-package",
        method="POST",
        data=mp_body,
        headers={"Content-Type": mp_ct},
        token=token,
    )
    out["steps"].append({"source_package": st, "body": body})
    out["source_package_ok"] = st in (200, 201)

    # SQL: analysis_complete + committee_required (même famille que BLOC4)
    sql_ws = f"""
    UPDATE process_workspaces
    SET status = 'analysis_complete', committee_required = TRUE
    WHERE id = '{workspace_id}'::uuid;
    """
    _sql(sql_ws)
    out["steps"].append({"sql_workspace": "analysis_complete + committee_required"})

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
    for (uname_tpl, role, voting), uid in zip(member_specs, member_ids):
        uname = uname_tpl.format(suffix=suffix)
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
            {
                "add_member": uname,
                "status": st,
                "body": body if st != 200 else {"ok": True},
            }
        )
        if st != 200:
            print(json.dumps(out, indent=2, default=str))
            return 1

    sql_delib = f"""
    UPDATE process_workspaces
    SET status = 'in_deliberation', deliberation_started_at = NOW()
    WHERE id = '{workspace_id}'::uuid;
    """
    _sql(sql_delib)
    out["steps"].append({"sql_workspace": "in_deliberation (BLOC4-style)"})

    # Bundles + evaluation (Phase 3–4)
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/bundles",
        token=token,
    )
    out["steps"].append({"get_bundles": st})
    out["bundles_response"] = body
    bundle_count = 0
    if isinstance(body, dict) and isinstance(body.get("bundles"), list):
        bundle_count = len(body["bundles"])
    out["bundle_count"] = bundle_count

    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/evaluation-frame",
        token=token,
    )
    out["steps"].append({"evaluation_frame": st})
    ef_raw = json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    clean, hits = _kill_list_clean(ef_raw)
    out["evaluation_frame_kill_list_ok"] = clean
    out["evaluation_frame_kill_list_hits"] = hits
    out["evaluation_frame_sample"] = (
        body if isinstance(body, dict) else str(body)[:1500]
    )

    # Seal
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/seal",
        method="POST",
        data=json.dumps(
            {"seal_comment": "BLOC6 pilote SCI Mali — scellement mandat"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["steps"].append({"seal": st, "body": body})
    out["seal_response"] = body
    if st != 200:
        print(json.dumps(out, indent=2, default=str))
        return 1

    # Irréversibilité : deuxième open-session → 409
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/committee/open-session",
        method="POST",
        data=json.dumps({"committee_type": "standard", "min_members": 5}).encode(),
        headers={"Content-Type": "application/json"},
        token=token,
    )
    out["steps"].append({"open_session_after_seal": st, "body": body})
    out["irreversibility_open_session_409"] = st == 409

    # Post-seal evaluation-frame kill list (still clean)
    st, body = _req(
        base,
        f"/api/workspaces/{workspace_id}/evaluation-frame",
        token=token,
    )
    ef_raw2 = (
        json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    )
    clean2, hits2 = _kill_list_clean(ef_raw2)
    out["evaluation_frame_post_seal_kill_list_ok"] = clean2
    out["evaluation_frame_post_seal_hits"] = hits2

    # SQL proofs : pv_snapshot + events count + signals
    pv_sql = f"""
    SELECT seal_hash,
           LENGTH(pv_snapshot::text) AS pv_snapshot_len,
           LEFT(pv_snapshot::text, 120) AS pv_preview
    FROM committee_sessions
    WHERE workspace_id = '{workspace_id}'::uuid;
    """
    rc_pv, pv_out = _sql_capture(pv_sql)
    out["sql_pv_snapshot_rc"] = rc_pv
    out["sql_pv_snapshot"] = pv_out[-800:] if pv_out else ""

    ev_sql = f"""
    SELECT event_type, COUNT(*) AS n
    FROM committee_deliberation_events
    WHERE workspace_id = '{workspace_id}'::uuid
    GROUP BY event_type
    ORDER BY event_type;
    """
    rc_ev, ev_out = _sql_capture(ev_sql)
    out["sql_cde_events_rc"] = rc_ev
    out["sql_cde_events"] = ev_out[-800:] if ev_out else ""

    sig_sql = f"""
    SELECT COUNT(*) AS n
    FROM vendor_market_signals
    WHERE source_workspace_id = '{workspace_id}'::uuid;
    """
    rc_sg, sg_out = _sql_capture(sig_sql)
    out["sql_vendor_signals_rc"] = rc_sg
    out["sql_vendor_signals"] = sg_out[-400:] if sg_out else ""

    out["phase7_note"] = (
        "Projection ARQ : enqueue côté serveur si REDIS_URL défini ; "
        "sinon warning logs — voir committee_sessions._enqueue_project_sealed_workspace_job."
    )

    print(json.dumps(out, indent=2, default=str))
    out_path = REPO_ROOT / "data" / "annotations" / f"bloc6_pilot_run_{suffix}.json"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"\n# Wrote {out_path}", file=sys.stderr)
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
