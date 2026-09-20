from fastapi import FastAPI
from app.api import auth_router, document_router
from app.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Voice RAG Platform",
    description="Multi-tenant Voice RAG Platform",
    version="0.1.0"
)

app.include_router(auth_router.router)
app.include_router(document_router.router)


@app.get("/health")
async def health_check():
    logger.info("Health check called")
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")