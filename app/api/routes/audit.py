from fastapi import APIRouter
from app.models.schemas import AuditRequest, AuditResponse
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/audit", response_model=AuditResponse)
async def run_audit(request: AuditRequest) -> AuditResponse:
    logger.info(f"Audit requested for URL: {request.url}")
    
    return AuditResponse(
        url=str(request.url),
        pages_crawled=0,
        overall_score=0.0,
        findings=["Audit pipeline not yet implemented"],
        recommendations=["Come back soon"],
        crawl_duration_seconds=0.0,
    )