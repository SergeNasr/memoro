from uuid import UUID

import structlog
from fastapi import HTTPException, Request
from firebase_admin import App, auth, credentials, initialize_app
from supabase import AuthApiError, Client, create_client

from backend.app.config import settings

logger = structlog.get_logger(__name__)

# Cookie configuration
COOKIE_NAME = "supabase_access_token"

# Firebase Admin SDK initialization (lazy)
_firebase_app: App | None = None


def get_firebase_client() -> App:
    """Get the Firebase Admin SDK app instance."""
    global _firebase_app
    if _firebase_app is None:
        if not settings.firebase_service_account_path:
            raise ValueError("firebase_service_account_path is required for Firebase auth")
        cred = credentials.Certificate(settings.firebase_service_account_path)
        _firebase_app = initialize_app(credential=cred)
    return _firebase_app


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


async def get_current_user_firebase(request: Request) -> UUID:
    """Get current user from Firebase ID token (parallel to get_current_user)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        firebase_app = get_firebase_client()
        decoded_token = auth.verify_id_token(token, app=firebase_app)
        user_id = decoded_token.get("uid")
        if not user_id:
            logger.error("firebase_token_missing_uid")
            raise HTTPException(status_code=401, detail="Unauthorized")
        return UUID(user_id)
    except ValueError as e:
        logger.error("firebase_token_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Unauthorized") from e
    except Exception as e:
        logger.error("firebase_token_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Unauthorized") from e


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
