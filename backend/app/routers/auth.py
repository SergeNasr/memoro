import structlog
from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.app.auth import COOKIE_NAME, get_current_user, get_optional_user
from backend.app.config import settings
from backend.app.services.firebase_auth import (
    complete_email_link_signin,
    send_email_link,
    verify_firebase_token,
)

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
    """Show login form with email input."""
    user_id = await get_optional_user(request)
    return templates.TemplateResponse(
        request, "login.html", {"is_authenticated": user_id is not None}
    )


# Supabase login page (kept for rollback)
# @router.get("/login", response_class=HTMLResponse)
# async def login_page(request: Request):
#     """Show login form asking for email."""
#     user_id = await get_optional_user(request)
#     return templates.TemplateResponse(
#         request, "login.html", {"is_authenticated": user_id is not None}
#     )


@router.post("/login")
async def send_magic_link(request: Request, email: str = Form(...)):
    """Send magic link email via Firebase."""
    callback_url = str(request.url_for("callback"))

    try:
        send_email_link(email, callback_url)
        logger.info("magic_link_sent", email=email)
    except Exception as e:
        logger.error("magic_link_send_failed", email=email, error=str(e))
        return templates.TemplateResponse(
            request,
            "components/login_message.html",
            {"message": "Failed to send magic link. Please try again."},
        )

    return templates.TemplateResponse(
        request,
        "components/login_message.html",
        {"message": "Check your email for the magic link!"},
    )


@router.get("/callback", name="callback")
async def callback(
    request: Request,
    oob_code: str | None = Query(None, alias="oobCode"),
    mode: str | None = Query(None),
    email: str | None = Query(None),
    id_token: str | None = Query(None, alias="idToken"),
    error: str | None = Query(None),
):
    """Handle Firebase callback - email link sign-in."""
    # Log the full URL to see what Firebase sends
    logger.info(
        "callback_received",
        full_url=str(request.url),
        oob_code=oob_code,
        mode=mode,
        email=email,
        id_token=id_token,
        error=error,
        query_params=dict(request.query_params),
        fragment=request.url.fragment,
    )

    if error:
        logger.error("auth_error_received", error=error)
        return RedirectResponse(url="/auth/login?error=auth_error")

    # If Firebase already provided an ID token, use it directly
    if id_token:
        try:
            user_id = verify_firebase_token(id_token)
            logger.info("email_link_signin_success_with_token", user_id=str(user_id))
            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie(
                key=COOKIE_NAME,
                value=id_token,
                max_age=int(COOKIE_MAX_AGE),
                **get_cookie_kwargs(),
            )
            return response
        except Exception as e:
            logger.error("firebase_token_validation_failed", error=str(e))
            return RedirectResponse(url="/auth/login?error=invalid_token")

    # Handle email link sign-in
    # If we have oobCode and email, assume it's a sign-in (mode might not be passed)
    if oob_code and email:
        # Default mode to signIn if not provided
        if not mode:
            mode = "signIn"

        if mode == "signIn":
            try:
                id_token = complete_email_link_signin(email, oob_code)
                user_id = verify_firebase_token(id_token)
                logger.info("email_link_signin_success", email=email, user_id=str(user_id))
            except Exception as e:
                logger.error("email_link_signin_failed", email=email, error=str(e))
                return RedirectResponse(url="/auth/login?error=invalid_link")

            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie(
                key=COOKIE_NAME,
                value=id_token,
                max_age=int(COOKIE_MAX_AGE),
                **get_cookie_kwargs(),
            )
            return response

    # Log what we received for debugging
    if oob_code:
        logger.warning(
            "callback_has_oobcode_but_no_idtoken",
            oob_code=oob_code,
            email=email,
            mode=mode,
            url=str(request.url),
        )

    # No valid callback parameters - show template
    user_id = await get_optional_user(request)
    return templates.TemplateResponse(
        request, "auth_callback.html", {"is_authenticated": user_id is not None}
    )


# Supabase callback endpoint (kept for rollback)
# @router.get("/callback", name="callback")
# async def callback(
#     request: Request,
#     access_token: str | None = Query(None, alias="access_token"),
#     supabase: Client = Depends(get_supabase_client),
# ):
#     if not access_token:
#         user_id = await get_optional_user(request)
#         return templates.TemplateResponse(
#             request, "auth_callback.html", {"is_authenticated": user_id is not None}
#         )
#
#     try:
#         user_response = supabase.auth.get_user(jwt=access_token)
#         if not user_response or not user_response.user:
#             logger.warning("invalid_token_received")
#             return RedirectResponse(url="/auth/login?error=invalid_token")
#     except AuthApiError as e:
#         logger.error("token_validation_failed", error=e.message)
#         return RedirectResponse(url="/auth/login?error=invalid_token")
#
#     response = RedirectResponse(url="/", status_code=302)
#     response.set_cookie(
#         key=COOKIE_NAME,
#         value=access_token,
#         max_age=int(COOKIE_MAX_AGE),
#         **get_cookie_kwargs(),
#     )
#
#     return response


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
