"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.logger import setup_logging
from backend.app.routers import interactions

# Setup logging
setup_logging(log_level=settings.log_level, environment=settings.environment)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("starting_memoro", environment=settings.environment)
    yield
    logger.info("shutting_down_memoro")


# Create FastAPI application
app = FastAPI(
    title="Memoro API",
    description="Personal CRM for tracking daily interactions",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(interactions.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.environment}
