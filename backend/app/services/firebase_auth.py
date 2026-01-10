"""Firebase Auth service for authentication operations."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
import structlog
from firebase_admin import auth

from backend.app.auth import get_firebase_client
from backend.app.config import settings

logger = structlog.get_logger(__name__)


def send_email_link(email: str, callback_url: str) -> None:
    """
    Send email sign-in link using Firebase Auth REST API.

    Args:
        email: User's email address
        callback_url: URL to redirect user after clicking the link

    Raises:
        ValueError: If required config is missing or sending fails
        Exception: If Firebase REST API call fails
    """
    if not settings.firebase_web_api_key:
        raise ValueError("firebase_web_api_key is required")

    # Include email in callback URL so it's preserved through Firebase's redirect
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    query_params["email"] = [email]  # Add email to query params
    new_query = urlencode(query_params, doseq=True)
    callback_url_with_email = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )

    api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={settings.firebase_web_api_key}"

    payload = {
        "requestType": "EMAIL_SIGNIN",
        "email": email,
        "continueUrl": callback_url_with_email,
    }

    try:
        response = httpx.post(api_url, json=payload, timeout=10.0)
        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            error_message = error_data.get("error", {}).get(
                "message", f"HTTP {response.status_code}"
            )
            raise httpx.HTTPStatusError(error_message, request=response.request, response=response)

        logger.info("email_link_sent", email=email, callback_url=callback_url_with_email)
    except httpx.HTTPError as e:
        logger.error("firebase_email_link_send_failed", email=email, error=str(e))
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", str(e))
                raise ValueError(f"Failed to send email link: {error_message}") from e
            except Exception:
                pass
        raise ValueError(f"Failed to send email link: {e}") from e
    except ValueError:
        raise
    except Exception as e:
        logger.error("firebase_email_link_send_error", email=email, error=str(e))
        raise


def complete_email_link_signin(email: str, oob_code: str) -> str:
    """
    Complete email link sign-in using Firebase Auth REST API.

    Args:
        email: User's email address
        oob_code: OOB code from the email link

    Returns:
        Firebase ID token

    Raises:
        ValueError: If required config is missing or sign-in fails
        Exception: If Firebase REST API call fails
    """
    if not settings.firebase_web_api_key:
        raise ValueError("firebase_web_api_key is required")

    api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={settings.firebase_web_api_key}"

    payload = {
        "email": email,
        "oobCode": oob_code,
    }

    try:
        response = httpx.post(api_url, json=payload, timeout=10.0)
        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            error_message = error_data.get("error", {}).get(
                "message", f"HTTP {response.status_code}"
            )
            raise httpx.HTTPStatusError(error_message, request=response.request, response=response)

        data = response.json()
        id_token = data.get("idToken")
        if not id_token:
            error_message = data.get("error", {}).get("message", "Unknown error")
            logger.error("firebase_no_id_token_email_link", response_data=data, error=error_message)
            raise ValueError(f"Firebase did not return idToken: {error_message}")

        logger.info("email_link_signin_completed", email=email, user_id=data.get("localId"))
        return id_token
    except httpx.HTTPError as e:
        logger.error("firebase_email_link_signin_failed", email=email, error=str(e))
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", str(e))
                raise ValueError(f"Failed to complete email link sign-in: {error_message}") from e
            except Exception:
                pass
        raise ValueError(f"Failed to complete email link sign-in: {e}") from e
    except ValueError:
        raise
    except Exception as e:
        logger.error("firebase_email_link_signin_error", email=email, error=str(e))
        raise


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
        firebase_app = get_firebase_client()
        decoded_token = auth.verify_id_token(id_token, app=firebase_app)
        user_id = decoded_token.get("uid")
        if not user_id:
            raise ValueError("No uid in Firebase token claims")
        logger.debug("firebase_token_verified", user_id=user_id)
        return user_id
    except ValueError:
        raise
    except Exception as e:
        logger.error("firebase_token_verification_failed", error=str(e))
        raise ValueError("Firebase token verification failed") from e
