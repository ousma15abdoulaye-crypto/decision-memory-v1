# Runbook — dms_embeddings IVFFlat Index

**Component:** `dms_embeddings` table (migration 064)  
**Index:** `idx_embeddings_dense_ivfflat` on `embedding_dense vector_cosine_ops`  
**Related:** ADR-H3-BGE-M3-001, GAP-11 CTO Audit

---

## Why an IVFFlat Index?

Without an index, every `embedding_dense <=>` query performs a **full table scan**.
At 10,000+ embeddings, this means latency > 1 second per RAG query.

IVFFlat partitions the vector space into `lists` clusters and probes only a subset,
reducing search complexity from O(N) to O(N/lists × nprobes).

---

## When to Create the Index

**Never create on empty table.** IVFFlat requires >= 100 rows for meaningful clustering.

| Rows | Recommended `lists` | Expected speedup |
|------|---------------------|-----------------|
| < 100 | N/A (skip) | — |
| 100–1000 | 10–30 | 5-10x |
| 1000–10000 | 50–100 | 10-20x |
| > 10000 | 100–200 | 20-50x |

Rule of thumb: `lists ≈ sqrt(N)`.

---

## How to Create

```bash
# After ingesting first batch of >= 100 embeddings:
python scripts/create_ivfflat_index.py
```

The script:
1. Counts rows in `dms_embeddings`.
2. Checks if the index already exists (idempotent).
3. Creates `CREATE INDEX CONCURRENTLY` (non-blocking).
4. Auto-computes `lists = max(1, min(100, N // 10))`.

---

## Search-time Tuning

After index creation, set `ivfflat.probes` for quality/speed tradeoff:

```sql
-- At query time (in the same session / transaction):
SET ivfflat.probes = 10;  -- default=1; higher = more accurate, slower
```

In `RAGService._DENSE_SEARCH_SQL`, add before the SELECT:
```sql
SET LOCAL ivfflat.probes = 10;
SELECT ...
```

| `probes` | Recall@10 | Latency |
|----------|-----------|---------|
| 1 (default) | ~90% | 1x |
| 10 | ~97% | 3x |
| 40 | ~99% | 8x |

For DMS production, `probes=10` is recommended.

---

## Ingestion Script

```bash
# Chunk documents, embed, and insert into dms_embeddings:
python scripts/ingest_embeddings.py --source <path_to_documents>
```

Create index after each batch load that crosses a new magnitude threshold (100, 1000, 10000).

---

## Monitoring

Check index usage:
```sql
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname = 'idx_embeddings_dense_ivfflat';
```

If `idx_scan = 0` after RAG queries, ensure `ORDER BY embedding_dense <=> ...`
uses `vector_cosine_ops` (matches index operator class).

---

## Rollback

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_embeddings_dense_ivfflat;
```

Full table scan will resume (no data loss, only performance impact).

---

## Maintenance

After major bulk inserts (> 2x current size), recreate the index:
```bash
python scripts/create_ivfflat_index.py  # Idempotent - drops old if exists
```

Or manually:
```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_embeddings_dense_ivfflat;
-- Then re-run the creation script
```
