"""FastAPI application entry point."""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from httpx import HTTPError

from backend.app.config import settings
from backend.app.exceptions import (
    MemoroException,
    general_exception_handler,
    http_error_handler,
    memoro_exception_handler,
)
from backend.app.logger import setup_logging
from backend.app.routers import contacts, family_members, interactions, search, ui

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


# Request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request details with timing."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Skip logging for static assets
    if not request.url.path.startswith("/static"):
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=f"{duration_ms:.2f}",
        )

    return response


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

# Mount static files
app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")

# Register routers
app.include_router(ui.router)  # UI routes (no prefix, serves HTML)
app.include_router(interactions.router)  # API routes
app.include_router(contacts.router)
app.include_router(family_members.router)
app.include_router(search.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.environment}
