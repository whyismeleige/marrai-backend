import json
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app.logger import get_logger
from app.config import get_settings
from app.core.crawler import CrawlResult
from app.core.utils import normalize_url

settings = get_settings()
logger = get_logger(__name__)

EXCLUDE_TAGS = ["script", "style", "nav", "footer", "header", "link", "noscript", "g", "menu", "button", "svg", "canvas"]
EXCLUDE_CLASSES = ["ad", "ads", "advertisements", "banner", "promo", "sponsored"]

@dataclass
class FAQItem:
    question: str
    answer: str


@dataclass
class ParsedPage:
    url: str
    status_code: int
    word_count: int = 0
    has_schema: bool = False
    images_without_alt: int = 0
    title: str | None = None
    meta_description: str | None = None
    meta_robots: str | None = None
    canonical_url: str | None = None
    body_text_content: str | None = None
    headings: list[dict[str, str]] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    json_ld_schema: list[str] = field(default_factory=list)
    schema_types: list[str] = field(default_factory=list)
    faq_items: list[FAQItem] = field(default_factory=list)

def _extract_title(soup: BeautifulSoup) -> str | None:
    return soup.title.string if soup.title else None

def _extract_meta_description(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": "description"})
    return meta.get("content") if meta else None

def _extract_meta_robots(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": "robots"})
    return meta.get("content") if meta else None

def _extract_canonical_url(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", attrs={"rel": "canonical"})
    return link.get("href") if link else None

def _extract_headers(soup: BeautifulSoup) -> list[dict[str, str]]:
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    
    return [{heading.name: heading.text.strip()} for heading in headings] 

def _extract_body_text(soup: BeautifulSoup) -> str | None: 
    container = soup.find("main") or soup.find("body")
    
    if not container:
        return None
    
    for tag in container.find_all(EXCLUDE_TAGS):
        tag.decompose()
        
    for tag in container.find_all(class_=EXCLUDE_CLASSES):
        tag.decompose()
        
    return container.get_text(separator=" ", strip=True)
   
def _extract_word_count(body_text: str | None) -> int:
    return len(body_text.split()) if body_text else 0


def _extract_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    tags = soup.find_all("a", href=True)
    
    links = []
    
    for tag in tags:
        link =  normalize_url(tag["href"], base_url)
        
        if link is not None:
            links.append(link)
            
    return links

def _extract_schema_types(node: Any) -> list[str]:
    types = []
    
    if isinstance(node, list):
        for item in node: 
            types.extend(_extract_schema_types(item))
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "@type":
                if isinstance(value, str):
                    types.append(value)
                elif isinstance(value, list):
                    for type_str in value:
                        if isinstance(type_str, str):
                            types.append(type_str)
            elif isinstance(value, (dict, list)):
                types.extend(_extract_schema_types(value))
    
    return types
                        

def _extract_schema(soup: BeautifulSoup) -> tuple[list[str], list[str], list[Any]]:
    tags = soup.find_all("script", {"type": "application/ld+json"})
    
    schema_data = []
    
    schema_types = []
    
    json_data = []
    
    for tag in tags:
        try:
            text = tag.get_text()
            data = json.loads(text) 

            schema_types.extend(_extract_schema_types(data))    
            schema_data.append(text)
            json_data.append(data)
        except Exception as e:
            continue    
        
    return (schema_data, list(set(schema_types)), json_data)

def _extract_images_without_alt(soup: BeautifulSoup) -> int:
    images_without_alt = [ 
        img for img in soup.find_all("img")
        if not img.has_attr("alt") or not img["alt"].strip()
    ]
    return len(images_without_alt)

def _build_faq_items(node: Any) -> list[FAQItem]:
    faq_items = []
    
    if isinstance(node, list):
        for item in node:
            faq_items.extend(_build_faq_items(item))
    elif isinstance(node, dict):
        if node.get("name") and (node.get("acceptedAnswer") or node.get("text")):
            question = node.get("name")
            answer_parts = []
            
            if node.get("acceptedAnswer"):
                accepted_answer = node.get("acceptedAnswer")
                
                if isinstance(accepted_answer, list):
                    for item in accepted_answer:
                        if item.get("text"):
                            answer_parts.append(item.get("text"))
                                
                elif isinstance(accepted_answer, dict):
                    if accepted_answer.get("text"):
                        answer_parts.append(accepted_answer.get("text"))
                    
                elif isinstance(accepted_answer, str):
                    answer_parts.append(accepted_answer)
            
            if node.get("text"):
                answer_parts.append(node.get("text"))
                
            answer = " ".join(answer_parts)
            
            faq_items.append(FAQItem(question, answer))
    
    return faq_items    

def _extract_faq_items(node: Any) -> list[FAQItem]:
    faq_items = []
    
    if isinstance(node, list):
        for item in node:
            faq_items.extend(_extract_faq_items(item))
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "@type" and (value == "FAQPage" or (isinstance(value, list) and "FAQPage" in value)):
                faq_items.extend(_build_faq_items(node.get("mainEntity")))
            elif isinstance(value, (dict, list)):
                faq_items.extend(_extract_faq_items(value))
    
    return faq_items


def parse(result: CrawlResult) -> ParsedPage:
    soup = BeautifulSoup(result.html, "lxml")
    
    body_text = _extract_body_text(soup)
    
    json_ld_schema, schema_types, json_data = _extract_schema(soup)
    
    return ParsedPage(
        url=result.url,
        status_code=result.status_code,
        has_schema= bool(json_ld_schema),
        images_without_alt= _extract_images_without_alt(soup),
        word_count=_extract_word_count(body_text),
        title= _extract_title(soup),
        meta_description= _extract_meta_description(soup),
        meta_robots= _extract_meta_robots(soup),
        canonical_url= _extract_canonical_url(soup),
        body_text_content= body_text,
        headings= _extract_headers(soup),
        internal_links= _extract_internal_links(soup, result.url),
        json_ld_schema= json_ld_schema,
        schema_types= schema_types,
        faq_items= _extract_faq_items(json_data) 
    )