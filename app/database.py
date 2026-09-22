import uuid

import asyncpg

from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

db_pool: asyncpg.Pool | None = None


async def connect() -> None:
    global db_pool
    if not db_pool:
        db_pool = await asyncpg.create_pool(
            settings.async_database_url, min_size=1, max_size=5
        )
        logger.info("DB pool created.")


async def disconnect() -> None:
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
        logger.info("DB pool closed.")


def _require_pool() -> asyncpg.Pool:
    if not db_pool:
        logger.error("DB pool is not initialized")
        raise RuntimeError("DB pool is not initialized")
    return db_pool


async def create_job(url: str, email: str | None) -> str:
    pool = _require_pool()
    async with pool.acquire() as conn:
        job_id = await conn.fetchval(
            "INSERT INTO jobs (job_id, url, email, status) "
            "VALUES ($1, $2, $3, $4) RETURNING job_id",
            uuid.uuid4(),
            url,
            email,
            "PENDING",
        )
        return str(job_id)


async def get_job(job_id: str) -> asyncpg.Record | None:
    pool = _require_pool()
    try:
        parsed_id = uuid.UUID(job_id)
    except (ValueError, AttributeError, TypeError):
        return None

    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM jobs WHERE job_id = $1", parsed_id)
