from functools import lru_cache

from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings

# Schemes accepted from hosted PostgreSQL providers / local Docker.
_POSTGRES_SCHEMES = {
    "postgres",
    "postgresql",
    "postgresql+asyncpg",
    "postgresql+psycopg2",
}


def _rebuild_database_url(raw_url: str, driver: str) -> str:
    """Normalize any user-provided Postgres URL to a specific driver scheme."""
    if "://" not in raw_url:
        raise ValueError("DATABASE_URL must be a valid postgres URL")
    scheme, _, rest = raw_url.partition("://")
    if scheme not in _POSTGRES_SCHEMES:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")
    return f"{driver}://{rest}"


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    # Optional file sink. Empty means stdout/stderr only, which is what
    # container platforms expect.
    LOG_FILE: str = ""

    # Public origin of the Next.js frontend, used for CORS and report links.
    FRONTEND_URL: str = "http://localhost:3000"
    # Comma-separated extra CORS origins. Defaults to FRONTEND_URL only.
    CORS_ORIGINS: str = ""

    # Direct URL support for hosted Postgres (Render/Railway/Neon/etc).
    # When empty, the individual DB_* variables are used instead.
    DATABASE_URL: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "aeo_audit"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    CRAWL_LIMIT: int = Field(default=20, ge=1, le=100)
    CRAWL_TIMEOUT: int = Field(default=10, ge=1, le=120)
    CRAWL_CONNECT_TIMEOUT: float = Field(default=5.0, ge=0.5, le=60)
    CRAWL_TOTAL_TIMEOUT: float = Field(default=30.0, ge=1.0, le=300)
    CRAWL_MAX_REDIRECTS: int = Field(default=5, ge=0, le=10)
    CRAWL_MAX_BODY_BYTES: int = Field(default=2_000_000, ge=64_000, le=20_000_000)
    CRAWL_CONCURRENCY: int = Field(default=3, ge=1, le=10)
    USER_AGENT: str = "marrai-aeo-audit/1.0"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    WORKER_CONCURRENCY_LIMIT: int = Field(default=2, ge=1, le=16)
    TASK_TIME_LIMIT: int = Field(default=300, ge=30, le=3600)
    TASK_SOFT_TIME_LIMIT: int = Field(default=240, ge=30, le=3600)

    # Abuse protection for audit creation, keyed by client IP.
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=3600, ge=10, le=86_400)
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=5, ge=1, le=1000)

    # Optional completion email via Resend. Empty disables email entirely.
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""

    # Shared secret used by the Next.js proxy routes to authenticate requests
    # and to prove that the X-Client-IP header is trustworthy.
    API_PROXY_SHARED_SECRET: str = ""

    @property
    def async_database_url(self) -> str:
        raw = self.DATABASE_URL or _build_dsn_from_parts(self)
        return _rebuild_database_url(raw, "postgresql")

    @property
    def sync_database_url(self) -> str:
        raw = self.DATABASE_URL or _build_dsn_from_parts(self)
        return _rebuild_database_url(raw, "postgresql+psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [self.FRONTEND_URL.rstrip("/")]
        if self.CORS_ORIGINS:
            origins.extend(
                origin.strip().rstrip("/")
                for origin in self.CORS_ORIGINS.split(",")
                if origin.strip()
            )
        # De-duplicate while preserving order.
        return list(dict.fromkeys(origins))

    @property
    def email_enabled(self) -> bool:
        return bool(self.RESEND_API_KEY and self.RESEND_FROM_EMAIL)

    @model_validator(mode="after")
    def _validate_production_config(self) -> "Settings":
        # Fail fast in production instead of running with dangerous defaults.
        if self.APP_ENV != "production":
            return self

        problems: list[str] = []
        if not self.DATABASE_URL and not self.DB_PASSWORD:
            problems.append("DATABASE_URL (or DB_PASSWORD) must be set")
        if not self.API_PROXY_SHARED_SECRET:
            problems.append("API_PROXY_SHARED_SECRET must be set")
        if not self.FRONTEND_URL or "localhost" in self.FRONTEND_URL:
            problems.append("FRONTEND_URL must be set to the public frontend origin")
        if self.CRAWL_LIMIT > 100:
            problems.append("CRAWL_LIMIT must be 100 or less")

        if problems:
            raise ValueError(
                "Invalid production configuration: " + "; ".join(problems)
            )
        return self


def _build_dsn_from_parts(settings: Settings) -> str:
    password = settings.DB_PASSWORD
    auth = f"{settings.DB_USER}:{password}@" if password else f"{settings.DB_USER}@"
    return (
        f"postgresql://{auth}{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
