"""P3.2 — Git state probe for PR preparation"""
import subprocess
from pathlib import Path

repo_root = Path(__file__).parent.parent

print("=" * 70)
print("P3.2 GIT STATE PROBE")
print("=" * 70)
print()

def run_git(args):
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode

# Current branch
print("[1] Current branch")
print("=" * 70)
stdout, stderr, code = run_git(["branch", "--show-current"])
print(f"BRANCH: {stdout.strip()}")
print()

# Git status
print("[2] Git status")
print("=" * 70)
stdout, stderr, code = run_git(["status", "--short"])
print("SHORT STATUS:")
print(stdout if stdout.strip() else "(no changes)")
print()

stdout, stderr, code = run_git(["status"])
print("FULL STATUS:")
print(stdout)
print()

# Modified files
print("[3] Modified files (not staged)")
print("=" * 70)
stdout, stderr, code = run_git(["diff", "--name-only"])
if stdout.strip():
    print(stdout)
else:
    print("(none)")
print()

# Staged files
print("[4] Staged files")
print("=" * 70)
stdout, stderr, code = run_git(["diff", "--name-only", "--cached"])
if stdout.strip():
    print(stdout)
else:
    print("(none)")
print()

# Recent log
print("[5] Recent commits (last 10)")
print("=" * 70)
stdout, stderr, code = run_git(["log", "--oneline", "-n", "10"])
print(stdout)
print()

# Untracked files
print("[6] Untracked files")
print("=" * 70)
stdout, stderr, code = run_git(["ls-files", "--others", "--exclude-standard"])
untracked = [f for f in stdout.strip().split('\n') if f.strip()]
if untracked:
    for f in untracked[:20]:  # Limit to 20
        print(f"  {f}")
    if len(untracked) > 20:
        print(f"  ... and {len(untracked) - 20} more")
else:
    print("(none)")
print()

print("=" * 70)
print("GIT STATE PROBE COMPLETE")
print("=" * 70)
