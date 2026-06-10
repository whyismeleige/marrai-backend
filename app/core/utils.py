from urllib.parse import urlparse, urljoin, urlunparse

def normalize_url(url: str, base_url: str) -> str | None:
    try:
        joined_url = urljoin(base_url, url)
        
        url_parsed = urlparse(joined_url)
        base_url_parsed = urlparse(base_url)
        
        if url_parsed.scheme not in ("http", "https"):
            return None
        
        if url_parsed.netloc != base_url_parsed.netloc:
            return None
        
        url_parsed = url_parsed._replace(fragment="", query="")
        
        unparsed_url = urlunparse(url_parsed)
        
        return unparsed_url.lower().rstrip("/")
    except Exception as e:
        return None
        
