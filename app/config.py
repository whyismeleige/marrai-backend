from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CRAWL_LIMIT: int = 20
    CRAWL_TIMEOUT: int = 10
    USER_AGENT: str = "aeo-audit-bot/1.0"
    
    class Config:
        env_file: ".env"
        env_file_encoding: "utf-8"
        
@lru_cache
def get_settings() -> Settings:
    return Settings()
