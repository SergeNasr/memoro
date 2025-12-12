"""Authentication provider abstraction layer."""

from typing import Protocol

import structlog
from clerk_backend_api import Clerk
from clerk_backend_api.exceptions import ClerkAPIError
from clerk_backend_api.jwks_helpers import VerifyTokenOptions, verify_token

from backend.app.config import settings

logger = structlog.get_logger(__name__)


class AuthProviderError(Exception):
    """Base exception for auth provider errors."""

    pass


class AuthProvider(Protocol):
    """Protocol defining authentication provider interface."""

    def send_magic_link(self, email: str, callback_url: str) -> None:
        """Send magic link email to user."""
        ...

    def verify_token(self, token: str) -> dict:
        """Verify token and return user dict with 'id' field."""
        ...

    def get_user_from_token(self, token: str) -> dict | None:
        """Get user info from token, returns None if invalid."""
        ...

    def get_session_token(self, session_id: str) -> str:
        """Get session token from session ID."""
        ...


class ClerkAuthProvider:
    """Clerk implementation of AuthProvider."""

    def __init__(self, secret_key: str):
        """Initialize Clerk client with secret key."""
        self._client = Clerk(bearer_auth=secret_key)
        self._secret_key = secret_key

    def send_magic_link(self, email: str, callback_url: str) -> None:
        """Send magic link email via Clerk."""
        try:
            sign_in_data = {"identifier": email, "strategy": "email_link"}
            sign_in_attempt = self._client.sign_ins.create(sign_in_data)
            prepare_data = {"strategy": "email_link"}
            prepared = self._client.sign_ins.prepare_first_factor(
                sign_in_attempt["id"], prepare_data
            )
            attempt_data = {"strategy": "email_link", "redirect_url": callback_url}
            self._client.sign_ins.attempt_first_factor(sign_in_attempt["id"], attempt_data)
        except ClerkAPIError as e:
            logger.error("clerk_magic_link_failed", email=email, error=str(e))
            raise AuthProviderError(f"Failed to send magic link: {e}") from e

    def verify_token(self, token: str) -> dict:
        """Verify token and return user dict with 'id' field."""
        try:
            options = VerifyTokenOptions(secret_key=self._secret_key)
            payload = verify_token(token, options)
            user_id = payload.get("sub")
            if not user_id:
                raise AuthProviderError("Invalid token: no user ID in payload")
            return {"id": user_id}
        except Exception as e:
            logger.error("clerk_token_verification_failed", error=str(e))
            raise AuthProviderError(f"Token verification failed: {e}") from e

    def get_user_from_token(self, token: str) -> dict | None:
        """Get user info from token, returns None if invalid."""
        try:
            return self.verify_token(token)
        except AuthProviderError:
            return None

    def get_session_token(self, session_id: str) -> str:
        """Get session token from session ID."""
        try:
            session = self._client.sessions.get(session_id)
            if not session:
                raise AuthProviderError(f"Session not found: {session_id}")
            token_response = self._client.sessions.get_token(session_id, "session")
            return token_response
        except ClerkAPIError as e:
            logger.error("clerk_get_session_token_failed", session_id=session_id, error=str(e))
            raise AuthProviderError(f"Failed to get session token: {e}") from e


def get_auth_provider() -> AuthProvider:
    """Get the configured auth provider instance."""
    return ClerkAuthProvider(settings.clerk_secret_key)
