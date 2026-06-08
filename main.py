from fastapi import FastAPI
from app.api.routes import audit
from app.logger import get_logger
from app.config import get_settings

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title="AEO Audit Tool",
    description="Audit websites for AI Retrieval readiness",
    version="0.1.0"
)

app.include_router(
    audit.router,
    prefix="/api/v1",
    tags=["audit"]
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV }