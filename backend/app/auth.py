from uuid import UUID

import structlog
from fastapi import HTTPException, Request

from backend.app.auth_provider import AuthProviderError, get_auth_provider

logger = structlog.get_logger(__name__)

# Cookie configuration
COOKIE_NAME = "clerk_session_token"


async def get_current_user(request: Request) -> UUID:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_provider = get_auth_provider()
    try:
        user = auth_provider.verify_token(token)
        if not user or not user.get("id"):
            raise HTTPException(status_code=401, detail="Unauthorized")
    except AuthProviderError as e:
        logger.error("token_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Unauthorized") from e

    return UUID(user["id"])


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
