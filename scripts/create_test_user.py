#!/usr/bin/env python3
"""Create test user for frontend-v51 login and workspace testing.

Usage:
  python scripts/create_test_user.py

Reads DATABASE_URL from the environment (or .env at project root).
The script is idempotent — safe to run multiple times (ON CONFLICT DO NOTHING).

User created:
  Full name : Abdoulaye Ousmane
  Email     : ousma15abdoulaye@gmail.com
  Username  : abdoulaye_ousmane
  Role      : procurement_officer (role_id = 2)

ADR-0003: raw psycopg, no ORM.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# ── Allow running from any working directory ──────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env if present (dev convenience — Railway injects DATABASE_URL directly)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # python-dotenv optional; DATABASE_URL must be set in environment

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]")
    sys.exit(1)

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed. Run: pip install bcrypt")
    sys.exit(1)

# ── Test user definition ──────────────────────────────────────────────────────
USER_EMAIL     = "ousma15abdoulaye@gmail.com"
USER_USERNAME  = "abdoulaye_ousmane"
USER_FULL_NAME = "Abdoulaye Ousmane"
USER_PASSWORD  = "Babayaga202@BT"
USER_ROLE_ID   = 2          # procurement_officer (seeded in migration 004_users_rbac)
USER_ROLE_NAME = "procurement_officer"

INSERT_SQL = """
INSERT INTO users (
    email,
    username,
    hashed_password,
    full_name,
    is_active,
    is_superuser,
    role_id,
    created_at
)
VALUES (
    %(email)s,
    %(username)s,
    %(hashed_password)s,
    %(full_name)s,
    TRUE,
    FALSE,
    %(role_id)s,
    %(created_at)s
)
ON CONFLICT (email) DO NOTHING
"""

CHECK_SQL = """
SELECT id FROM users WHERE email = %(email)s
"""


def hash_password(plain: str) -> str:
    """Hash password with bcrypt rounds=12 — mirrors src/api/auth_helpers.py."""
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("  Set it directly or add it to your .env file.")
        print("  Example: DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname")
        sys.exit(1)

    # psycopg expects postgresql:// not postgresql+psycopg://
    conn_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    hashed_password = hash_password(USER_PASSWORD)
    created_at = datetime.utcnow().isoformat()

    params = {
        "email":           USER_EMAIL,
        "username":        USER_USERNAME,
        "hashed_password": hashed_password,
        "full_name":       USER_FULL_NAME,
        "role_id":         USER_ROLE_ID,
        "created_at":      created_at,
    }

    with psycopg.connect(conn_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Check whether the user already exists before inserting
            cur.execute(CHECK_SQL, {"email": USER_EMAIL})
            existing = cur.fetchone()

            if existing:
                print(f"ℹ  User already exists: {USER_EMAIL} (id={existing['id']}) — no changes made.")
                return

            cur.execute(INSERT_SQL, params)
            conn.commit()

            # Confirm the row landed
            cur.execute(CHECK_SQL, {"email": USER_EMAIL})
            created = cur.fetchone()

    if created:
        print(f"✓ Test user created: {USER_EMAIL}")
        print(f"  Username: {USER_USERNAME}")
        print(f"  Role: {USER_ROLE_NAME}")
    else:
        # ON CONFLICT DO NOTHING fired — row existed under a different email
        print(f"ℹ  Insert skipped (conflict on username or email). User may already exist.")


if __name__ == "__main__":
    main()
