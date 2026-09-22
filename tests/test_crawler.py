from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import get_settings
from app.core.crawler import Crawler


@pytest.fixture
def crawler():
    return Crawler(seed_url="https://example.com")


@pytest.mark.parametrize("html, base_url, expected", [
    ("""
    <html>
        <body>
            <a href="/about">About</a>
            <a href="/blog">Blog</a>
        </body>
    </html>
    """, "https://example.com", ["https://example.com/about", "https://example.com/blog"]),
    ("""
    <html>
        <body>
            <a href="/about">About</a>
            <a href="/blog">Blog</a>
            <a href="https://google.com">Google</a>
        </body>
    </html>
    """, "https://example.com", ["https://example.com/about", "https://example.com/blog"]),
    ("""
    <html>
        <body>
            <a href="/about">About</a>
            <a href="">Blog</a>
        </body>
    </html>
    """, "https://example.com", ["https://example.com/about", "https://example.com"]),
    ("""
    <html>
        <body>
        </body>
    </html>
    """, "https://example.com", []),
])
def test_extract_links(crawler, html, base_url, expected):
    result = crawler._extract_links(html, base_url)
    assert result == expected


def _html(title, extra_body=""):
    return f"<html><head><title>{title}</title></head><body>{extra_body}</body></html>"


def _default_handler(path):
    if path == "/robots.txt":
        return httpx.Response(404)
    if path == "/":
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=_html("Home", "<a href='/about'>About</a>"),
        )
    if path == "/asset.gif":
        return httpx.Response(200, headers={"content-type": "image/gif"}, text="GIF89a")
    return httpx.Response(
        200, headers={"content-type": "text/html"}, text=_html(path)
    )


def _mock_client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: handler(request.url.path)),
        follow_redirects=False,
    )


async def _crawl_with(handler, monkeypatch, seed="https://example.com"):
    monkeypatch.setattr("app.core.crawler.assert_url_safe", AsyncMock())
    crawler = Crawler(seed)
    crawler._build_client = lambda: _mock_client(handler)
    return await crawler.crawl()


@pytest.mark.asyncio
async def test_crawl_fetches_home_and_extracted_link(monkeypatch):
    output = await _crawl_with(_default_handler, monkeypatch)
    assert len(output.results) == 2
    urls = {r.url for r in output.results}
    assert "https://example.com" in urls
    assert "https://example.com/about" in urls
    assert output.failures == []


@pytest.mark.asyncio
async def test_out_of_scope_redirect_is_skipped(monkeypatch):
    def handler(path):
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/":
            return httpx.Response(302, headers={"location": "https://evil.com/"})
        return httpx.Response(200, headers={"content-type": "text/html"})

    output = await _crawl_with(handler, monkeypatch)
    assert output.results == []
    assert output.failures == []


@pytest.mark.asyncio
async def test_unreachable_page_is_recorded(monkeypatch):
    def handler(path):
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=_html("Home", "<a href='/missing'>x</a>"),
            )
        return httpx.Response(404, headers={"content-type": "text/html"})

    output = await _crawl_with(handler, monkeypatch)
    failing = [f for f in output.failures if f.url.endswith("/missing")]
    assert len(failing) == 1
    assert failing[0].status_code == 404


@pytest.mark.asyncio
async def test_asset_links_are_never_fetched(monkeypatch):
    def handler(path):
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=_html("Home", "<a href='/asset.gif'>img</a>"),
            )
        return httpx.Response(200, headers={"content-type": "text/html"})

    output = await _crawl_with(handler, monkeypatch)
    assert all("/asset.gif" not in r.url for r in output.results)
    assert all(f.url != "https://example.com/asset.gif" for f in output.failures)


@pytest.mark.asyncio
async def test_oversized_body_is_reported(monkeypatch):
    monkeypatch.setattr(get_settings(), "CRAWL_MAX_BODY_BYTES", 64)

    def handler(path):
        if path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="x" * 5000)

    output = await _crawl_with(handler, monkeypatch)
    assert output.results == []
    assert any(f.detail and "size" in f.detail for f in output.failures)