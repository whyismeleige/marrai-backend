import time
from dataclasses import dataclass
from collections import Counter
from collections.abc import Callable, Awaitable

from app.core.crawler import Crawler, CrawlResult
from app.core.parser import parse, ParsedPage
from app.core.scorer import score_page, ScoreResult, UnreachablePage


@dataclass
class OrchestrationResult:
    url: str
    overall_score: int
    pages: list[ScoreResult]
    unreachable_pages: list[UnreachablePage]
    pages_crawled: int
    crawl_duration_seconds: float
    recommendations: list[str]
    findings: list[str]


async def orchestrate(seed_url: str, on_status_change: Callable[[str], Awaitable[None]] | None = None) -> OrchestrationResult:
    crawler = Crawler(seed_url)

    crawl_start = time.perf_counter()
    
    if on_status_change:
        await on_status_change("CRAWLING")

    crawl_results: list[CrawlResult] = await crawler.crawl()

    crawl_duration_seconds = time.perf_counter() - crawl_start

    parsed_pages: list[ParsedPage] = [parse(result) for result in crawl_results]

    scored_pages: list[ScoreResult] = []
    unreachable_pages: list[UnreachablePage] = []
    
    if on_status_change:
        await on_status_change("SCORING")

    for page in parsed_pages:
        result: ScoreResult | UnreachablePage = score_page(page)
        if isinstance(result, ScoreResult):
            scored_pages.append(result)
        else:
            unreachable_pages.append(result)

    site_score = (
        round(sum(page.overall_score for page in scored_pages) / len(scored_pages))
        if scored_pages
        else 0
    )

    all_findings = []
    all_recommendations = []

    for page in scored_pages:
        for category in [
            page.structured_data,
            page.connectivity,
            page.content_quality,
            page.technical_compliance,
            page.metadata,
        ]:
            all_findings.extend(category.findings)
            all_recommendations.extend(category.recommendations)

    top_findings = [finding for finding, _ in Counter(all_findings).most_common(5)]
    top_recommendations = [
        recommendation
        for recommendation, _ in Counter(all_recommendations).most_common(5)
    ]

    return OrchestrationResult(
        url=seed_url,
        overall_score=site_score,
        crawl_duration_seconds=crawl_duration_seconds,
        pages=scored_pages,
        pages_crawled=len(crawl_results),
        unreachable_pages=unreachable_pages,
        findings=top_findings,
        recommendations=top_recommendations,
    )
