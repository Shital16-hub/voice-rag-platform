from fastapi import FastAPI
from app.api import auth
from app.core.logger import get_logger

logger = get_logger(__name__)

# create the FastAPI app
app = FastAPI(
    title="Voice RAG Platform",
    description="Multi-tenant Voice RAG Platform",
    version="0.1.0"
)

# register our routers
app.include_router(auth.router)


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    logger.info("Health check called")
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")