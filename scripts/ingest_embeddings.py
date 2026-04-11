"""
Ingestion batch : export JSONL M12-v2 -> chunks -> embeddings (BGE-M3 ou stub) -> dms_embeddings.

Aligné ADR-H3 / CONTEXT_ANCHOR. Exige PostgreSQL + migration 096 (tenant_id + RLS).

Usage:
  python scripts/ingest_embeddings.py --input data/annotations/foo.jsonl --tenant-id <UUID>
  python scripts/ingest_embeddings.py --input tests/fixtures/m12_rag_ingest_sample.jsonl \\
      --tenant-id <UUID> --dry-run --limit 5

Prérequis : DATABASE_URL, tenant existant dans public.tenants.
Optionnel : BGE_MODEL_PATH + FlagEmbedding pour vecteurs denses prod ; sinon stub hash (CI).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Json

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

_SOURCE_TABLE = "m12_corpus_line"
_MAX_PG_BIGINT = 2**63 - 1


def stable_source_pk(line_id: str) -> int:
    """Déterministe : BIGINT pour colonne source_pk (contrainte UNIQUE avec tenant)."""
    digest = hashlib.sha256(line_id.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big", signed=False) % _MAX_PG_BIGINT


def corpus_text_from_m12_line(line: dict[str, Any]) -> str:
    """Texte indexable : préfère champs texte explicites, sinon sérialisation JSON tronquée."""
    parts: list[str] = []
    dms = line.get("dms_annotation")
    if isinstance(dms, dict):
        for key in (
            "document_text",
            "raw_document_text",
            "ocr_text",
            "extracted_text",
        ):
            v = dms.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        if not parts:
            c1 = dms.get("couche_1_routing")
            if isinstance(c1, dict):
                ev = c1.get("routing_evidence")
                if isinstance(ev, str) and ev.strip():
                    parts.append(ev.strip())
    if not parts:
        raw = json.dumps(line, ensure_ascii=False, default=str)
        parts.append(raw[:200_000])
    return "\n\n".join(parts)


def _upsert_chunk(
    cur: Any,
    *,
    tenant_id: str,
    source_pk: int,
    chunk_index: int,
    chunk_text: str,
    vec: str,
    sparse: dict[str, float],
    model_name: str,
    model_version: str,
) -> None:
    sql = """
        INSERT INTO public.dms_embeddings (
            tenant_id, source_table, source_pk, chunk_index,
            chunk_text, embedding_dense, embedding_sparse,
            model_name, model_version
        )
        VALUES (
            %(tenant_id)s::uuid, %(source_table)s, %(source_pk)s, %(chunk_index)s,
            %(chunk_text)s, %(vec)s::vector, %(sparse)s::jsonb,
            %(model_name)s, %(model_version)s
        )
        ON CONFLICT (tenant_id, source_table, source_pk, chunk_index)
        DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            embedding_dense = EXCLUDED.embedding_dense,
            embedding_sparse = EXCLUDED.embedding_sparse,
            model_name = EXCLUDED.model_name,
            model_version = EXCLUDED.model_version
    """
    cur.execute(
        sql,
        {
            "tenant_id": tenant_id,
            "source_table": _SOURCE_TABLE,
            "source_pk": source_pk,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "vec": vec,
            "sparse": Json(sparse),
            "model_name": model_name,
            "model_version": model_version,
        },
    )


def main() -> int:
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv(_PROJECT_ROOT / ".env.local", override=True)

    parser = argparse.ArgumentParser(description="Ingest M12 JSONL into dms_embeddings")
    parser.add_argument(
        "--input", type=Path, required=True, help="Fichier JSONL m12-v2"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        required=True,
        help="UUID tenant (public.tenants) — RLS et colonne tenant_id",
    )
    parser.add_argument("--dry-run", action="store_true", help="Pas d'écriture DB")
    parser.add_argument("--limit", type=int, default=None, help="Max lignes JSONL")
    parser.add_argument(
        "--batch-commits",
        type=int,
        default=50,
        help="Commit tous les N lignes source (hors dry-run)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from src.annotation.m12_export_io import (
        export_line_kind,
        iter_m12_jsonl_lines,
        stable_m12_corpus_line_id,
    )
    from src.memory.chunker import SemanticChunker
    from src.memory.embedding_service import EmbeddingService

    inp = args.input.resolve()
    if not inp.is_file():
        logger.error("Fichier introuvable : %s", inp)
        return 2

    embedder = EmbeddingService()
    chunker = SemanticChunker()
    model_label = (
        "bge-m3" if os.environ.get("BGE_MODEL_PATH", "").strip() else "stub-hash"
    )
    version_label = "1.0"

    lines_read = 0
    chunks_written = 0
    lines_skipped = 0

    if args.dry_run:
        for line in iter_m12_jsonl_lines(inp):
            if args.limit is not None and lines_read >= args.limit:
                break
            lines_read += 1
            if not isinstance(line, dict):
                lines_skipped += 1
                continue
            kind = export_line_kind(line)
            if kind != "m12-v2" or line.get("export_ok") is not True:
                lines_skipped += 1
                continue
            text = corpus_text_from_m12_line(line)
            if not text.strip():
                lines_skipped += 1
                continue
            lid = stable_m12_corpus_line_id(line)
            pk = stable_source_pk(lid)
            chunks = chunker.chunk(text)
            for ch in chunks:
                emb = embedder.embed_chunks([ch])[0]
                vec_literal = "[" + ",".join(str(v) for v in emb.dense) + "]"
                logger.debug(
                    "dry-run line=%s pk=%s idx=%s dim=%s",
                    lid,
                    pk,
                    ch.chunk_index,
                    len(emb.dense),
                )
                chunks_written += 1
        logger.info(
            "Terminé [dry-run] lignes_lues=%s ignorées=%s chunks_simulés=%s",
            lines_read,
            lines_skipped,
            chunks_written,
        )
        return 0

    import psycopg

    from src.core.config import get_settings

    settings = get_settings()
    dsn = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

    pending = 0
    with psycopg.connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_tenant', %s, true)",
                (args.tenant_id.strip(),),
            )
            cur.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                (args.tenant_id.strip(),),
            )

        for line in iter_m12_jsonl_lines(inp):
            if args.limit is not None and lines_read >= args.limit:
                break
            lines_read += 1
            if not isinstance(line, dict):
                lines_skipped += 1
                continue
            kind = export_line_kind(line)
            if kind != "m12-v2" or line.get("export_ok") is not True:
                lines_skipped += 1
                continue
            text = corpus_text_from_m12_line(line)
            if not text.strip():
                lines_skipped += 1
                continue
            lid = stable_m12_corpus_line_id(line)
            pk = stable_source_pk(lid)
            chunks = chunker.chunk(text)
            if not chunks:
                lines_skipped += 1
                continue
            embed_results = embedder.embed_chunks(chunks)
            with conn.cursor() as cur:
                for ch, emb in zip(chunks, embed_results, strict=True):
                    vec_literal = "[" + ",".join(str(v) for v in emb.dense) + "]"
                    _upsert_chunk(
                        cur,
                        tenant_id=args.tenant_id.strip(),
                        source_pk=pk,
                        chunk_index=ch.chunk_index,
                        chunk_text=ch.text,
                        vec=vec_literal,
                        sparse=emb.sparse,
                        model_name=model_label,
                        model_version=version_label,
                    )
                    chunks_written += 1
                pending += 1
            if pending >= args.batch_commits:
                conn.commit()
                pending = 0
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT set_config('app.current_tenant', %s, true)",
                        (args.tenant_id.strip(),),
                    )
                    cur.execute(
                        "SELECT set_config('app.tenant_id', %s, true)",
                        (args.tenant_id.strip(),),
                    )
        conn.commit()

    logger.info(
        "Terminé lignes_lues=%s ignorées=%s chunks_upsert=%s tenant=%s",
        lines_read,
        lines_skipped,
        chunks_written,
        args.tenant_id[:8] + "...",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
