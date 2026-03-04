"""Capture les erreurs et failures pytest pour diagnostic."""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header",
     "tests/vendors/test_vendor_patch.py",
     "tests/vendors/test_vendor_dedup.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"C:\Users\abdoulaye.ousmane\decision-memory-v1"
)
output = result.stdout + result.stderr
safe = output.encode("ascii", errors="replace").decode("ascii")
print(safe[-4000:])
print(f"=== returncode: {result.returncode} ===")
