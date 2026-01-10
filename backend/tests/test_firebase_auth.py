"""Tests for Firebase Auth service module."""

from unittest.mock import patch

import httpx
import pytest

from backend.app.services.firebase_auth import (
    complete_email_link_signin,
    send_email_link,
    verify_firebase_token,
)


class TestSendEmailLink:
    """Tests for send_email_link function."""

    def test_send_email_link_success(self, mock_firebase_settings):
        """Test successful email link sending."""
        from unittest.mock import MagicMock

        email = "test@example.com"
        callback_url = "https://example.com/auth/callback"

        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"email": email}
            mock_post.return_value = mock_response

            send_email_link(email, callback_url)

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "identitytoolkit.googleapis.com" in call_args[0][0]
            assert call_args[1]["json"]["requestType"] == "EMAIL_SIGNIN"
            assert call_args[1]["json"]["email"] == email
            # Email is now included in the continueUrl to preserve it through Firebase redirect
            continue_url = call_args[1]["json"]["continueUrl"]
            assert callback_url in continue_url
            assert (
                f"email={email.replace('@', '%40')}" in continue_url
                or f"email={email}" in continue_url
            )

    def test_send_email_link_missing_api_key(self, mock_firebase_settings):
        """Test that missing API key raises ValueError."""
        mock_firebase_settings.firebase_web_api_key = None

        with pytest.raises(ValueError, match="firebase_web_api_key is required"):
            send_email_link("test@example.com", "https://example.com/callback")

    def test_send_email_link_http_error(self, mock_firebase_settings):
        """Test that HTTP error raises ValueError."""

        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection error")

            with pytest.raises(ValueError, match="Failed to send email link"):
                send_email_link("test@example.com", "https://example.com/callback")


class TestCompleteEmailLinkSignin:
    """Tests for complete_email_link_signin function."""

    def test_complete_email_link_signin_success(self, mock_firebase_settings):
        """Test successful email link sign-in."""
        from unittest.mock import MagicMock

        email = "test@example.com"
        oob_code = "test-oob-code"
        id_token = "test-id-token"

        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"idToken": id_token, "localId": "test-user-id"}
            mock_post.return_value = mock_response

            result = complete_email_link_signin(email, oob_code)

            assert result == id_token
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "identitytoolkit.googleapis.com" in call_args[0][0]
            assert call_args[1]["json"]["email"] == email
            assert call_args[1]["json"]["oobCode"] == oob_code

    def test_complete_email_link_signin_missing_api_key(self, mock_firebase_settings):
        """Test that missing API key raises ValueError."""
        mock_firebase_settings.firebase_web_api_key = None

        with pytest.raises(ValueError, match="firebase_web_api_key is required"):
            complete_email_link_signin("test@example.com", "oob-code")

    def test_complete_email_link_signin_no_id_token(self, mock_firebase_settings):
        """Test that missing idToken in response raises ValueError."""
        from unittest.mock import MagicMock

        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            with pytest.raises(ValueError, match="Firebase did not return idToken"):
                complete_email_link_signin("test@example.com", "oob-code")

    def test_complete_email_link_signin_http_error(self, mock_firebase_settings):
        """Test that HTTP error raises ValueError."""

        with patch("backend.app.services.firebase_auth.httpx.post") as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection error")

            with pytest.raises(ValueError, match="Failed to complete email link sign-in"):
                complete_email_link_signin("test@example.com", "oob-code")


class TestVerifyFirebaseToken:
    """Tests for verify_firebase_token function."""

    def test_verify_firebase_token_success(self, mock_firebase_settings):
        """Test successful token verification."""

        id_token = "test-id-token"
        user_id = "test-user-id"

        # Setup mock to return decoded token with uid
        mock_decoded_token = {"uid": user_id, "email": "test@example.com"}

        # Patch both _get_firebase_app and the imported auth module
        with (
            patch("backend.app.services.firebase_auth._get_firebase_app"),
            patch("backend.app.services.firebase_auth.auth") as mock_auth,
        ):
            mock_auth.verify_id_token.return_value = mock_decoded_token
            result = verify_firebase_token(id_token)

            assert result == user_id
            mock_auth.verify_id_token.assert_called_once_with(id_token)

    def test_verify_firebase_token_no_uid(self, mock_firebase_settings):
        """Test that missing uid in token raises ValueError."""

        id_token = "test-id-token"

        # Setup mock to return decoded token without uid
        mock_decoded_token = {"email": "test@example.com"}

        # Patch both _get_firebase_app and the imported auth module
        with (
            patch("backend.app.services.firebase_auth._get_firebase_app"),
            patch("backend.app.services.firebase_auth.auth") as mock_auth,
        ):
            mock_auth.verify_id_token.return_value = mock_decoded_token
            with pytest.raises(ValueError, match="No uid in Firebase token claims"):
                verify_firebase_token(id_token)

    def test_verify_firebase_token_invalid_token(self, mock_firebase_settings):
        """Test that invalid token raises exception."""

        id_token = "invalid-token"

        # Create a mock exception class
        class InvalidIdTokenError(Exception):
            pass

        # Patch both _get_firebase_app and the imported auth module
        with (
            patch("backend.app.services.firebase_auth._get_firebase_app"),
            patch("backend.app.services.firebase_auth.auth") as mock_auth,
        ):
            mock_auth.verify_id_token.side_effect = InvalidIdTokenError("Invalid token")
            with pytest.raises(InvalidIdTokenError):
                verify_firebase_token(id_token)

    def test_verify_firebase_token_expired_token(self, mock_firebase_settings):
        """Test that expired token raises exception."""

        id_token = "expired-token"

        # Create a mock exception class
        class ExpiredIdTokenError(Exception):
            pass

        # Patch both _get_firebase_app and the imported auth module
        with (
            patch("backend.app.services.firebase_auth._get_firebase_app"),
            patch("backend.app.services.firebase_auth.auth") as mock_auth,
        ):
            mock_auth.verify_id_token.side_effect = ExpiredIdTokenError("Expired token")
            with pytest.raises(ExpiredIdTokenError):
                verify_firebase_token(id_token)
