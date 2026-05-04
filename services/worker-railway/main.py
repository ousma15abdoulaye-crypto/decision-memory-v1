"""
DMS Worker Railway — FastAPI worker for internal Railway DB access
Spec: decisions/worker/W1_worker_railway_spec.md
"""

import asyncio
import hmac
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

# Ensure repo root is in sys.path so src.* imports resolve when running
# from services/worker-railway/ (Railway startCommand: cd services/worker-railway).
_repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import psycopg
from arq import create_pool
from arq.connections import RedisSettings
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Windows async fix for psycopg
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load .env file
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
WORKER_AUTH_TOKEN = os.getenv("WORKER_AUTH_TOKEN")
ARQ_REDIS_URL = os.getenv("ARQ_REDIS_URL") or os.getenv("REDIS_URL")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
if not WORKER_AUTH_TOKEN:
    raise ValueError("WORKER_AUTH_TOKEN environment variable is required")


def get_arq_redis_url(header_override: str | None = None) -> str | None:
    """Resolve ARQ Redis DSN without logging secret-bearing values."""
    if header_override:
        return header_override
    if ARQ_REDIS_URL:
        return ARQ_REDIS_URL

    host = os.getenv("REDISHOST")
    password = os.getenv("REDIS_PASSWORD")
    port = os.getenv("REDISPORT", "6379")
    user = os.getenv("REDISUSER", "default")
    if host and password:
        return f"redis://{quote(user)}:{quote(password)}@{host}:{port}"

    return None


def redis_config_status() -> dict[str, bool]:
    """Return only presence flags, never Redis values."""
    return {
        "ARQ_REDIS_URL": bool(os.getenv("ARQ_REDIS_URL")),
        "REDIS_URL": bool(os.getenv("REDIS_URL")),
        "REDISHOST": bool(os.getenv("REDISHOST")),
        "REDIS_PASSWORD": bool(os.getenv("REDIS_PASSWORD")),
        "REDISPORT": bool(os.getenv("REDISPORT")),
        "REDISUSER": bool(os.getenv("REDISUSER")),
        "X_ARQ_REDIS_URL": False,
    }


# Logging structuré JSON
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper()), format="%(message)s")
logger = logging.getLogger(__name__)


def log_structured(level: str, message: str, **kwargs):
    """Log structured JSON to stdout"""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "message": message,
        **kwargs,
    }
    logger.log(getattr(logging, level.upper()), json.dumps(log_entry))


def log_exception(level: str, message: str, exc: Exception) -> None:
    """Log exception class only; connection strings can appear in DB errors."""
    log_structured(level, message, error_type=type(exc).__name__)


class RehydrateEnqueueRequest(BaseModel):
    """Payload for controlled bundle_document raw_text rehydration enqueue."""

    workspace_id: UUID
    document_id: UUID
    force: bool = False


class M12ClassifyEnqueueRequest(BaseModel):
    """Payload for controlled bundle_document M12 classification enqueue."""

    workspace_id: UUID
    document_id: UUID
    force: bool = False


class BundleGateBEnqueueRequest(BaseModel):
    """Payload for controlled supplier_bundle Gate B qualification enqueue."""

    workspace_id: UUID
    bundle_id: UUID
    force: bool = False


class BundleOfferExtractionEnqueueRequest(BaseModel):
    """Payload for controlled supplier_bundle offer extraction enqueue."""

    workspace_id: UUID
    bundle_id: UUID
    force: bool = False


M6D_EXPECTED_DAO_CRITERIA_COUNT = 3
M6D_EXPECTED_DAO_WEIGHT_TOTAL = 100.0
M6D_DAO_WEIGHT_TOLERANCE = 0.01


def runtime_commit() -> str | None:
    """Return Railway commit metadata when the platform exposes it."""
    for key in (
        "RAILWAY_GIT_COMMIT_SHA",
        "RAILWAY_DEPLOYMENT_COMMIT_SHA",
        "SOURCE_COMMIT",
        "GIT_COMMIT_SHA",
    ):
        value = os.getenv(key)
        if value:
            return value
    return None


@contextmanager
def open_m6d_readonly_connection():
    """Read-only DB access for M6D diagnostics.

    The worker does not run JWT middleware, so ``app.tenant_id`` is never set.
    Several tables (e.g. ``criterion_assessments``) use RLS policies that require
    either a matching tenant or ``app.is_admin=true``. Without this, reads can
    fail at the SQL layer and surface as ``Database query failed`` on the probe.

    PostgreSQL enforces read-only at transaction level (``BEGIN READ ONLY``) before
    applying the transaction-local ``app.is_admin`` GUC. ``get_connection()`` is
    deliberately not used here: it may issue ``set_config`` before the probe can
    enter a read-only transaction.

    This context manager is invoked only from the authenticated diagnostics
    probe; all SQL still filters by ``workspace_id`` supplied in the route (the
    assembler and probe queries are workspace-scoped).
    """
    from src.db.core import _ConnectionWrapper
    from src.resilience import db_breaker, retry_db_operation

    @retry_db_operation
    def _connect():
        return db_breaker.call(lambda: psycopg.connect(DATABASE_URL))

    conn = _connect()
    wrapper = _ConnectionWrapper(conn)
    try:
        wrapper.execute("BEGIN READ ONLY")
        wrapper.execute(
            "SELECT set_config('app.is_admin', :v, true)",
            {"v": "true"},
        )
        yield wrapper
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        wrapper.close()


def fetch_m6d_rows(conn, sql: str, params: dict) -> list[dict]:
    from src.db import db_fetchall

    return db_fetchall(conn, sql, params)


def build_canonical_m14_offers(conn, workspace_id: str) -> list[dict]:
    from src.procurement.m14_workspace_assembler import build_m14_offers_for_workspace

    return build_m14_offers_for_workspace(
        conn,
        workspace_id,
        allow_existing_evaluation_documents=True,
        allow_stale_criterion_assessments=True,
    )


def is_m14_offer_readiness_error(exc: Exception) -> bool:
    from src.procurement.m14_workspace_assembler import M14OfferReadinessError

    return isinstance(exc, M14OfferReadinessError)


def construct_m14_input_no_persist(
    case_id: str, offers: list[dict], dao_rows: list[dict]
):
    from src.procurement.m14_evaluation_models import (
        M14EvaluationInput,
        m14_h2_scoring_structure_dict_from_dao_criteria_rows,
    )

    return M14EvaluationInput(
        case_id=case_id,
        source_rules_document_id=f"diagnostic:m6d:{case_id}",
        offers=offers,
        h2_capability_skeleton={
            "scoring_structure": m14_h2_scoring_structure_dict_from_dao_criteria_rows(
                dao_rows
            )
        },
    )


def summarize_canonical_offer(offer: dict) -> dict:
    fields = offer.get("extracted_fields")
    if not isinstance(fields, list):
        fields = []
    evidence_map = offer.get("evidence_map")
    missing_fields = offer.get("missing_fields")
    line_items = offer.get("line_items")
    extraction_id = offer.get("extraction_id")
    identity_only = not extraction_id or not fields or not bool(evidence_map)

    return {
        "bundle_id": str(offer.get("document_id") or ""),
        "document_id": str(offer.get("document_id") or ""),
        "supplier_name": offer.get("supplier_name"),
        "extraction_id": str(extraction_id) if extraction_id else None,
        "extraction_ok": offer.get("extraction_ok") is True,
        "review_required": bool(offer.get("review_required", False)),
        "taxonomy_core": offer.get("taxonomy_core"),
        "family_main": offer.get("family_main"),
        "family_sub": offer.get("family_sub"),
        "extracted_fields_count": len(fields),
        "evidence_map_present": bool(evidence_map),
        "missing_fields_count": (
            len(missing_fields) if isinstance(missing_fields, list) else 0
        ),
        "line_items_count": len(line_items) if isinstance(line_items, list) else 0,
        "readiness_status": offer.get("readiness_status") or "unknown",
        "readiness_blockers": list(offer.get("readiness_blockers") or []),
        "readiness_warnings": list(offer.get("readiness_warnings") or []),
        "identity_only": identity_only,
    }


def m6d_forbidden_actions() -> dict[str, str]:
    return {
        "m14_evaluate": "NO",
        "run_pipeline_v5": "NO",
        "bridge": "NO",
        "matrix": "NO",
        "scoring": "NO",
        "db_update": "NO",
        "migration": "NO",
        "mistral_call": "NO",
        "enqueue": "NO",
        "winner_rank_recommendation": "NO",
    }


# FastAPI app
app = FastAPI(title="DMS Worker Railway", version="1.0.0")


# Auth dependency
def verify_token(authorization: str | None = Header(None)):
    """Verify bearer token (constant-time comparison)"""
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )
    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    if not hmac.compare_digest(token, WORKER_AUTH_TOKEN):
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    return token


# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with latency"""
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000

    log_structured(
        "INFO",
        f"{request.method} {request.url.path}",
        endpoint=request.url.path,
        status_code=response.status_code,
        latency_ms=round(latency_ms, 2),
    )

    return response


@app.get("/healthz")
async def healthz():
    """Public healthcheck for Railway (no auth required)"""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/health")
async def health(
    token: str = Header(None, alias="Authorization", include_in_schema=False)
):
    """Health check worker + DB reachability"""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()

        return {
            "status": "ok",
            "db": "reachable",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        log_exception("ERROR", "DB health check failed", e)
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "unreachable",
                "error": "Database health check failed",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@app.get("/db/ping")
async def db_ping(
    token: str = Header(None, alias="Authorization", include_in_schema=False)
):
    """Execute SELECT 1 + server timestamp"""
    verify_token(token)

    try:
        start = time.perf_counter()
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 AS ok, now() AS server_time")
                row = await cur.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "ok": row[0],
            "server_time": row[1].isoformat(),
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        log_exception("ERROR", "DB ping failed", e)
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/db/info")
async def db_info(
    token: str = Header(None, alias="Authorization", include_in_schema=False)
):
    """Get PostgreSQL version and database size"""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                # Get version
                await cur.execute("SELECT version()")
                version_row = await cur.fetchone()
                version = version_row[0]

                # Get database name and size
                await cur.execute("""
                    SELECT
                        current_database() AS db_name,
                        pg_database_size(current_database()) AS db_size_bytes,
                        pg_size_pretty(pg_database_size(current_database())) AS db_size_pretty
                """)
                size_row = await cur.fetchone()

        return {
            "version": version,
            "database_name": size_row[0],
            "database_size_bytes": size_row[1],
            "database_size_pretty": size_row[2],
        }
    except Exception as e:
        log_exception("ERROR", "DB info query failed", e)
        raise HTTPException(status_code=500, detail="Database query failed")


@app.post("/arq/enqueue/rehydrate", status_code=202)
async def enqueue_rehydrate(
    req: RehydrateEnqueueRequest,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
    arq_redis_url: str | None = Header(
        None, alias="X-ARQ-Redis-URL", include_in_schema=False
    ),
):
    """Enqueue the canonical document-level rehydration task.

    This endpoint only validates the existing bundle_document and queues an ARQ
    job. It never writes raw_text directly.
    """
    verify_token(token)
    redis_url = get_arq_redis_url(arq_redis_url)
    if not redis_url:
        status_flags = redis_config_status()
        status_flags["X_ARQ_REDIS_URL"] = bool(arq_redis_url)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ARQ Redis is not configured",
                "redis_config_present": status_flags,
            },
        )

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id::text,
                           workspace_id::text,
                           COALESCE(char_length(raw_text), 0) AS raw_text_len
                    FROM bundle_documents
                    WHERE id = %s::uuid
                      AND workspace_id = %s::uuid
                    """,
                    (str(req.document_id), str(req.workspace_id)),
                )
                row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="bundle_document not found")
        if int(row[2] or 0) > 0 and not req.force:
            raise HTTPException(
                status_code=409,
                detail="bundle_document already has raw_text; use force to overwrite",
            )
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "Rehydrate enqueue precheck failed", e)
        raise HTTPException(status_code=500, detail="Database precheck failed")

    try:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        try:
            job = await pool.enqueue_job(
                "rehydrate_bundle_document_raw_text_task",
                workspace_id=str(req.workspace_id),
                document_id=str(req.document_id),
                force=req.force,
            )
        finally:
            await pool.close()
        if job is None:
            raise HTTPException(
                status_code=409, detail="job already enqueued or duplicate"
            )
        log_structured(
            "INFO",
            "Rehydrate job enqueued",
            job_id=job.job_id,
            workspace_id=str(req.workspace_id),
            document_id=str(req.document_id),
            force=req.force,
        )
        return {
            "job_id": job.job_id,
            "function": "rehydrate_bundle_document_raw_text_task",
            "workspace_id": str(req.workspace_id),
            "document_id": str(req.document_id),
            "force": req.force,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "ARQ rehydrate enqueue failed", e)
        raise HTTPException(status_code=500, detail="ARQ enqueue failed")


@app.post("/arq/enqueue/m12-classify", status_code=202)
async def enqueue_m12_classify(
    req: M12ClassifyEnqueueRequest,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
    arq_redis_url: str | None = Header(
        None, alias="X-ARQ-Redis-URL", include_in_schema=False
    ),
):
    """Enqueue document-level M12 classification for an existing bundle_document."""
    verify_token(token)
    redis_url = get_arq_redis_url(arq_redis_url)
    if not redis_url:
        status_flags = redis_config_status()
        status_flags["X_ARQ_REDIS_URL"] = bool(arq_redis_url)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ARQ Redis is not configured",
                "redis_config_present": status_flags,
            },
        )

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id::text,
                           workspace_id::text,
                           COALESCE(char_length(raw_text), 0) AS raw_text_len,
                           m12_doc_kind
                    FROM bundle_documents
                    WHERE id = %s::uuid
                      AND workspace_id = %s::uuid
                    """,
                    (str(req.document_id), str(req.workspace_id)),
                )
                row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="bundle_document not found")
        if int(row[2] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="bundle_document raw_text is required before M12 classification",
            )
        if row[3] is not None and not req.force:
            raise HTTPException(
                status_code=409,
                detail="bundle_document already has m12_doc_kind; use force to reclassify",
            )
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "M12 classify enqueue precheck failed", e)
        raise HTTPException(status_code=500, detail="Database precheck failed")

    try:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        try:
            job = await pool.enqueue_job(
                "classify_bundle_document_m12_task",
                workspace_id=str(req.workspace_id),
                document_id=str(req.document_id),
                force=req.force,
            )
        finally:
            await pool.close()
        if job is None:
            raise HTTPException(
                status_code=409, detail="job already enqueued or duplicate"
            )
        log_structured(
            "INFO",
            "M12 classify job enqueued",
            job_id=job.job_id,
            workspace_id=str(req.workspace_id),
            document_id=str(req.document_id),
            force=req.force,
        )
        return {
            "job_id": job.job_id,
            "function": "classify_bundle_document_m12_task",
            "workspace_id": str(req.workspace_id),
            "document_id": str(req.document_id),
            "force": req.force,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "ARQ M12 classify enqueue failed", e)
        raise HTTPException(status_code=500, detail="ARQ enqueue failed")


@app.post("/arq/enqueue/bundle-gate-b-qualify", status_code=202)
async def enqueue_bundle_gate_b_qualify(
    req: BundleGateBEnqueueRequest,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
    arq_redis_url: str | None = Header(
        None, alias="X-ARQ-Redis-URL", include_in_schema=False
    ),
):
    """Enqueue Gate B qualification for an existing supplier_bundle."""
    verify_token(token)
    redis_url = get_arq_redis_url(arq_redis_url)
    if not redis_url:
        status_flags = redis_config_status()
        status_flags["X_ARQ_REDIS_URL"] = bool(arq_redis_url)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ARQ Redis is not configured",
                "redis_config_present": status_flags,
            },
        )

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT sb.id::text,
                           sb.workspace_id::text,
                           sb.gate_b_role,
                           COUNT(bd.id) AS doc_count,
                           COUNT(*) FILTER (
                               WHERE char_length(coalesce(bd.raw_text,'')) > 0
                           ) AS docs_with_text,
                           COUNT(*) FILTER (
                               WHERE bd.m12_doc_kind IS NOT NULL
                           ) AS docs_with_m12
                    FROM supplier_bundles sb
                    LEFT JOIN bundle_documents bd
                      ON bd.bundle_id = sb.id
                     AND bd.workspace_id = sb.workspace_id
                    WHERE sb.id = %s::uuid
                      AND sb.workspace_id = %s::uuid
                    GROUP BY sb.id
                    """,
                    (str(req.bundle_id), str(req.workspace_id)),
                )
                row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="supplier_bundle not found")
        if row[2] is not None and not req.force:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle already has gate_b_role; use force to re-evaluate",
            )
        if int(row[3] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires bundle_documents before Gate B qualification",
            )
        if int(row[4] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires raw_text before Gate B qualification",
            )
        if int(row[5] or 0) < int(row[4] or 0):
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires M12 on text documents before Gate B qualification",
            )
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "Gate B bundle enqueue precheck failed", e)
        raise HTTPException(status_code=500, detail="Database precheck failed")

    try:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        try:
            job = await pool.enqueue_job(
                "qualify_supplier_bundle_gate_b_task",
                workspace_id=str(req.workspace_id),
                bundle_id=str(req.bundle_id),
                force=req.force,
            )
        finally:
            await pool.close()
        if job is None:
            raise HTTPException(
                status_code=409, detail="job already enqueued or duplicate"
            )
        log_structured(
            "INFO",
            "Gate B bundle qualify job enqueued",
            job_id=job.job_id,
            workspace_id=str(req.workspace_id),
            bundle_id=str(req.bundle_id),
            force=req.force,
        )
        return {
            "job_id": job.job_id,
            "function": "qualify_supplier_bundle_gate_b_task",
            "workspace_id": str(req.workspace_id),
            "bundle_id": str(req.bundle_id),
            "force": req.force,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "ARQ Gate B bundle qualify enqueue failed", e)
        raise HTTPException(status_code=500, detail="ARQ enqueue failed")


@app.post("/arq/enqueue/bundle-offer-extract", status_code=202)
async def enqueue_bundle_offer_extract(
    req: BundleOfferExtractionEnqueueRequest,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
    arq_redis_url: str | None = Header(
        None, alias="X-ARQ-Redis-URL", include_in_schema=False
    ),
):
    """Enqueue offer extraction for one scorable supplier_bundle only."""
    verify_token(token)
    redis_url = get_arq_redis_url(arq_redis_url)
    if not redis_url:
        status_flags = redis_config_status()
        status_flags["X_ARQ_REDIS_URL"] = bool(arq_redis_url)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ARQ Redis is not configured",
                "redis_config_present": status_flags,
            },
        )

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT sb.id::text,
                           sb.workspace_id::text,
                           sb.gate_b_role,
                           COUNT(bd.id) AS doc_count,
                           COUNT(*) FILTER (
                               WHERE char_length(coalesce(bd.raw_text,'')) > 0
                           ) AS docs_with_text,
                           COUNT(*) FILTER (
                               WHERE char_length(coalesce(bd.raw_text,'')) > 0
                                 AND bd.m12_doc_kind IS NOT NULL
                           ) AS text_docs_with_m12,
                           COUNT(*) FILTER (
                               WHERE char_length(coalesce(bd.raw_text,'')) > 0
                                 AND (
                                     lower(coalesce(bd.m12_doc_kind,'')) IN (
                                         'offer',
                                         'quotation',
                                         'vendor_offer',
                                         'offer_technical',
                                         'offer_financial',
                                         'offer_combined'
                                     )
                                     OR lower(coalesce(bd.doc_type::text,'')) IN (
                                         'offer',
                                         'quotation',
                                         'vendor_offer',
                                         'offer_technical',
                                         'offer_financial',
                                         'offer_combined'
                                     )
                                 )
                           ) AS offer_docs_with_text,
                           COUNT(oe.id) AS existing_extractions
                    FROM supplier_bundles sb
                    LEFT JOIN bundle_documents bd
                      ON bd.bundle_id = sb.id
                     AND bd.workspace_id = sb.workspace_id
                    LEFT JOIN offer_extractions oe
                      ON oe.bundle_id = sb.id
                     AND oe.workspace_id = sb.workspace_id
                    WHERE sb.id = %s::uuid
                      AND sb.workspace_id = %s::uuid
                    GROUP BY sb.id
                    """,
                    (str(req.bundle_id), str(req.workspace_id)),
                )
                row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="supplier_bundle not found")
        if str(row[2] or "").strip().lower() != "scorable":
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle must have gate_b_role=scorable before offer extraction",
            )
        if int(row[7] or 0) > 0 and not req.force:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle already has offer_extractions; use force to re-extract",
            )
        if int(row[3] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires bundle_documents before offer extraction",
            )
        if int(row[4] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires raw_text before offer extraction",
            )
        if int(row[5] or 0) < int(row[4] or 0):
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires M12 on text documents before offer extraction",
            )
        if int(row[6] or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="supplier_bundle requires an offer document before offer extraction",
            )
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "Bundle offer extraction enqueue precheck failed", e)
        raise HTTPException(status_code=500, detail="Database precheck failed")

    try:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        try:
            job = await pool.enqueue_job(
                "extract_supplier_bundle_offer_task",
                workspace_id=str(req.workspace_id),
                bundle_id=str(req.bundle_id),
                force=req.force,
            )
        finally:
            await pool.close()
        if job is None:
            raise HTTPException(
                status_code=409, detail="job already enqueued or duplicate"
            )
        log_structured(
            "INFO",
            "Bundle offer extraction job enqueued",
            job_id=job.job_id,
            workspace_id=str(req.workspace_id),
            bundle_id=str(req.bundle_id),
            force=req.force,
        )
        return {
            "job_id": job.job_id,
            "function": "extract_supplier_bundle_offer_task",
            "workspace_id": str(req.workspace_id),
            "bundle_id": str(req.bundle_id),
            "force": req.force,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "ARQ bundle offer extraction enqueue failed", e)
        raise HTTPException(status_code=500, detail="ARQ enqueue failed")


@app.get(
    "/diagnostics/v1/workspaces/{workspace_id}/bundles/{bundle_id}/m4c-pre-snapshot"
)
async def m4c_bundle_pre_snapshot(
    workspace_id: UUID,
    bundle_id: UUID,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
):
    """Read-only M4C pre-extraction snapshot for one supplier_bundle."""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT sb.id::text AS bundle_id,
                           sb.vendor_name_raw,
                           sb.gate_b_role,
                           sb.completeness_score,
                           sb.missing_documents,
                           sb.qualification_status,
                           sb.is_retained,
                           COUNT(oe.id) AS offer_extractions_count
                    FROM supplier_bundles sb
                    LEFT JOIN offer_extractions oe
                      ON oe.bundle_id = sb.id
                     AND oe.workspace_id = sb.workspace_id
                    WHERE sb.id = %s::uuid
                      AND sb.workspace_id = %s::uuid
                    GROUP BY sb.id
                    """,
                    (str(bundle_id), str(workspace_id)),
                )
                bundle_row = await cur.fetchone()
                if bundle_row is None:
                    raise HTTPException(
                        status_code=404, detail="supplier_bundle not found"
                    )

                await cur.execute(
                    """
                    SELECT bd.id::text AS document_id,
                           char_length(coalesce(bd.raw_text,'')) AS raw_text_len,
                           md5(coalesce(bd.raw_text,'')) AS raw_text_md5,
                           bd.m12_doc_kind,
                           bd.m12_confidence
                    FROM bundle_documents bd
                    WHERE bd.workspace_id = %s::uuid
                      AND bd.bundle_id = %s::uuid
                    ORDER BY bd.uploaded_at NULLS LAST, bd.id::text
                    """,
                    (str(workspace_id), str(bundle_id)),
                )
                document_rows = await cur.fetchall()
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "M4C pre-snapshot query failed", e)
        raise HTTPException(status_code=500, detail="Database query failed")

    documents = [
        {
            "document_id": row[0],
            "raw_text_len": int(row[1] or 0),
            "raw_text_md5": row[2],
            "m12_doc_kind": row[3],
            "m12_confidence": float(row[4]) if row[4] is not None else None,
        }
        for row in document_rows
    ]
    return {
        "bundle": {
            "bundle_id": bundle_row[0],
            "vendor_name_raw": bundle_row[1],
            "gate_b_role": bundle_row[2],
            "completeness_score": (
                float(bundle_row[3]) if bundle_row[3] is not None else None
            ),
            "missing_documents": list(bundle_row[4] or []),
            "qualification_status": bundle_row[5],
            "is_retained": bool(bundle_row[6]),
        },
        "document": documents[0] if documents else None,
        "documents": documents,
        "offer_extractions_count": int(bundle_row[7] or 0),
    }


def build_m6d_builder_probe_payload(
    workspace_id: UUID,
    include_m14_input: bool = False,
    expected_offers_count: int | None = None,
) -> dict:
    workspace_id_str = str(workspace_id)
    builder_blockers: list[str] = []
    try:
        with open_m6d_readonly_connection() as conn:
            try:
                canonical_offers = build_canonical_m14_offers(conn, workspace_id_str)
            except Exception as exc:
                if not is_m14_offer_readiness_error(exc):
                    raise
                builder_blockers = list(getattr(exc, "blockers", []) or [str(exc)])
                canonical_offers = []

            dao_rows = fetch_m6d_rows(
                conn,
                """
                SELECT id::text AS id,
                       critere_nom,
                       COALESCE(ponderation, 0)::float AS ponderation,
                       COALESCE(is_eliminatory, false) AS is_eliminatory,
                       COALESCE(NULLIF(trim(categorie::text), ''), 'general') AS famille,
                       created_at
                FROM dao_criteria
                WHERE workspace_id = CAST(:wid AS uuid)
                ORDER BY categorie NULLS LAST, ponderation DESC NULLS LAST, id::text
                """,
                {"wid": workspace_id_str},
            )
            workspace_rows = fetch_m6d_rows(
                conn,
                """
                SELECT COALESCE(legacy_case_id::text, id::text) AS case_id
                FROM process_workspaces
                WHERE id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id_str},
            )
            evaluation_rows = fetch_m6d_rows(
                conn,
                """
                SELECT COUNT(*)::int AS n
                FROM evaluation_documents
                WHERE workspace_id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id_str},
            )
            assessment_rows = fetch_m6d_rows(
                conn,
                """
                SELECT COUNT(*)::int AS n
                FROM criterion_assessments
                WHERE workspace_id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id_str},
            )
            offer_ids = [
                str(offer.get("document_id"))
                for offer in canonical_offers
                if offer.get("document_id")
            ]
            if offer_ids:
                stale_rows = fetch_m6d_rows(
                    conn,
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM criterion_assessments
                        WHERE workspace_id = CAST(:wid AS uuid)
                          AND NOT (bundle_id::text = ANY(:bundle_ids::text[]))
                    ) AS stale
                    """,
                    {"wid": workspace_id_str, "bundle_ids": offer_ids},
                )
                stale_assessments_exist = bool(
                    stale_rows and stale_rows[0].get("stale")
                )
            else:
                stale_assessments_exist = bool(
                    assessment_rows and int(assessment_rows[0].get("n") or 0) > 0
                )
    except Exception as e:
        log_exception("ERROR", "M6D builder probe query failed", e)
        raise HTTPException(status_code=500, detail="Database query failed")

    offers = [summarize_canonical_offer(offer) for offer in canonical_offers]
    offers_count = len(offers)
    dao_criteria_count = len(dao_rows)
    dao_weights_total = sum(float(row.get("ponderation") or 0.0) for row in dao_rows)
    dao_weights_by_family: dict[str, float] = {}
    for row in dao_rows:
        family = str(row.get("famille") or "general")
        dao_weights_by_family[family] = dao_weights_by_family.get(family, 0.0) + float(
            row.get("ponderation") or 0.0
        )
    evaluation_documents_count = (
        int(evaluation_rows[0].get("n") or 0) if evaluation_rows else 0
    )
    criterion_assessments_count = (
        int(assessment_rows[0].get("n") or 0) if assessment_rows else 0
    )
    case_id = (
        str(workspace_rows[0].get("case_id"))
        if workspace_rows and workspace_rows[0].get("case_id")
        else workspace_id_str
    )

    input_blockers: list[str] = []
    input_warnings: list[str] = []
    input_blockers.extend(builder_blockers)
    if offers_count == 0:
        input_blockers.append("builder_returned_zero_offers")
    if expected_offers_count is not None and offers_count != expected_offers_count:
        input_blockers.append("offers_count_mismatch")
    if any(offer["identity_only"] for offer in offers):
        input_blockers.append("identity_only_offer_detected")
    if any(offer["readiness_blockers"] for offer in offers):
        input_blockers.append("offer_readiness_blockers_present")
    if dao_criteria_count != M6D_EXPECTED_DAO_CRITERIA_COUNT:
        input_blockers.append("dao_criteria_count_mismatch")
    if (
        abs(dao_weights_total - M6D_EXPECTED_DAO_WEIGHT_TOTAL)
        > M6D_DAO_WEIGHT_TOLERANCE
    ):
        input_blockers.append("dao_weights_total_mismatch")
    if evaluation_documents_count > 0:
        input_blockers.append("evaluation_documents_existing_skip_risk")
    if stale_assessments_exist or criterion_assessments_count > 0:
        input_blockers.append("criterion_assessments_historical_contamination_risk")
    for offer in offers:
        for warning in offer["readiness_warnings"]:
            if warning not in input_warnings:
                input_warnings.append(warning)

    m14_input_probe = None
    if include_m14_input:
        m14_input_constructed = False
        if not input_blockers:
            try:
                construct_m14_input_no_persist(case_id, canonical_offers, dao_rows)
                m14_input_constructed = True
            except Exception as exc:
                input_blockers.append(
                    f"m14_input_construction_failed:{type(exc).__name__}"
                )
        m14_input_probe = {
            "m14_input_constructed": m14_input_constructed,
            "offers_count": offers_count,
            "dao_criteria_count": dao_criteria_count,
            "dao_weights_total": dao_weights_total,
            "dao_weights_by_family": dao_weights_by_family,
            "input_ready": not input_blockers,
            "input_blockers": input_blockers,
            "input_warnings": input_warnings,
            "no_persist": True,
            "evaluation_engine_called": False,
            "repository_used": False,
            "created_artifacts": [],
        }

    return {
        "workspace_id": str(workspace_id),
        "runtime_commit": runtime_commit(),
        "offers_count": offers_count,
        "offers": offers,
        "stale_assessments_exist": stale_assessments_exist,
        "evaluation_documents_count": evaluation_documents_count,
        "criterion_assessments_count": criterion_assessments_count,
        "m14_input_probe": m14_input_probe,
        "forbidden_actions": m6d_forbidden_actions(),
    }


@app.get("/diagnostics/v1/workspaces/{workspace_id}/m6d-builder-probe")
async def m6d_builder_probe(
    workspace_id: UUID,
    include_m14_input: bool = False,
    expected_offers_count: int | None = None,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
):
    """Read-only M6D probe: enriched offers and no-persist M14 input readiness."""
    verify_token(token)
    return await asyncio.to_thread(
        build_m6d_builder_probe_payload,
        workspace_id,
        include_m14_input,
        expected_offers_count,
    )


@app.get("/bundle-documents/{document_id}/rehydration-state")
async def bundle_document_rehydration_state(
    document_id: UUID,
    workspace_id: UUID,
    token: str = Header(None, alias="Authorization", include_in_schema=False),
):
    """Read-only state check for the M1 rehydration gate."""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id::text,
                           workspace_id::text,
                           bundle_id::text,
                           filename,
                           COALESCE(char_length(raw_text), 0) AS raw_text_len,
                           ocr_engine,
                           m12_doc_kind,
                           m12_confidence,
                           extracted_at
                    FROM bundle_documents
                    WHERE id = %s::uuid
                      AND workspace_id = %s::uuid
                    """,
                    (str(document_id), str(workspace_id)),
                )
                row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="bundle_document not found")
        return {
            "id": row[0],
            "workspace_id": row[1],
            "bundle_id": row[2],
            "filename": row[3],
            "raw_text_len": row[4],
            "ocr_engine": row[5],
            "m12_doc_kind": row[6],
            "m12_confidence": float(row[7]) if row[7] is not None else None,
            "extracted_at": row[8].isoformat() if row[8] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception("ERROR", "Bundle document state query failed", e)
        raise HTTPException(status_code=500, detail="Database query failed")


@app.on_event("startup")
async def startup_event():
    """Test DB connection on startup"""
    log_structured("INFO", "Worker starting", port=PORT)
    try:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL, connect_timeout=5
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT version()")
                version = await cur.fetchone()
        log_structured("INFO", "DB connection test OK", version=version[0][:50])
    except Exception as e:
        log_exception("ERROR", "DB connection test FAILED on startup", e)
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=LOG_LEVEL.lower())
