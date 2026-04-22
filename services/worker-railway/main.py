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
from datetime import datetime, timezone
from typing import Optional

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Windows async fix for psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load .env file
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
WORKER_AUTH_TOKEN = os.getenv("WORKER_AUTH_TOKEN")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
if not WORKER_AUTH_TOKEN:
    raise ValueError("WORKER_AUTH_TOKEN environment variable is required")

# Logging structuré JSON
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def log_structured(level: str, message: str, **kwargs):
    """Log structured JSON to stdout"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **kwargs
    }
    logger.log(getattr(logging, level.upper()), json.dumps(log_entry))


# FastAPI app
app = FastAPI(title="DMS Worker Railway", version="1.0.0")


# Auth dependency
def verify_token(authorization: Optional[str] = Header(None)):
    """Verify bearer token (constant-time comparison)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    if not hmac.compare_digest(token, WORKER_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

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
        latency_ms=round(latency_ms, 2)
    )

    return response


@app.get("/health")
async def health(token: str = Header(None, alias="Authorization", include_in_schema=False)):
    """Health check worker + DB reachability"""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, connect_timeout=5) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()

        return {
            "status": "ok",
            "db": "reachable",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        log_structured("ERROR", "DB health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "unreachable",
                "error": str(e)[:200],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@app.get("/db/ping")
async def db_ping(token: str = Header(None, alias="Authorization", include_in_schema=False)):
    """Execute SELECT 1 + server timestamp"""
    verify_token(token)

    try:
        start = time.perf_counter()
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, connect_timeout=5) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 AS ok, now() AS server_time")
                row = await cur.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "ok": row[0],
            "server_time": row[1].isoformat(),
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        log_structured("ERROR", "DB ping failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)[:200]}")


@app.get("/db/info")
async def db_info(token: str = Header(None, alias="Authorization", include_in_schema=False)):
    """Get PostgreSQL version and database size"""
    verify_token(token)

    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, connect_timeout=5) as conn:
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
            "database_size_pretty": size_row[2]
        }
    except Exception as e:
        log_structured("ERROR", "DB info query failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)[:200]}")


@app.on_event("startup")
async def startup_event():
    """Test DB connection on startup"""
    log_structured("INFO", "Worker starting", port=PORT)
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, connect_timeout=5) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT version()")
                version = await cur.fetchone()
        log_structured("INFO", "DB connection test OK", version=version[0][:50])
    except Exception as e:
        log_structured("ERROR", "DB connection test FAILED on startup", error=str(e))
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=LOG_LEVEL.lower())
