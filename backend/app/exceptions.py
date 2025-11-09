"""Custom exceptions and error handlers."""

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import HTTPError

logger = structlog.get_logger(__name__)


class MemoroException(Exception):
    """Base exception for Memoro application errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LLMServiceError(MemoroException):
    """LLM service errors (OpenRouter API failures)."""

    def __init__(self, message: str = "Failed to analyze interaction. Please try again."):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class DatabaseError(MemoroException):
    """Database operation errors."""

    def __init__(self, message: str = "Database operation failed. Please try again."):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def memoro_exception_handler(request: Request, exc: MemoroException) -> JSONResponse:
    """Handle custom Memoro exceptions."""
    logger.error(
        "memoro_exception",
        exception_type=type(exc).__name__,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "unexpected_exception",
        exception_type=type(exc).__name__,
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


async def http_error_handler(request: Request, exc: HTTPError) -> JSONResponse:
    """Handle HTTP errors from external services."""
    logger.error(
        "http_error",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "External service unavailable. Please try again."},
    )


async def authentication_redirect_handler(request: Request, exc) -> RedirectResponse:
    """Handle authentication redirects for UI endpoints."""
    from backend.app.auth import AuthenticationRedirect

    if isinstance(exc, AuthenticationRedirect):
        redirect_url = exc.redirect_url
    else:
        redirect_url = "/auth/login"

    # Check if this is an HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"

    response = RedirectResponse(url=redirect_url, status_code=302)

    if is_htmx:
        # HTMX will follow HX-Redirect header
        response.headers["HX-Redirect"] = redirect_url

    return response
