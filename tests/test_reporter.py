import json
import uuid
from datetime import datetime, timezone

from app.core.reporter import generate_report

_JOB_ID = str(uuid.uuid4())


def _result_dict() -> dict:
    return {
        "url": "https://example.com",
        "pages_crawled": 2,
        "overall_score": 71,
        "semantic_score": 78,
        "findings": ["Missing author metadata."],
        "recommendations": ["Add author metadata."],
        "semantic_findings": [],
        "semantic_recommendations": [],
        "pages": [],
        "semantic_pages": [],
        "unreachable_pages": [{"url": "https://example.com/secret", "status_code": 404, "reason": "Not Found"}],
        "crawl_duration_seconds": 1.5,
    }


def _job(result, status="SUCCESS"):
    return {
        "job_id": _JOB_ID,
        "url": "https://example.com",
        "status": status,
        "result": result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "completed_at": datetime.now(timezone.utc),
    }


def test_string_result_is_parsed_and_normalized():
    job = _job(json.dumps(_result_dict()))
    report = generate_report(job)
    assert report.status.value == "success"
    assert report.result is not None
    assert report.result.overall_score == 71
    assert report.result.unreachable_pages[0].status_code == 404
    assert report.job_id == _JOB_ID


def test_dict_result_is_accepted():
    job = _job(_result_dict())
    report = generate_report(job)
    assert report.result.pages_crawled == 2


def test_missing_result_stays_null():
    report = generate_report(_job(None, status="FAILURE"))
    assert report.result is None
    assert report.error_message is None