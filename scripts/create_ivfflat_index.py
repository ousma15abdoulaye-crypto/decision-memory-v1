"""Create IVFFlat index on dms_embeddings.embedding_dense (GAP-11).

Run AFTER the first batch of >= 100 embeddings has been inserted:
    python scripts/create_ivfflat_index.py

The index CONCURRENTLY option avoids locking the table during creation.
See docs/ops/embeddings_index_runbook.md for the full runbook.
"""

from __future__ import annotations

import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

_INDEX_NAME = "idx_embeddings_dense_ivfflat"
_TABLE = "public.dms_embeddings"
_COLUMN = "embedding_dense"
_LISTS = 100  # sqrt(N) where N ≈ 10000 initial rows; tune after first batch


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Check row count first
            cur.execute(f"SELECT COUNT(*) AS c FROM {_TABLE}")
            row = cur.fetchone()
            count = int(row["c"]) if row else 0  # type: ignore[index]
            if count < 100:
                print(
                    f"WARNING: only {count} rows in {_TABLE}. "
                    "IVFFlat requires >= 100 rows for meaningful clustering. "
                    "Proceeding anyway (index will be valid but suboptimal)."
                )

            # Check if index already exists
            cur.execute(
                """
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'dms_embeddings'
                  AND indexname  = %s
                """,
                (_INDEX_NAME,),
            )
            if cur.fetchone():
                print(f"Index {_INDEX_NAME} already exists — skipping.")
                return

            lists = max(1, min(_LISTS, count // 10)) if count > 0 else _LISTS
            print(f"Creating IVFFlat index on {_TABLE}({_COLUMN}) with lists={lists} ...")
            cur.execute(
                f"""
                CREATE INDEX CONCURRENTLY {_INDEX_NAME}
                    ON {_TABLE}
                    USING ivfflat ({_COLUMN} vector_cosine_ops)
                    WITH (lists = {lists})
                """
            )
            print(f"Index {_INDEX_NAME} created successfully.")


if __name__ == "__main__":
    main()
