import asyncio
from collections import deque
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.logger import get_logger
from app.config import get_settings
from app.core.utils import normalize_url

settings = get_settings()
logger = get_logger(__name__) 

@dataclass
class CrawlResult:
    url: str
    html: str
    status_code: int
    
class Crawler:
    def __init__(self, seed_url: str, limit: int = None):
        self.seed_url = seed_url
        self.limit = limit if limit is not None else settings.CRAWL_LIMIT
        
        self.visited: set[str] = set()
        self.queue: deque[str] = deque()
        self.results: list[CrawlResult] = []
        
        self.domain = urlparse(seed_url).netloc
        
        self.robot_parser = RobotFileParser()
        
        self._semaphore = asyncio.Semaphore(3)
        
    async def _load_robots(self):
        try:
            url = f"https://{self.domain}/robots.txt"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=settings.CRAWL_TIMEOUT)
                
                robots_txt_lines = response.text.splitlines()
                
                self.robot_parser.parse(robots_txt_lines)
                
                logger.info(f"Loaded robots.txt from {url}")
        except Exception as e:
            logger.warning(f"Could not load robots.txt for {self.domain}:{e}. Proceeding without it.")
        
    def _is_allowed(self, url: str) -> bool:
        return self.robot_parser.can_fetch(settings.USER_AGENT, url)
    
    async def _fetch(self, url: str) -> CrawlResult | None:
        try:
            headers = {
                "User-Agent": settings.USER_AGENT,
                "Accept": "text/html"
            }
            
            async with self._semaphore:
                async with httpx.AsyncClient(
                    headers=headers, 
                    timeout=settings.CRAWL_TIMEOUT, 
                    follow_redirects=True,
                ) as client:
                
                    response = await client.get(url)
                    
                    html = response.text
                    status_code = response.status_code
                    
                    if status_code != 200:
                        return None
                    
                    logger.debug(f"Successfully fetched HTML Content from URL: {url} - Status Code: {status_code}")
                
                    return CrawlResult(url, html, status_code)
                
        except Exception as e:
            logger.error(f"Error fetching url: {url} and Exception {e}")
            return None
        
    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        
        tags = soup.find_all("a", href=True)
        
        links = []
        
        for tag in tags:
            link = normalize_url(tag["href"], base_url)
            
            if link is not None: 
                links.append(link)
                
        return links
            
    async def crawl(self) -> list[CrawlResult]:
        await self._load_robots()
        
        normalized_url = normalize_url(self.seed_url, "")
        
        if not normalized_url:
            return self.results
        
        self.queue.append(normalized_url)
        
        while self.queue and len(self.results) < self.limit:
            batch = []
            
            while self.queue and len(batch) < 3:
                url = self.queue.popleft()
                
                if not self._is_allowed(url):
                    continue
                
                if url not in self.visited:
                    self.visited.add(url)
                else:
                    continue
                
                batch.append(url)
                
            tasks = [self._fetch(url) for url in batch]
            
            results = await asyncio.gather(*tasks)
            
            results =  [result for result in results if result]
            
            for result in results:
                links = self._extract_links(result.html, result.url)
                
                filtered_links = []
                
                for link in links:
                    if not self._is_allowed(link):
                        continue
                
                    if link not in self.visited:
                        self.visited.add(link)
                    else:
                        continue
                
                    filtered_links.append(link)
                
                self.queue.extend(filtered_links)
                
            self.results.extend(results)
             
        logger.info(f"Crawl complete for {self.seed_url} -- {len(self.results)} pages fetched")
        
        return self.results