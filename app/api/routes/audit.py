from fastapi import APIRouter, HTTPException

from app.database import create_job, get_job
from app.worker.tasks import run_audit_task
from app.core.reporter import generate_report
from app.models.schemas import (
    AuditRequest,
    JobCreatedResponse,
    JobResponse,
)
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/audit", response_model=JobCreatedResponse)
async def run_audit(request: AuditRequest) -> JobCreatedResponse:
    logger.info(f"Audit requested for URL: {request.url}")

    try:
        seed_url = str(request.url)
        email = str(request.email)

        job_id = await create_job(seed_url, email)

        run_audit_task.delay(job_id, seed_url, email)

        return JobCreatedResponse(job_id=job_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occured during the audit. Please try again.",
        )


@router.get("/audit/{job_id}", response_model=JobResponse)
async def get_audit(job_id: str) -> JobResponse:
    try:
        job = await get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Audit job was not found."
            )
            
        return generate_report(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occured during the audit. Please try again.",
        )
