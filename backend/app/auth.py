from uuid import UUID

import structlog
from fastapi import HTTPException, Request
from supabase import AuthApiError, Client, create_client

from backend.app.config import settings

logger = structlog.get_logger(__name__)

# Cookie configuration
COOKIE_NAME = "supabase_access_token"


def get_supabase_client() -> Client:
    """Get the Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_secret_key)


async def get_current_user(request: Request) -> UUID:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_client()
    try:
        user = supabase.auth.get_user(jwt=token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Unauthorized")
    except AuthApiError as e:
        logger.error("token_validation_failed", error=e.message)
        raise HTTPException(status_code=401, detail="Unauthorized") from e

    return UUID(user.user.id)


async def get_authenticated_user(request: Request) -> UUID:
    """
    FastAPI dependency for API endpoints that require authentication.
    Returns user_id if authenticated, raises HTTPException(401) otherwise.
    """
    return await get_current_user(request)


class AuthenticationRedirect(HTTPException):
    """Custom exception for authentication redirects in UI endpoints."""

    def __init__(self, redirect_url: str = "/auth/login"):
        super().__init__(status_code=401, detail="Unauthorized")
        self.redirect_url = redirect_url


async def require_auth(request: Request) -> UUID:
    """
    FastAPI dependency for UI endpoints that require authentication.
    Returns user_id if authenticated, raises AuthenticationRedirect otherwise.
    """
    try:
        return await get_current_user(request)
    except HTTPException as e:
        # Raise custom exception that will be handled by exception handler
        raise AuthenticationRedirect("/auth/login") from e


async def get_optional_user(request: Request) -> UUID | None:
    """
    Safely check if user is authenticated without raising exceptions.
    Returns user_id if authenticated, None otherwise.
    Used for template context to conditionally show UI elements.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
