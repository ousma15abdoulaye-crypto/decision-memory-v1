#!/usr/bin/env python3
"""
DMS Database Setup — Creates database, role, and pg_trgm extension.
Run: python scripts/setup_db.py
"""
from __future__ import annotations

import sys
import getpass
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg
    from psycopg import sql
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)


def create_db_and_role(
    host: str = "localhost",
    port: int = 5432,
    superuser: str = "postgres",
    superuser_password: str = "",
    db_name: str = "dms",
    db_user: str = "dms",
    db_password: str = "dms_dev_password_change_me",
) -> bool:
    """Create database, role, and pg_trgm extension."""
    
    if not superuser_password:
        superuser_password = getpass.getpass(f"Enter password for PostgreSQL superuser '{superuser}': ")
    
    # Connect as superuser to create role and database
    try:
        print(f"Connecting as superuser '{superuser}'...")
        admin_conn = psycopg.connect(
            f"postgresql://{superuser}:{superuser_password}@{host}:{port}/postgres"
        )
        admin_conn.autocommit = True
        
        with admin_conn.cursor() as cur:
            # Create role
            print(f"Creating role '{db_user}'...")
            cur.execute(
                sql.SQL("""
                    DO $$
                    BEGIN
                      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s) THEN
                        CREATE ROLE {} LOGIN PASSWORD %s;
                      ELSE
                        ALTER ROLE {} PASSWORD %s;
                      END IF;
                    END$$;
                """).format(
                    sql.Identifier(db_user),
                    sql.Identifier(db_user)
                ),
                (db_user, db_password, db_password)
            )
            print(f"✅ Role '{db_user}' created/updated")
            
            # Create database
            print(f"Creating database '{db_name}'...")
            try:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(db_name),
                        sql.Identifier(db_user)
                    )
                )
                print(f"✅ Database '{db_name}' created")
            except psycopg.errors.DuplicateDatabase:
                print(f"⚠️  Database '{db_name}' already exists, continuing...")
            
        admin_conn.close()
        
        # Connect as db_user to enable extension
        print(f"Connecting as '{db_user}' to enable pg_trgm extension...")
        user_conn = psycopg.connect(
            f"postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}"
        )
        user_conn.autocommit = True
        
        with user_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            print("✅ pg_trgm extension enabled")
        
        user_conn.close()
        
        print("\n" + "="*60)
        print("✅ Setup complete!")
        print("="*60)
        print(f"Database: {db_name}")
        print(f"User: {db_user}")
        print(f"Password: {db_password}")
        print(f"\nDATABASE_URL for .env file:")
        print(f"postgresql+psycopg://{db_user}:{db_password}@{host}:{port}/{db_name}")
        print("="*60)
        
        return True
        
    except psycopg.OperationalError as e:
        print(f"ERROR: Connection failed: {e}", file=sys.stderr)
        return False
    except psycopg.errors.InsufficientPrivilege as e:
        print(f"ERROR: Insufficient privileges: {e}", file=sys.stderr)
        print("Make sure you're using a superuser account.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup DMS PostgreSQL database")
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--superuser", default="postgres", help="PostgreSQL superuser")
    parser.add_argument("--superuser-password", default="", help="Superuser password (will prompt if not provided)")
    parser.add_argument("--db-name", default="dms", help="Database name")
    parser.add_argument("--db-user", default="dms", help="Database user")
    parser.add_argument("--db-password", default="dms_dev_password_change_me", help="Database user password")
    
    args = parser.parse_args()
    
    success = create_db_and_role(
        host=args.host,
        port=args.port,
        superuser=args.superuser,
        superuser_password=args.superuser_password,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )
    
    sys.exit(0 if success else 1)
