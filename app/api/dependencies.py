import secrets

import redis.asyncio as redis
from fastapi import HTTPException, Request

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def resolve_client_ip(request: Request) -> str:
    """Return the trusted client IP for rate limiting.

    The browser only talks to the Next.js server routes, which forward the
    request with an X-Client-IP header. That header is only believed when the
    caller authenticates with API_PROXY_SHARED_SECRET, so unauthenticated
    clients cannot spoof their way past rate limits by sending fake headers.
    """
    if settings.API_PROXY_SHARED_SECRET:
        provided = request.headers.get("X-Proxy-Secret", "")
        if not provided or not secrets.compare_digest(
            provided, settings.API_PROXY_SHARED_SECRET
        ):
            raise HTTPException(
                status_code=403,
                detail="This endpoint must be accessed through the Marrai app.",
            )
        forwarded = request.headers.get("X-Client-IP", "").strip()
        if forwarded:
            return forwarded[:64]

    # No shared secret configured (local development), or no forwarded IP:
    # fall back to the direct network peer.
    return request.client.host if request.client else "unknown"


async def rate_limit_check(request: Request) -> str:
    """Allow a bounded number of audit creations per client IP per window."""
    client_ip = resolve_client_ip(request)

    try:
        client = await get_redis_client()
        key = f"rate-limit:audit:{client_ip}"
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)

        if count > settings.RATE_LIMIT_MAX_REQUESTS:
            ttl = await client.ttl(key)
            retry_after = max(ttl, 1)
            logger.warning(
                "Rate limit exceeded for client %s (window %ss)",
                client_ip,
                settings.RATE_LIMIT_WINDOW_SECONDS,
            )
            raise HTTPException(
                status_code=429,
                detail="You have reached the free audit limit for now. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Availability over precision: if Redis is briefly unavailable the
        # audit should still work rather than erroring out for every user.
        logger.error("Rate limiter unavailable, allowing request: %s", exc)

    return client_ip
