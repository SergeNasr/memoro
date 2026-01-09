"""Tests for Firebase Auth service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, Response
from firebase_admin import exceptions

from backend.app.services.firebase_auth import (
    exchange_oob_code_for_token,
    send_magic_link,
    verify_firebase_token,
)


class TestSendMagicLink:
    """Tests for send_magic_link function."""

    @pytest.mark.asyncio
    async def test_send_magic_link_success(self):
        """Test successful magic link sending."""
        email = "test@example.com"
        callback_url = "https://example.com/callback"

        mock_response = Response(200, json={"email": email})
        mock_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                await send_magic_link(email, callback_url)

                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert "sendOobCode" in call_args[0][0]
                assert call_args[1]["json"]["requestType"] == "EMAIL_SIGNIN"
                assert call_args[1]["json"]["email"] == email
                assert call_args[1]["json"]["continueUrl"] == callback_url

    @pytest.mark.asyncio
    async def test_send_magic_link_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = None

            with pytest.raises(ValueError, match="firebase_web_api_key is required"):
                await send_magic_link("test@example.com", "https://example.com/callback")

    @pytest.mark.asyncio
    async def test_send_magic_link_api_error(self):
        """Test that API errors are raised."""
        email = "test@example.com"
        callback_url = "https://example.com/callback"

        mock_response = Response(400, json={"error": {"message": "Invalid email"}})
        mock_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                with pytest.raises(HTTPStatusError):
                    await send_magic_link(email, callback_url)


class TestExchangeOobCodeForToken:
    """Tests for exchange_oob_code_for_token function."""

    @pytest.mark.asyncio
    async def test_exchange_oob_code_for_token_success_with_email(self):
        """Test successful token exchange with email provided."""
        oob_code = "test-oob-code"
        email = "test@example.com"
        id_token = "test-id-token"

        mock_response = Response(200, json={"idToken": id_token, "email": email})
        mock_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                result = await exchange_oob_code_for_token(oob_code, email)

                assert result == id_token
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert "signInWithEmailLink" in call_args[0][0]
                assert call_args[1]["json"]["email"] == email
                assert call_args[1]["json"]["oobCode"] == oob_code

    @pytest.mark.asyncio
    async def test_exchange_oob_code_for_token_success_without_email(self):
        """Test successful token exchange without email (extracted from oobCode)."""
        oob_code = "test-oob-code"
        email = "test@example.com"
        id_token = "test-id-token"

        # Mock response for email extraction
        mock_email_response = Response(200, json={"email": email})
        mock_email_response.request = MagicMock()

        # Mock response for token exchange
        mock_token_response = Response(200, json={"idToken": id_token, "email": email})
        mock_token_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                # First call for email extraction, second for token exchange
                mock_client.post.side_effect = [mock_email_response, mock_token_response]
                mock_client_class.return_value = mock_client

                result = await exchange_oob_code_for_token(oob_code)

                assert result == id_token
                assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_exchange_oob_code_for_token_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = None

            with pytest.raises(ValueError, match="firebase_web_api_key is required"):
                await exchange_oob_code_for_token("test-oob-code")

    @pytest.mark.asyncio
    async def test_exchange_oob_code_for_token_no_id_token_in_response(self):
        """Test that missing idToken in response raises ValueError."""
        oob_code = "test-oob-code"
        email = "test@example.com"

        mock_response = Response(200, json={"email": email})
        mock_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="No idToken in Firebase response"):
                    await exchange_oob_code_for_token(oob_code, email)

    @pytest.mark.asyncio
    async def test_exchange_oob_code_for_token_api_error(self):
        """Test that API errors are raised."""
        oob_code = "test-oob-code"
        email = "test@example.com"

        mock_response = Response(400, json={"error": {"message": "Invalid oobCode"}})
        mock_response.request = MagicMock()

        with patch("backend.app.services.firebase_auth.settings") as mock_settings:
            mock_settings.firebase_web_api_key = "test-api-key"

            with patch("backend.app.services.firebase_auth.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                with pytest.raises(HTTPStatusError):
                    await exchange_oob_code_for_token(oob_code, email)


class TestVerifyFirebaseToken:
    """Tests for verify_firebase_token function."""

    def test_verify_firebase_token_success(self):
        """Test successful token verification."""
        token = "test-token"
        user_id = "test-user-id"

        mock_decoded_token = {"uid": user_id, "email": "test@example.com"}

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.return_value = mock_decoded_token

                result = verify_firebase_token(token)

                assert result == user_id
                mock_auth.verify_id_token.assert_called_once_with(token)

    def test_verify_firebase_token_no_uid(self):
        """Test that missing uid in token raises ValueError."""
        token = "test-token"
        mock_decoded_token = {"email": "test@example.com"}

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.return_value = mock_decoded_token

                with pytest.raises(ValueError, match="No uid in Firebase token claims"):
                    verify_firebase_token(token)

    def test_verify_firebase_token_invalid_token(self):
        """Test that invalid token raises exception."""
        token = "invalid-token"

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.side_effect = exceptions.InvalidIdTokenError(
                    "Invalid token"
                )

                with pytest.raises(exceptions.InvalidIdTokenError):
                    verify_firebase_token(token)

    def test_verify_firebase_token_expired_token(self):
        """Test that expired token raises exception."""
        token = "expired-token"

        with patch("backend.app.services.firebase_auth._get_firebase_app"):
            with patch("backend.app.services.firebase_auth.auth") as mock_auth:
                mock_auth.verify_id_token.side_effect = exceptions.ExpiredIdTokenError(
                    "Expired token"
                )

                with pytest.raises(exceptions.ExpiredIdTokenError):
                    verify_firebase_token(token)
