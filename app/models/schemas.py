from datetime import datetime, timezone
from pydantic import BaseModel, HttpUrl, Field

from app.models.jobs import JobStatus


class AuditRequest(BaseModel):
    url: HttpUrl


class CategoryScoreResponse(BaseModel):
    score: int
    max_possible: int
    metrics: dict[str, int]
    findings: list[str]
    recommendations: list[str]


class PageResponse(BaseModel):
    url: str
    overall_score: int
    metadata: CategoryScoreResponse
    content_quality: CategoryScoreResponse
    structured_data: CategoryScoreResponse
    connectivity: CategoryScoreResponse
    technical_compliance: CategoryScoreResponse


class UnreachablePageResponse(BaseModel):
    url: str
    status_code: int
    reason: str

class ChunkSemanticScoreResponse(BaseModel):
    heading: str
    section_position: int
    alignment_score: int
    finding: str | None
    recommendation: str | None

class PageSemanticScoreResponse(BaseModel):
    url: str
    overall_score: int
    section_scores: list[ChunkSemanticScoreResponse]
    finding: str | None
    recommendation: str | None

class AuditResponse(BaseModel):
    url: str
    pages_crawled: int
    overall_score: int
    semantic_score: int
    findings: list[str]
    recommendations: list[str]
    semantic_findings: list[str]
    semantic_recommendations: list[str]
    pages: list[PageResponse]
    semantic_pages: list[PageSemanticScoreResponse]
    unreachable_pages: list[UnreachablePageResponse]
    crawl_duration_seconds: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobResponse(BaseModel):
    job_id: str
    url: str
    status: JobStatus
    result: AuditResponse | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None
    completed_at: datetime | None


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = "pending"
