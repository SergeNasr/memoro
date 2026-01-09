"""Firebase Auth service for authentication operations."""

import structlog
from firebase_admin import auth, credentials, initialize_app
from httpx import AsyncClient, HTTPStatusError

from backend.app.config import settings

logger = structlog.get_logger(__name__)

# Firebase Admin SDK initialization (lazy)
_firebase_app = None


def _get_firebase_app():
    """Initialize and return Firebase Admin SDK app instance."""
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate(settings.firebase_service_account_path)
        _firebase_app = initialize_app(credential=cred)
    return _firebase_app


async def send_magic_link(email: str, callback_url: str) -> None:
    """
    Send magic link email via Firebase Auth REST API.

    Args:
        email: User email address
        callback_url: URL to redirect user after clicking magic link

    Raises:
        HTTPStatusError: If Firebase API request fails
        ValueError: If required config is missing
    """
    if not settings.firebase_web_api_key:
        raise ValueError("firebase_web_api_key is required")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={settings.firebase_web_api_key}"

    payload = {
        "requestType": "EMAIL_SIGNIN",
        "email": email,
        "continueUrl": callback_url,
        "canHandleCodeInApp": True,
    }

    logger.info("sending_firebase_magic_link", email=email, callback_url=callback_url)

    async with AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("firebase_magic_link_sent", email=email)
        except HTTPStatusError as e:
            logger.error(
                "firebase_magic_link_failed",
                email=email,
                status_code=e.response.status_code,
                error=e.response.text,
            )
            raise


async def exchange_oob_code_for_token(oob_code: str, email: str | None = None) -> str:
    """
    Exchange OOB code for Firebase ID token.

    Args:
        oob_code: Out-of-band code from magic link
        email: User email (optional, will be extracted from oobCode if not provided)

    Returns:
        Firebase ID token

    Raises:
        HTTPStatusError: If Firebase API request fails
        ValueError: If required config is missing or email cannot be determined
    """
    if not settings.firebase_web_api_key:
        raise ValueError("firebase_web_api_key is required")

    # If email not provided, try to get it from oobCode verification
    if not email:
        email = await _get_email_from_oob_code(oob_code)

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={settings.firebase_web_api_key}"

    payload = {
        "email": email,
        "oobCode": oob_code,
    }

    logger.info("exchanging_oob_code_for_token", email=email)

    async with AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            id_token = data.get("idToken")
            if not id_token:
                raise ValueError("No idToken in Firebase response")
            logger.info("oob_code_exchanged_for_token", email=email)
            return id_token
        except HTTPStatusError as e:
            logger.error(
                "firebase_token_exchange_failed",
                email=email,
                status_code=e.response.status_code,
                error=e.response.text,
            )
            raise


async def _get_email_from_oob_code(oob_code: str) -> str:
    """
    Extract email from OOB code by verifying it.

    Args:
        oob_code: Out-of-band code

    Returns:
        Email address associated with the OOB code

    Raises:
        HTTPStatusError: If Firebase API request fails
        ValueError: If email cannot be extracted
    """
    if not settings.firebase_web_api_key:
        raise ValueError("firebase_web_api_key is required")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:resetPassword?key={settings.firebase_web_api_key}"

    payload = {"oobCode": oob_code}

    async with AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            email = data.get("email")
            if not email:
                raise ValueError("No email in Firebase oobCode verification response")
            return email
        except HTTPStatusError as e:
            logger.error(
                "firebase_oob_code_verification_failed",
                status_code=e.response.status_code,
                error=e.response.text,
            )
            raise


def verify_firebase_token(token: str) -> str:
    """
    Verify Firebase ID token and extract user_id.

    Args:
        token: Firebase ID token

    Returns:
        Firebase user ID (uid)

    Raises:
        ValueError: If token is invalid or user_id cannot be extracted
        Exception: If Firebase Admin SDK verification fails
    """
    try:
        _get_firebase_app()
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        if not user_id:
            raise ValueError("No uid in Firebase token claims")
        logger.debug("firebase_token_verified", user_id=user_id)
        return user_id
    except Exception as e:
        logger.error("firebase_token_verification_failed", error=str(e))
        raise
