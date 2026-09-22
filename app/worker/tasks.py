import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone

import asyncpg
from celery.signals import worker_process_init

from app.config import get_settings
from app.core.errors import AuditError
from app.core.orchestrator import orchestrate
from app.logger import get_logger
from app.services.emailer import send_audit_complete_mail
from app.worker.celery_app import app as celery_app

logger = get_logger(__name__)
settings = get_settings()

GENERIC_FAILURE_MESSAGE = (
    "Something went wrong while auditing this website. Please try again."
)


@worker_process_init.connect
def preload_model(sender, **kwargs):
    from app.core.embedder import _get_model

    _get_model()
    logger.info("Embedding model preloaded and ready")


async def _update_job_status(
    pool: asyncpg.Pool, job_id: str, status: str, **kwargs
) -> None:
    if not pool:
        logger.error("DB pool is not initialized")
        raise RuntimeError("DB pool is not initialized")

    fields = {"status": status}
    fields.update(kwargs)

    set_parts: list[str] = []
    values: list[object] = []

    for column, value in fields.items():
        set_parts.append(f"{column} = ${len(values) + 1}")
        values.append(value)

    query = (
        "UPDATE jobs "
        f"SET {', '.join(set_parts)}, updated_at = NOW() "
        f"WHERE job_id = ${len(values) + 1}"
    )
    values.append(job_id)

    async with pool.acquire() as conn:
        await conn.execute(query, *values)


@celery_app.task(
    name="app.worker.tasks.run_audit_task",
    soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    time_limit=settings.TASK_TIME_LIMIT,
)
def run_audit_task(job_id: str, url: str, email: str | None):
    asyncio.run(_run_audit_async(job_id, url, email))


async def _run_audit_async(job_id: str, url: str, email: str | None) -> None:
    pool: asyncpg.Pool | None = None
    try:
        pool = await asyncpg.create_pool(
            settings.async_database_url,
            min_size=1,
            max_size=3,
        )
        await _update_job_status(pool, job_id, "STARTED")

        async def status_callback(status: str) -> None:
            await _update_job_status(pool, job_id, status)

        result = await orchestrate(url, status_callback)

        if result.pages_crawled == 0:
            raise AuditError(
                "The target website could not be reached. Please verify the URL and try again."
            )

        if not result.pages:
            raise AuditError(
                "All pages on the domain were blocked from crawling. Check robots.txt restrictions."
            )

        logger.info("Audit %s completed for %s", job_id, url)

        await _update_job_status(
            pool,
            job_id,
            "SUCCESS",
            url=url,
            result=json.dumps(asdict(result)),
            completed_at=datetime.now(timezone.utc),
        )

        if email:
            # Email is strictly a notification. A failure here must never
            # turn a successful audit into a failed one.
            send_audit_complete_mail(to_email=email, job_id=job_id, result=result)
            logger.debug("Completion email sent for audit %s", job_id)
    except AuditError as exc:
        logger.warning("Audit %s aborted: %s", job_id, exc)
        await _mark_failure(pool, job_id, str(exc))
    except Exception as exc:
        logger.exception("Audit %s failed for %s", job_id, url)
        await _mark_failure(pool, job_id, GENERIC_FAILURE_MESSAGE)
    finally:
        if pool is not None:
            await pool.close()


async def _mark_failure(
    pool: asyncpg.Pool | None, job_id: str, message: str
) -> None:
    if pool is None:
        return
    try:
        await _update_job_status(
            pool,
            job_id,
            "FAILURE",
            error_message=message,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to update job %s to FAILURE: %s", job_id, exc)