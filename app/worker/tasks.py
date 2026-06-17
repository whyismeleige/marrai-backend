import asyncio
from typing import Any
from dataclasses import asdict
from datetime import datetime, timezone

import asyncpg
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import get_settings
from app.logger import get_logger
from app.core.orchestrator import orchestrate
from app.worker.celery_app import app as celery_app

logger = get_logger(__name__)
settings = get_settings()

db_pool = None


async def _update_job_status(job_id: str, status: str, **kwargs):
    global db_pool

    if not db_pool:
        logger.error("DB pool is not initialized")
        raise RuntimeError("DB pool is not initialized")

    fields = {"status": status}
    fields.update(kwargs)

    set_parts = []
    values = []

    for i, (column, value) in enumerate(fields.items(), start=1):
        set_parts.append(f"{column} = ${i}")
        values.append(value)

    job_id_placeholder = f"${len(values) +  1}"

    query = f"""
        UPDATE jobs
        SET {", ".join(set_parts)}, updated_at = NOW()
        WHERE job_id = {job_id_placeholder}
    """

    values.append(job_id)

    async with db_pool.acquire() as conn:
        await conn.execute(query, *values)


@worker_process_init.connect
def init_worker_process(**kwargs):
    asyncio.run(_connect_pool())


async def _connect_pool():
    global db_pool
    if not db_pool:
        db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL, min_size=1, max_size=3
        )
        logger.info("DB Pool created.")


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    asyncio.run(_disconnect_pool())


async def _disconnect_pool():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("DB Pool closed.")


@celery_app.task()
def run_audit(job_id: str, url: str):
    asyncio.run(_run_audit_async(job_id, url))


async def _run_audit_async(job_id: str, url: str):
    try:
        await _update_job_status(job_id, "STARTED")

        async def status_callback(status):
            await _update_job_status(job_id, status)

        result = await orchestrate(url, status_callback)

        if result.pages_crawled == 0:
            raise Exception(
                "The target website could not be reached. Please verify the URL and try again."
            )

        if not result.pages:
            raise Exception(
                "All pages on the domain were blocked from crawling. Check robots.txt restrictions."
            )

        logger.info(f"{url} task completed")

        return await _update_job_status(
            job_id,
            "SUCCESS",
            url=url,
            result=asdict(result),
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        try:
            await _update_job_status(
                job_id,
                "FAILURE",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as db_error:
            logger.error(f"Failed to update job status to FAILURE; {db_error}")
