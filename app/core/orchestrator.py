import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.chunker import chunk
from app.core.crawler import Crawler, CrawlOutput
from app.core.embedder import embed
from app.core.errors import AuditError, UrlSafetyError
from app.core.parser import ParsedPage, parse
from app.core.scorer import (
    HTTP_ERROR_MESSAGES,
    ScoreResult,
    UnreachablePage,
    score_page,
    score_site,
)
from app.core.scorer import ScoreResult as _ScoreResult  # noqa: F401  (re-export clarity)
from app.core.security import assert_url_safe
from app.core.semantic_scorer import (
    PageSemanticScore,
    score_chunks,
    score_semantic,
)


@dataclass
class OrchestrationResult:
    url: str
    overall_score: int
    semantic_score: int
    pages: list[ScoreResult]
    unreachable_pages: list[UnreachablePage]
    semantic_pages: list[PageSemanticScore]
    pages_crawled: int
    crawl_duration_seconds: float
    recommendations: list[str]
    findings: list[str]
    semantic_findings: list[str]
    semantic_recommendations: list[str]


async def orchestrate(
    seed_url: str,
    on_status_change: Callable[[str], Awaitable[None]] | None = None,
) -> OrchestrationResult:
    # Re-check the seed URL inside the worker: the job may have been created
    # before DNS changed, and the worker is the process that actually connects.
    try:
        await assert_url_safe(seed_url)
    except UrlSafetyError as exc:
        raise AuditError(str(exc)) from exc

    crawler = Crawler(seed_url)

    crawl_start = time.perf_counter()

    if on_status_change:
        await on_status_change("CRAWLING")

    crawl_output: CrawlOutput = await crawler.crawl()

    crawl_duration_seconds = time.perf_counter() - crawl_start

    parsed_pages: list[ParsedPage] = [parse(result) for result in crawl_output.results]

    scored_pages: list[ScoreResult] = []
    unreachable_pages: list[UnreachablePage] = [
        UnreachablePage(
            url=failure.url,
            status_code=failure.status_code,
            reason=HTTP_ERROR_MESSAGES.get(failure.status_code)
            or failure.detail
            or "The page could not be reached.",
        )
        for failure in crawl_output.failures
    ]

    if on_status_change:
        await on_status_change("SCORING")

    for page in parsed_pages:
        result: ScoreResult | UnreachablePage = score_page(page)
        if isinstance(result, ScoreResult):
            scored_pages.append(result)
        else:
            unreachable_pages.append(result)

    site_score_result = score_site(scored_pages)

    semantic_page_scores = []

    for page in parsed_pages:
        page_chunks = chunk(page)
        if not page_chunks:
            continue
        page_embeddings = embed(page_chunks)
        page_semantic_score = score_chunks(page.url, page_embeddings)
        semantic_page_scores.append(page_semantic_score)

    semantic_site_result = score_semantic(semantic_page_scores)

    return OrchestrationResult(
        url=seed_url,
        overall_score=site_score_result.overall_score,
        semantic_score=semantic_site_result.overall_score,
        crawl_duration_seconds=crawl_duration_seconds,
        pages=scored_pages,
        semantic_pages=semantic_site_result.page_scores,
        pages_crawled=len(crawl_output.results),
        unreachable_pages=unreachable_pages,
        findings=site_score_result.top_findings,
        recommendations=site_score_result.top_recommendations,
        semantic_findings=semantic_site_result.top_findings,
        semantic_recommendations=semantic_site_result.top_recommendations,
    )
