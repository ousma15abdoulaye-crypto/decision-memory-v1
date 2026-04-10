"""Test Pipeline V5 live via Railway API."""
import os
import sys
import requests
from datetime import datetime

# Get Railway API URL (Railway runs on port 9090 internally, external via https)
RAILWAY_URL = "https://annotation-backend-production.up.railway.app"
# Railway assigns random public domains, check actual domain
ALT_URL = "https://web-production-e3a0.up.railway.app"
WORKSPACE_ID = "f1a6edfb-ac50-4301-a1a9-7a80053c632a"

def test_health():
    """Test 1: Health check."""
    print(f"\n=== TEST 1: Health Check ===")
    try:
        resp = requests.get(f"{RAILWAY_URL}/health", timeout=10, verify=False)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_pipeline_endpoint():
    """Test 2: Pipeline V5 endpoint (no auth - will 401 but endpoint exists)."""
    print(f"\n=== TEST 2: Pipeline V5 Endpoint Exists ===")
    try:
        resp = requests.post(
            f"{RAILWAY_URL}/api/workspaces/{WORKSPACE_ID}/run-pipeline",
            timeout=10,
            verify=False
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 401:
            print(f"OK Endpoint exists (401 = needs auth)")
            return True
        elif resp.status_code == 404:
            print(f"FAIL Endpoint NOT FOUND (route missing in app_factory?)")
            return False
        else:
            print(f"Response: {resp.text[:500]}")
            return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_openapi_schema():
    """Test 3: Check OpenAPI schema for pipeline route."""
    print(f"\n=== TEST 3: OpenAPI Schema ===")
    try:
        resp = requests.get(f"{RAILWAY_URL}/openapi.json", timeout=10, verify=False)
        if resp.status_code == 200:
            schema = resp.json()
            paths = schema.get("paths", {})
            pipeline_path = f"/api/workspaces/{{workspace_id}}/run-pipeline"
            if pipeline_path in paths:
                print(f"OK Pipeline route in OpenAPI: {pipeline_path}")
                print(f"   Methods: {list(paths[pipeline_path].keys())}")
                return True
            else:
                print(f"FAIL Pipeline route NOT in OpenAPI")
                print(f"Available workspace routes:")
                for p in paths:
                    if "/workspaces" in p:
                        print(f"   - {p}")
                return False
        else:
            print(f"Cannot retrieve OpenAPI: {resp.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print(f"=== PIPELINE V5 LIVE TESTS ===")
    print(f"Target: {RAILWAY_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    results = []
    results.append(("Health", test_health()))
    results.append(("Pipeline Endpoint", test_pipeline_endpoint()))
    results.append(("OpenAPI Schema", test_openapi_schema()))

    print(f"\n=== SUMMARY ===")
    for name, ok in results:
        symbol = "OK" if ok else "FAIL"
        print(f"[{symbol}] {name}")

    sys.exit(0 if all(r[1] for r in results) else 1)

if __name__ == "__main__":
    main()
