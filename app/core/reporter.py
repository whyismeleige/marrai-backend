import json

from asyncpg import Record

from app.models.schemas import AuditResponse, JobResponse


def _parse_result(raw_result: object) -> dict | None:
    if raw_result is None:
        return None
    if isinstance(raw_result, dict):
        return raw_result
    try:
        return json.loads(raw_result)
    except (ValueError, TypeError):
        return None


def generate_report(job: Record) -> JobResponse:
    result_data = _parse_result(job["result"])

    return JobResponse(
        job_id=str(job["job_id"]),
        url=job["url"],
        status=str(job["status"]).lower(),
        result=AuditResponse(**result_data) if result_data else None,
        error_message=job["error_message"] or None,
        created_at=job["created_at"],
        updated_at=job["updated_at"] or None,
        completed_at=job["completed_at"] or None,
    )