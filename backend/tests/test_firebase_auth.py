"""Tests for Firebase Auth service module."""

import urllib.parse

import pytest

from backend.app.services.firebase_auth import get_google_sign_in_url, verify_firebase_token


class TestGetGoogleSignInUrl:
    """Tests for get_google_sign_in_url function."""

    def test_get_google_sign_in_url_success(self, mock_firebase_settings):
        """Test successful Google Sign-In URL generation."""
        callback_url = "https://example.com/auth/callback"
        client_id = "test-client-id.apps.googleusercontent.com"

        # Override the client_id for this test
        mock_firebase_settings.firebase_web_client_id = client_id

        url = get_google_sign_in_url(callback_url)

        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")

        # Parse URL to check parameters
        parsed = urllib.parse.urlparse(url)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        assert params["client_id"] == client_id
        assert params["redirect_uri"] == callback_url
        assert params["response_type"] == "code"
        assert params["scope"] == "openid email profile"
        assert "state" in params
        assert len(params["state"]) > 0
        assert params["access_type"] == "offline"
        assert params["prompt"] == "select_account"

    def test_get_google_sign_in_url_missing_client_id(self, mock_firebase_settings):
        """Test that missing client ID raises ValueError."""
        # Remove the firebase_web_client_id attribute
        if hasattr(mock_firebase_settings, "firebase_web_client_id"):
            delattr(mock_firebase_settings, "firebase_web_client_id")

        with pytest.raises(ValueError, match="firebase_web_client_id is required"):
            get_google_sign_in_url("https://example.com/callback")

    def test_get_google_sign_in_url_generates_unique_state(self, mock_firebase_settings):
        """Test that each call generates a unique state parameter."""
        callback_url = "https://example.com/auth/callback"
        client_id = "test-client-id.apps.googleusercontent.com"

        mock_firebase_settings.firebase_web_client_id = client_id

        url1 = get_google_sign_in_url(callback_url)
        url2 = get_google_sign_in_url(callback_url)

        # Extract state parameters from URLs
        params1 = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url1).query))
        params2 = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url2).query))

        # States should be different
        assert params1["state"] != params2["state"]
        # But both should be valid base64url strings
        assert len(params1["state"]) > 0
        assert len(params2["state"]) > 0


class TestVerifyFirebaseToken:
    """Tests for verify_firebase_token function."""

    def test_verify_firebase_token_success(self, mock_firebase_settings):
        """Test successful token verification."""
        from unittest.mock import patch

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
        from unittest.mock import patch

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
        from unittest.mock import patch

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
        from unittest.mock import patch

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
