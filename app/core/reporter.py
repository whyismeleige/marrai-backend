import json

from asyncpg import Record

from app.models.schemas import JobResponse, AuditResponse


def generate_report(job: Record) -> JobResponse:
    result_data = json.loads(job["result"]) if job["result"] else None
    return JobResponse(
        job_id=str(job["job_id"]),
        url=job["url"],
        status=job["status"].lower(),
        result=AuditResponse(**result_data) if result_data else None,
        error_message=job["error_message"] if job["error_message"] else None,
        created_at=job["created_at"],
        updated_at=job["updated_at"] if job["updated_at"] else None,
        completed_at=job["completed_at"] if job["completed_at"] else None,
    )
