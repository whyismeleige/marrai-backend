import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import rate_limit_check
from app.core.errors import UrlSafetyError
from app.core.reporter import generate_report
from app.core.security import assert_url_safe
from app.database import create_job, get_job
from app.logger import get_logger
from app.models.schemas import AuditRequest, JobCreatedResponse, JobResponse
from app.worker.tasks import run_audit_task

logger = get_logger(__name__)

router = APIRouter()


@router.post("/audit", response_model=JobCreatedResponse)
async def run_audit(
    request: AuditRequest,
    _client_ip: str = Depends(rate_limit_check),
) -> JobCreatedResponse:
    seed_url = str(request.url)
    email = request.email

    logger.info("Audit requested for URL: %s", seed_url)

    # Reject private/internal destinations before anything is persisted.
    try:
        await assert_url_safe(seed_url)
    except UrlSafetyError as exc:
        logger.info("Rejected audit request for unsafe URL (%s)", exc.code)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        job_id = await create_job(seed_url, email)
        run_audit_task.delay(job_id, seed_url, email)
        return JobCreatedResponse(job_id=job_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create audit job for %s", seed_url)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while creating your audit. Please try again.",
        ) from exc


@router.get("/audit/{job_id}", response_model=JobResponse)
async def get_audit(job_id: str) -> JobResponse:
    if _is_valid_uuid(job_id) is False:
        raise HTTPException(
            status_code=422, detail="That audit id does not look valid."
        )

    try:
        job = await get_job(job_id)
    except Exception as exc:
        logger.exception("Failed to load audit job %s", job_id)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while loading your audit. Please try again.",
        ) from exc

    if not job:
        raise HTTPException(status_code=404, detail="Audit job was not found.")

    return generate_report(job)


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False