"""Test login admin@dms.local / admin123 sur Railway prod."""
import urllib.request
import urllib.parse
import json
import base64

BASE = "https://decision-memory-v1-production.up.railway.app"

data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE}/auth/token", data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
        token = body.get("access_token", "")
        raw = token.split(".")[1] if token else ""
        raw += "=" * (4 - len(raw) % 4)
        claims = json.loads(base64.b64decode(raw)) if raw else {}
        role = claims.get("role")
        sub = claims.get("sub")
        typ = claims.get("type")
        print(f"HTTP {resp.status} OK")
        print(f"role : {role}")
        print(f"sub  : {sub}")
        print(f"type : {typ}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code} FAIL")
    print(body[:400])
except Exception as ex:
    print(f"ERROR: {ex}")
