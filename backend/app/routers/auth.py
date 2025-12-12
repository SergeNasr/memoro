import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.app.auth import COOKIE_NAME, get_current_user, get_optional_user
from backend.app.auth_provider import AuthProvider, AuthProviderError, get_auth_provider
from backend.app.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


templates = Jinja2Templates(directory="backend/app/templates")

# Cookie configuration constants
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def get_cookie_kwargs() -> dict:
    """Get standard cookie kwargs for security settings."""
    return {
        "httponly": True,
        "secure": settings.environment != "development",
        "samesite": "lax",
        "path": "/",  # Explicitly set path for cookie operations
    }


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login form asking for email."""
    user_id = await get_optional_user(request)
    return templates.TemplateResponse(
        request, "login.html", {"is_authenticated": user_id is not None}
    )


@router.post("/login")
async def send_magic_link(
    request: Request,
    email: str = Form(...),
    auth_provider: AuthProvider = Depends(get_auth_provider),
):
    """Send magic link email via auth provider."""
    callback_url = str(request.url_for("callback"))

    auth_provider.send_magic_link(email, callback_url)

    return templates.TemplateResponse(
        request,
        "components/login_message.html",
        {"message": "Check your email for the magic link!"},
    )


@router.get("/callback", name="callback")
async def callback(
    request: Request,
    clerk_session: str | None = Query(None, alias="__clerk_created_session"),
    auth_provider: AuthProvider = Depends(get_auth_provider),
):
    if not clerk_session:
        user_id = await get_optional_user(request)
        return templates.TemplateResponse(
            request, "auth_callback.html", {"is_authenticated": user_id is not None}
        )

    try:
        token = auth_provider.get_session_token(clerk_session)
    except AuthProviderError as e:
        logger.error("session_token_fetch_failed", error=str(e))
        return RedirectResponse(url="/auth/login?error=invalid_token")

    try:
        user = auth_provider.get_user_from_token(token)
        if not user or not user.get("id"):
            logger.warning("invalid_token_received")
            return RedirectResponse(url="/auth/login?error=invalid_token")
    except AuthProviderError as e:
        logger.error("token_validation_failed", error=str(e))
        return RedirectResponse(url="/auth/login?error=invalid_token")

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=int(COOKIE_MAX_AGE),
        **get_cookie_kwargs(),
    )

    return response


@router.post("/logout")
async def logout(request: Request):
    """Clear session cookie and redirect to login."""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key=COOKIE_NAME, **get_cookie_kwargs())

    return response


@router.get("/session")
async def session(request: Request):
    try:
        user_id = await get_current_user(request)
        return {"authenticated": True, "user_id": str(user_id)}
    except HTTPException:
        return {"authenticated": False}
