from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.database as database
from app.api.dependencies import close_redis_client, get_redis_client
from app.api.routes import audit as audit_routes
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await database.connect()
    except Exception as exc:
        # Availability over strictness: a briefly-unreachable database at boot
        # should not take the whole API down. /ready reports the gap and the
        # pool stays None until the next successful connect.
        logger.warning("Database unavailable at startup (%s); API will start.", exc)
    try:
        await get_redis_client()
    except Exception as exc:
        logger.warning("Redis unavailable at startup (%s); will retry lazily.", exc)
    yield
    await close_redis_client()
    await database.disconnect()


app = FastAPI(
    title="Marrai AEO Audit API",
    description=(
        "Free website audit API that crawls a site and scores its readiness "
        "for AI / answer-engine retrieval (metadata, structure, structured "
        "data, connectivity, technical compliance, and semantic alignment)."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Accept",
        "X-Proxy-Secret",
        "X-Client-IP",
    ],
)

app.include_router(audit_routes.router, prefix="/api/v1", tags=["audit"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/ready")
async def readiness_check():
    """Verify critical runtime dependencies without exposing any secrets."""
    checks: dict[str, bool] = {"database": False, "redis": False}

    try:
        pool = database.db_pool
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                checks["database"] = True
    except Exception as exc:
        logger.warning("Readiness database check failed: %s", exc)

    try:
        client = await get_redis_client()
        checks["redis"] = bool(await client.ping())
    except Exception as exc:
        logger.warning("Readiness redis check failed: %s", exc)

    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    return {"status": "unavailable", "checks": checks}