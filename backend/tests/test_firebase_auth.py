"""Tests for Firebase Auth service."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.services.firebase_auth import (
    complete_email_link_signin,
    send_email_link,
    verify_firebase_token,
)


class TestFirebaseAuth:
    """Firebase auth service tests."""

    def test_send_email_link(self, mock_firebase_settings):
        """Send email link calls Firebase API."""
        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
            send_email_link("test@example.com", "https://example.com/callback")
            mock_post.assert_called_once()
            assert "identitytoolkit.googleapis.com" in mock_post.call_args[0][0]

    def test_send_email_link_error(self, mock_firebase_settings):
        """HTTP error raises ValueError."""
        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection error")
            with pytest.raises(ValueError, match="Failed to send email link"):
                send_email_link("test@example.com", "https://example.com/callback")

    def test_complete_signin(self, mock_firebase_settings):
        """Complete sign-in returns ID token."""
        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: {"idToken": "test-token", "localId": "user-123"}
            )
            result = complete_email_link_signin("test@example.com", "oob-code")
            assert result == "test-token"

    def test_verify_token(self, mock_firebase_auth):
        """Verify token returns user ID."""
        from backend.tests.conftest import TEST_USER_ID

        result = verify_firebase_token("test-token")
        assert result == TEST_USER_ID

    def test_verify_token_invalid(self, mock_firebase_auth):
        """Invalid token raises ValueError."""
        mock_firebase_auth.set_error(Exception("Invalid token"))
        with pytest.raises(ValueError, match="Firebase token verification failed"):
            verify_firebase_token("invalid-token")
