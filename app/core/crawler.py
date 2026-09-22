import asyncio
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.core.errors import UrlSafetyError
from app.core.security import assert_url_safe
from app.core.utils import normalize_url
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}

# Common asset extensions are skipped before fetching so the crawler never
# downloads binaries it cannot parse as HTML.
NON_HTML_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z",
    ".css", ".js", ".mjs", ".map", ".json", ".xml", ".rss", ".atom",
    ".mp3", ".mp4", ".webm", ".wav", ".ogg", ".mov",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
    ".exe", ".dmg", ".iso", ".bin", ".apk",
}

REDIRECT_STATUSES = {301, 302, 303, 307, 308}


@dataclass
class CrawlResult:
    url: str
    html: str
    status_code: int


@dataclass
class FetchFailure:
    url: str
    status_code: int
    detail: str = ""


@dataclass
class CrawlOutput:
    results: list[CrawlResult] = field(default_factory=list)
    failures: list[FetchFailure] = field(default_factory=list)


class Crawler:
    def __init__(self, seed_url: str, limit: int | None = None):
        self.seed_url = seed_url
        self.limit = limit if limit is not None else settings.CRAWL_LIMIT

        self.visited: set[str] = set()
        self.queue: deque[str] = deque()
        self.results: list[CrawlResult] = []
        self.failures: list[FetchFailure] = []

        parsed = urlparse(seed_url)
        self.domain = parsed.hostname
        self.scheme = parsed.scheme or "https"

        self.robot_parser = RobotFileParser()
        self._semaphore = asyncio.Semaphore(settings.CRAWL_CONCURRENCY)

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            settings.CRAWL_TIMEOUT,
            connect=settings.CRAWL_CONNECT_TIMEOUT,
            pool=settings.CRAWL_CONNECT_TIMEOUT,
        )
        return httpx.AsyncClient(
            headers={
                "User-Agent": settings.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
            timeout=timeout,
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=settings.CRAWL_CONCURRENCY + 2,
                max_keepalive_connections=settings.CRAWL_CONCURRENCY,
            ),
        )

    def _in_scope(self, url: str) -> bool:
        try:
            host = urlparse(url).hostname
        except ValueError:
            return False
        return bool(host) and host == self.domain

    @staticmethod
    def _is_non_html_asset(url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in NON_HTML_EXTENSIONS)

    async def _load_robots(self, client: httpx.AsyncClient) -> None:
        robots_url = f"{self.scheme}://{self.domain}/robots.txt"

        # Baseline: unless a real robots.txt is parsed below, allow everything.
        # A freshly-constructed RobotFileParser treats every URL as disallowed,
        # which would silently block crawling any site without a robots.txt.
        self.robot_parser.parse([])

        try:
            for _ in range(3):
                await assert_url_safe(robots_url)
                if not self._in_scope(robots_url):
                    return
                response = await client.get(
                    robots_url, timeout=min(settings.CRAWL_TIMEOUT, 10)
                )
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        return
                    robots_url = urljoin(robots_url, location)
                    continue
                if response.status_code == 200:
                    self.robot_parser.parse(response.text.splitlines())
                    logger.info("Loaded robots.txt from %s", robots_url)
                return
        except (UrlSafetyError, httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Could not load robots.txt for %s (%s). Proceeding without it.",
                self.domain,
                exc,
            )

    def _is_allowed(self, url: str) -> bool:
        try:
            return self.robot_parser.can_fetch(settings.USER_AGENT, url)
        except Exception:
            return True

    async def _read_body(self, response: httpx.Response) -> str | None:
        limit = settings.CRAWL_MAX_BODY_BYTES
        chunks: list[bytes] = []
        total = 0

        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > limit:
                return None
            chunks.append(chunk)

        raw = b"".join(chunks)
        encoding = response.charset_encoding or "utf-8"
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")

    async def _fetch(
        self, url: str, client: httpx.AsyncClient
    ) -> CrawlResult | FetchFailure | None:
        """Fetch one URL. Returns None when the URL is deliberately skipped."""
        current_url = url

        for _ in range(settings.CRAWL_MAX_REDIRECTS + 1):
            if not self._in_scope(current_url) or self._is_non_html_asset(current_url):
                return None

            try:
                # Re-validated per hop so redirects cannot pivot into
                # private infrastructure (and to reduce DNS-rebinding risk).
                await assert_url_safe(current_url)
            except UrlSafetyError as exc:
                logger.warning("Blocked unsafe crawl target %s: %s", current_url, exc)
                return None

            try:
                async with self._semaphore:
                    async with client.stream("GET", current_url) as response:
                        if response.status_code in REDIRECT_STATUSES:
                            location = response.headers.get("location")
                            if not location:
                                return FetchFailure(
                                    url, response.status_code, "The redirect had no destination."
                                )
                            current_url = urljoin(current_url, location)
                            continue

                        if response.status_code != 200:
                            return FetchFailure(url, response.status_code)

                        content_type = (
                            response.headers.get("content-type", "")
                            .split(";")[0]
                            .strip()
                            .lower()
                        )
                        if content_type and content_type not in HTML_CONTENT_TYPES:
                            logger.debug(
                                "Skipping non-HTML resource %s (%s)",
                                current_url,
                                content_type,
                            )
                            return None

                        html = await self._read_body(response)
                        if html is None:
                            return FetchFailure(
                                url, 0, "The page exceeded the maximum allowed size."
                            )

                        return CrawlResult(
                            url=current_url, html=html, status_code=200
                        )

            except httpx.TimeoutException:
                logger.warning("Timeout fetching %s", current_url)
                return FetchFailure(url, 0, "The request timed out.")
            except httpx.TooManyRedirects:
                return FetchFailure(url, 0, "The page had too many redirects.")
            except httpx.HTTPError as exc:
                logger.warning("Error fetching %s: %s", current_url, exc)
                return FetchFailure(url, 0, "The website could not be reached.")
            except ValueError as exc:
                logger.warning("Invalid URL %s: %s", current_url, exc)
                return None

        return FetchFailure(url, 0, "The page had too many redirects.")

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")

        links: list[str] = []
        for tag in soup.find_all("a", href=True):
            link = normalize_url(tag["href"], base_url)
            if link is not None:
                links.append(link)
        return links

    async def crawl(self) -> CrawlOutput:
        normalized_url = normalize_url(self.seed_url, self.seed_url)
        if not normalized_url:
            return CrawlOutput(results=self.results, failures=self.failures)

        self.queue.append(normalized_url)
        self.visited.add(normalized_url)

        async with self._build_client() as client:
            await self._load_robots(client)

            while self.queue and len(self.results) < self.limit:
                batch: list[str] = []
                while (
                    self.queue
                    and len(batch) < settings.CRAWL_CONCURRENCY
                    and len(self.results) + len(batch) < self.limit
                ):
                    url = self.queue.popleft()
                    if self._is_allowed(url):
                        batch.append(url)

                if not batch:
                    continue

                fetched = await asyncio.gather(
                    *(self._fetch(url, client) for url in batch)
                )

                for item in fetched:
                    if item is None:
                        continue
                    if isinstance(item, FetchFailure):
                        self.failures.append(item)
                        continue

                    self.results.append(item)
                    for link in self._extract_links(item.html, item.url):
                        if link in self.visited:
                            continue
                        self.visited.add(link)
                        self.queue.append(link)

        logger.info(
            "Crawl complete for %s -- %d pages fetched, %d unreachable",
            self.seed_url,
            len(self.results),
            len(self.failures),
        )
        return CrawlOutput(results=self.results, failures=self.failures)
