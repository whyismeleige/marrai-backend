from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field

class AuditRequest(BaseModel):
    url: HttpUrl
    
class AuditResponse(BaseModel):
    url: str
    pages_crawled: int
    overall_score: float
    findings: list[str]
    recommendations: list[str]
    crawl_duration_seconds: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
