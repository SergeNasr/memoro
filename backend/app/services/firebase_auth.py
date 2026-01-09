"""Firebase Auth service for authentication operations."""

import secrets
import urllib.parse

import structlog
from firebase_admin import auth, credentials, initialize_app

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


def get_google_sign_in_url(callback_url: str) -> str:
    """
    Generate Google Sign-In OAuth URL using Firebase Auth REST API configuration.

    Args:
        callback_url: URL to redirect user after Google authentication

    Returns:
        Google OAuth authorization URL

    Raises:
        ValueError: If required config is missing
    """
    client_id = getattr(settings, "firebase_web_client_id", None)
    if not client_id:
        raise ValueError("firebase_web_client_id is required")

    # Generate a secure state parameter for CSRF protection
    state = secrets.token_urlsafe(32)

    # Google OAuth 2.0 authorization endpoint
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    # Required OAuth parameters
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    # Construct the full URL
    oauth_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.info("generated_google_sign_in_url", callback_url=callback_url, state=state)

    return oauth_url


def verify_firebase_token(id_token: str) -> str:
    """
    Verify Firebase ID token and extract user_id.

    Args:
        id_token: Firebase ID token

    Returns:
        Firebase user ID (uid)

    Raises:
        ValueError: If token is invalid or user_id cannot be extracted
        Exception: If Firebase Admin SDK verification fails
    """
    try:
        _get_firebase_app()
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token.get("uid")
        if not user_id:
            raise ValueError("No uid in Firebase token claims")
        logger.debug("firebase_token_verified", user_id=user_id)
        return user_id
    except Exception as e:
        logger.error("firebase_token_verification_failed", error=str(e))
        raise
