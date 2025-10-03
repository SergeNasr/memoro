"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import HTTPError

from backend.app.config import settings
from backend.app.exceptions import (
    MemoroException,
    general_exception_handler,
    http_error_handler,
    memoro_exception_handler,
)
from backend.app.logger import setup_logging
from backend.app.routers import contacts, interactions

# Setup logging
setup_logging(log_level=settings.log_level, environment=settings.environment)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    from backend.app.db import close_pool, get_pool

    logger.info("starting_memoro", environment=settings.environment)

    # Initialize database pool
    await get_pool()

    yield

    # Close database pool
    await close_pool()
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

# Register exception handlers
app.add_exception_handler(MemoroException, memoro_exception_handler)
app.add_exception_handler(HTTPError, http_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers
app.include_router(interactions.router)
app.include_router(contacts.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.environment}
