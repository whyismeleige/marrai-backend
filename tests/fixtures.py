from app.core.orchestrator import OrchestrationResult
from app.core.scorer import ScoreResult, CategoryScore, UnreachablePage

fake_category = CategoryScore(
    score=80,
    max_possible=100,
    metrics={"test": 80},
    findings=["Good"],
    recommendations=[],
)

fake_page = ScoreResult(
    url="https://example.com",
    overall_score=80,
    metadata=fake_category,
    content_quality=fake_category,
    structured_data=fake_category,
    connectivity=fake_category,
    technical_compliance=fake_category,
)

fake_result = OrchestrationResult(
    url="https://example.com",
    site_score=80,
    pages=[fake_page],
    unreachable_pages=[],
    pages_crawled=1,
    crawl_duration_seconds=1.5,
    findings=["Good content"],
    recommendations=["Add schema"],
)

fake_empty_result = OrchestrationResult(
    url="https://example.com",
    site_score=0,
    pages=[],
    unreachable_pages=[],
    pages_crawled=0,
    crawl_duration_seconds=1.0,
    findings=[],
    recommendations=[],
)

fake_blocked_result = OrchestrationResult(
    url="https://example.com",
    site_score=0,
    pages=[],
    unreachable_pages=[
        UnreachablePage(
            url="https://example.com", status_code=403, reason="Forbidden Page"
        )
    ],
    pages_crawled=1,
    crawl_duration_seconds=1.0,
    findings=[],
    recommendations=[],
)
