import redis.asyncio as redis
from fastapi import HTTPException, Request

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

TTL_SECONDS = 300

_redis_client = None

async def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client

async def rate_limit_check(request: Request):
    redis_client = await get_redis_client()

    ip = (
        request.headers.get("X-Forwarded-For", request.client.host)
        .split(",")[0]
        .strip()
    )

    ip_set = await redis_client.set(
        name=f"rate-limit:{ip}", value="1", nx=True, ex=TTL_SECONDS
    )

    if not ip_set:
        logger.warning(f"IP Address is rate limited: {ip}")
        raise HTTPException(
            status_code=429,
            detail="You are currently rate limited, Try Again Later.",
            headers={"Retry-After": "300"},
        )
