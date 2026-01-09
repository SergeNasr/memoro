"""Tests for Firebase Auth service module."""

import sys
import urllib.parse
from unittest.mock import Mock, patch

import pytest

# Mock firebase_admin before importing the service module (since PR 1 dependencies may not be installed)
mock_firebase_admin = Mock()
mock_firebase_admin.auth = Mock()
mock_firebase_admin.credentials = Mock()
mock_firebase_admin.initialize_app = Mock()

with patch.dict(sys.modules, {"firebase_admin": mock_firebase_admin}):
    from backend.app.services.firebase_auth import get_google_sign_in_url, verify_firebase_token


class TestGetGoogleSignInUrl:
    """Tests for get_google_sign_in_url function."""

    def test_get_google_sign_in_url_success(self):
        """Test successful Google Sign-In URL generation."""
        callback_url = "https://example.com/auth/callback"
        client_id = "test-client-id.apps.googleusercontent.com"

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_client_id = client_id

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

    def test_get_google_sign_in_url_missing_client_id(self):
        """Test that missing client ID raises ValueError."""
        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            # Simulate missing attribute by using getattr that returns None
            type(mock_settings).firebase_web_client_id = property(lambda self: None)

            with pytest.raises(ValueError, match="firebase_web_client_id is required"):
                get_google_sign_in_url("https://example.com/callback")

    def test_get_google_sign_in_url_generates_unique_state(self):
        """Test that each call generates a unique state parameter."""
        callback_url = "https://example.com/auth/callback"
        client_id = "test-client-id.apps.googleusercontent.com"

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_client_id = client_id

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

    def test_verify_firebase_token_success(self):
        """Test successful token verification."""
        id_token = "test-id-token"
        user_id = "test-user-id"

        # Create a dict-like object that supports .get() method
        class MockToken(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_decoded_token = MockToken({"uid": user_id, "email": "test@example.com"})

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.return_value = mock_decoded_token

                result = verify_firebase_token(id_token)

                assert result == user_id
                mock_auth.verify_id_token.assert_called_once_with(id_token)

    def test_verify_firebase_token_no_uid(self):
        """Test that missing uid in token raises ValueError."""
        id_token = "test-id-token"
        
        # Create a dict-like object that supports .get() method
        class MockToken(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        mock_decoded_token = MockToken({"email": "test@example.com"})

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.return_value = mock_decoded_token

                with pytest.raises(ValueError, match="No uid in Firebase token claims"):
                    verify_firebase_token(id_token)

    def test_verify_firebase_token_invalid_token(self):
        """Test that invalid token raises exception."""
        id_token = "invalid-token"

        # Create a mock exception class
        class InvalidIdTokenError(Exception):
            pass

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.side_effect = InvalidIdTokenError("Invalid token")

                with pytest.raises(InvalidIdTokenError):
                    verify_firebase_token(id_token)

    def test_verify_firebase_token_expired_token(self):
        """Test that expired token raises exception."""
        id_token = "expired-token"

        # Create a mock exception class
        class ExpiredIdTokenError(Exception):
            pass

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.side_effect = ExpiredIdTokenError("Expired token")

                with pytest.raises(ExpiredIdTokenError):
                    verify_firebase_token(id_token)
