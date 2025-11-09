import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from supabase import AuthApiError, Client

from backend.app.auth import COOKIE_NAME, get_current_user, get_optional_user, get_supabase_client
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
    supabase: Client = Depends(get_supabase_client),
):
    """Send magic link email via Supabase."""
    callback_url = str(request.url_for("callback"))

    supabase.auth.sign_in_with_otp(
        {
            "email": email,
            "options": {"should_create_user": False, "email_redirect_to": callback_url},
        }
    )

    return templates.TemplateResponse(
        request,
        "components/login_message.html",
        {"message": "Check your email for the magic link!"},
    )


@router.get("/callback", name="callback")
async def callback(
    request: Request,
    access_token: str | None = Query(None, alias="access_token"),
    supabase: Client = Depends(get_supabase_client),
):
    if not access_token:
        user_id = await get_optional_user(request)
        return templates.TemplateResponse(
            request, "auth_callback.html", {"is_authenticated": user_id is not None}
        )

    try:
        user_response = supabase.auth.get_user(jwt=access_token)
        if not user_response or not user_response.user:
            logger.warning("invalid_token_received")
            return RedirectResponse(url="/auth/login?error=invalid_token")
    except AuthApiError as e:
        logger.error("token_validation_failed", error=e.message)
        return RedirectResponse(url="/auth/login?error=invalid_token")

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
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
