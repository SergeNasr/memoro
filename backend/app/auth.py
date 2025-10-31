from uuid import UUID

import structlog
from fastapi import HTTPException, Request
from supabase import AuthApiError, Client, create_client

from backend.app.config import settings

logger = structlog.get_logger(__name__)


def get_supabase_client() -> Client:
    """Get the Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_secret_key)


async def get_current_user(request: Request) -> UUID:
    token = request.cookies.get("supabase_access_token")
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
