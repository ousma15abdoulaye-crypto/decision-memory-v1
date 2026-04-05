#!/usr/bin/env python3
"""Smoke BLOC 3 — API Railway réelle (auth + workspaces + market + committee).

Usage :
  python scripts/bloc3_smoke_railway.py https://<app>.up.railway.app

Variables optionnelles :
  BLOC3_API_BASE — même rôle que l'argument (priorité à l'argument).

Comportement :
  - Crée un utilisateur dédié via POST /auth/register (identifiable smoke-test).
  - POST /auth/token (form-urlencoded, pas JSON).
  - POST /api/workspaces (reference_code unique SMOKE-BLOC3-<suffixe>).
  - GET /api/market/overview
  - GET /api/workspaces/{id}/committee

Gate « plateforme » (A+B) : échec si **500** sur POST /api/workspaces ou GET /api/market/overview.
Committee : **200 / 404 / 403** = OK — 403 = RBAC (ex. workspace.read) ; le compte smoke
n’a pas forcément ce droit. Point **C** (créateur workspace → lecture committee / membership)
sera central dans l’implémentation **architecture cognitive** ; jusqu’alors ne pas traiter 403
comme régression serveur.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


def _req(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 45,
) -> tuple[int, dict | str]:
    h = dict(headers or {})
    try:
        r = urllib.request.Request(url, data=data, method=method)
        for k, v in h.items():
            r.add_header(k, v)
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    try:
        body: dict | str = json.loads(raw.decode())
    except json.JSONDecodeError:
        body = raw.decode(errors="replace")[:500]
    return status, body


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "").strip().rstrip("/")
    if not base:
        base = os.environ.get("BLOC3_API_BASE", "").strip().rstrip("/")
    if not base:
        print(
            "Usage: python scripts/bloc3_smoke_railway.py <base_url>\n"
            "Exemple: python scripts/bloc3_smoke_railway.py "
            "https://decision-memory-v1-production.up.railway.app",
            file=sys.stderr,
        )
        return 1

    print(f"=== BLOC3 SMOKE — {base} ===\n")
    ok_all = True

    smoke_user = f"smoke_bloc3_{uuid.uuid4().hex[:10]}"
    smoke_pass = "SmokeBloc3Test123!"

    reg_payload = json.dumps(
        {
            "email": f"{smoke_user}@example.com",
            "username": smoke_user,
            "password": smoke_pass,
        }
    ).encode()
    st, reg = _req(
        f"{base}/auth/register",
        method="POST",
        data=reg_payload,
        headers={"Content-Type": "application/json"},
    )
    if st not in (200, 201):
        print(f"[0] POST /auth/register -> HTTP {st} FAIL")
        print(f"     body: {reg}")
        ok_all = False
        return 1
    print(f"[0] POST /auth/register -> HTTP {st} OK")
    if isinstance(reg, dict):
        print(f"     username: {reg.get('username')}")

    form = urllib.parse.urlencode(
        {"username": smoke_user, "password": smoke_pass}
    ).encode()
    st, tok_body = _req(
        f"{base}/auth/token",
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if st != 200 or not isinstance(tok_body, dict) or "access_token" not in tok_body:
        print(f"[1] POST /auth/token -> HTTP {st} FAIL")
        print(f"     body: {tok_body}")
        return 1
    token = tok_body["access_token"]
    print(f"[1] POST /auth/token -> HTTP {st} OK")

    ref_suffix = uuid.uuid4().hex[:12]
    reference_code = f"SMOKE-BLOC3-{ref_suffix}"
    ws_payload = json.dumps(
        {
            "reference_code": reference_code,
            "title": "Smoke test BLOC 3",
            "process_type": "devis_simple",
            "humanitarian_context": "none",
        }
    ).encode()
    st, ws = _req(
        f"{base}/api/workspaces",
        method="POST",
        data=ws_payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    if st not in (200, 201):
        print(f"[2] POST /api/workspaces -> HTTP {st} FAIL")
        print(f"     body: {ws}")
        ok_all = False
        workspace_id = None
    else:
        print(f"[2] POST /api/workspaces -> HTTP {st} OK")
        workspace_id = ws.get("workspace_id") if isinstance(ws, dict) else None
        print(f"     reference_code: {reference_code}")
        print(f"     workspace_id: {workspace_id}")

    st, mkt = _req(
        f"{base}/api/market/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    if st != 200:
        print(f"[3] GET /api/market/overview -> HTTP {st} FAIL")
        print(f"     body: {mkt}")
        ok_all = False
    else:
        print(f"[3] GET /api/market/overview -> HTTP {st} OK")

    if workspace_id:
        st, com = _req(
            f"{base}/api/workspaces/{workspace_id}/committee",
            headers={"Authorization": f"Bearer {token}"},
        )
        if st == 403:
            print(
                f"[4] GET /api/workspaces/{{id}}/committee -> HTTP {st} OK "
                f"(RBAC — workspace.read requis ; attendu pour user smoke)"
            )
        elif st not in (200, 404):
            print(f"[4] GET /api/workspaces/{{id}}/committee -> HTTP {st} FAIL")
            print(f"     body: {com}")
            ok_all = False
        else:
            print(
                f"[4] GET /api/workspaces/{{id}}/committee -> HTTP {st} OK "
                f"(404 si pas de session committee)"
            )
    else:
        print("[4] GET /api/workspaces/{id}/committee -> SKIP (pas de workspace_id)")
        ok_all = False

    print("\n=== RESULT ===")
    print("OK" if ok_all else "KO")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
