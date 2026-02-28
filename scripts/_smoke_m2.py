"""Smoke test M2 — moteur auth V4.1.0.

Usage :
  python scripts/_smoke_m2.py https://<TON-URL>.up.railway.app
"""

import base64
import json
import sys
import urllib.parse
import urllib.request
import uuid


def run(base: str) -> None:
    print(f"=== SMOKE M2 — {base} ===\n")

    # 0. Créer un utilisateur smoke dédié (évite dépendance au seed admin)
    smoke_user = f"smoke_{uuid.uuid4().hex[:8]}"
    smoke_pass = "SmokeM2Test123!"
    reg_payload = json.dumps({
        "email": f"{smoke_user}@smoke-test.com",
        "username": smoke_user,
        "password": smoke_pass,
    }).encode()
    req0 = urllib.request.Request(f"{base}/auth/register", data=reg_payload, method="POST")
    req0.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req0, timeout=20) as r0:
        reg = json.loads(r0.read())
        print(f"[0] POST /auth/register -> HTTP {r0.status} OK")
        print(f"     username  : {reg.get('username')}")
        print(f"     role_name : {reg.get('role_name')}")

    # 1. POST /auth/token
    data = urllib.parse.urlencode({"username": smoke_user, "password": smoke_pass}).encode()
    req = urllib.request.Request(f"{base}/auth/token", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read())
        token = body["access_token"]
        print(f"\n[1] POST /auth/token -> HTTP {resp.status} OK")

    # Decode JWT claims (no signature check)
    raw = token.split(".")[1]
    raw += "=" * (4 - len(raw) % 4)
    claims = json.loads(base64.b64decode(raw))
    jti_ok = "jti" in claims
    role_ok = "role" in claims
    type_ok = claims.get("type") == "access"
    print(f"     jti   : {'PRESENT OK' if jti_ok else 'ABSENT FAIL'}")
    print(f"     role  : {claims.get('role', 'ABSENT FAIL')}")
    print(f"     type  : {claims.get('type', 'ABSENT FAIL')} {'OK' if type_ok else 'FAIL'}")
    print(f"     sub   : {claims.get('sub', 'ABSENT')}")

    # 2. GET /auth/me
    req2 = urllib.request.Request(f"{base}/auth/me")
    req2.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req2, timeout=20) as r2:
        me = json.loads(r2.read())
        print(f"\n[2] GET  /auth/me -> HTTP {r2.status} OK")
        print(f"     username  : {me.get('username')}")
        print(f"     role_name : {me.get('role_name')}")
        print(f"     id        : {me.get('id')}")

    # 3. POST /api/cases
    case_body = json.dumps({"case_type": "DAO", "title": "Smoke M2", "lot": None}).encode()
    req3 = urllib.request.Request(f"{base}/api/cases", data=case_body, method="POST")
    req3.add_header("Authorization", f"Bearer {token}")
    req3.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req3, timeout=20) as r3:
        case = json.loads(r3.read())
        print(f"\n[3] POST /api/cases -> HTTP {r3.status} OK")
        print(f"     id       : {case.get('id')}")
        print(f"     owner_id : {case.get('owner_id')}")

    # 4. GET /api/cases
    req4 = urllib.request.Request(f"{base}/api/cases")
    req4.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req4, timeout=20) as r4:
        print(f"\n[4] GET  /api/cases -> HTTP {r4.status} OK")

    # Summary
    all_ok = jti_ok and role_ok and type_ok
    print("\n" + "=" * 50)
    if all_ok:
        print("SMOKE M2 --- VERT OK --- Token V4.1.0 confirme")
    else:
        print("SMOKE M2 --- ROUGE FAIL --- Claims manquants")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "PLACEHOLDER":
        print("Usage: python scripts/_smoke_m2.py https://<URL>.up.railway.app")
        sys.exit(0)
    run(sys.argv[1].rstrip("/"))
