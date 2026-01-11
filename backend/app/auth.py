from uuid import UUID

import structlog
from fastapi import HTTPException, Request
from firebase_admin import App, auth, credentials, initialize_app
from supabase import Client, create_client

from backend.app.config import settings
from backend.app.db import get_pool
from backend.app.services.users import get_or_create_user_by_firebase_uid

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
    """Get current user from Firebase ID token."""
    return await get_current_user_firebase(request)


async def get_current_user_firebase(request: Request) -> UUID:
    """
    Get current user from Firebase ID token.

    Verifies the Firebase token and resolves the Firebase UID to an internal UUID.
    Creates a new user if one doesn't exist for this Firebase UID.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Verify Firebase token
        firebase_app = get_firebase_client()
        decoded_token = auth.verify_id_token(token, app=firebase_app)
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email", "")

        if not firebase_uid:
            logger.error("firebase_token_missing_uid")
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Resolve Firebase UID to internal UUID
        pool = await get_pool()
        async with pool.acquire() as conn:
            user_id = await get_or_create_user_by_firebase_uid(conn, firebase_uid, email)

        return user_id
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
