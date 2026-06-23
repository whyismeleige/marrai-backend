import uuid
import asyncpg

from app.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

db_pool = None


async def connect():
    global db_pool
    if not db_pool:
        db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL, min_size=1, max_size=5
        )
        logger.info("DB Pool created.")


async def disconnect():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("DB pool closed.")


async def create_job(url: str, email: str) -> str:
    global db_pool

    if not db_pool:
        logger.error("DB pool is not initialized")
        raise RuntimeError("DB pool is not initialized")

    async with db_pool.acquire() as conn:
        job_id = await conn.fetchval(
            "INSERT INTO jobs (job_id, url, email, status) VALUES ($1, $2, $3, $4) RETURNING job_id",
            uuid.uuid4(), url, email, "PENDING"
        )
        return str(job_id)

async def get_job(job_id: str) -> asyncpg.Record | None:
    global db_pool

    if not db_pool:
        logger.error("DB pool is not initialized")
        raise RuntimeError("DB pool is not initialized")

    async with db_pool.acquire() as conn:
        job = await conn.fetchrow(
            "SELECT * FROM jobs where job_id = $1",
            uuid.UUID(job_id)
        )    
        return job
