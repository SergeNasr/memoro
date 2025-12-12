"""Tests for authentication module."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException, Request

from backend.app.auth import get_current_user
from backend.app.auth_provider import AuthProviderError
from backend.tests.conftest import make_mock_user_response

TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_uuid(self, mock_auth_provider):
        """Test that valid token returns correct UUID."""
        mock_auth_provider.verify_token.return_value = make_mock_user_response(TEST_USER_ID)

        # Mock request with cookie
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"clerk_session_token": "valid_token_here"}

        user_id = await get_current_user(mock_request)

        assert user_id == UUID(TEST_USER_ID)
        mock_auth_provider.verify_token.assert_called_once_with("valid_token_here")

    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        """Test that missing token raises HTTPException 401."""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_auth_provider):
        """Test that invalid token raises HTTPException 401."""
        mock_auth_provider.verify_token.return_value = {}

        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"clerk_session_token": "invalid_token"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_no_user_in_response_raises_401(self, mock_auth_provider):
        """Test that response without user ID raises HTTPException 401."""
        mock_auth_provider.verify_token.return_value = {}

        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"clerk_session_token": "token"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_provider_error_raises_401(self, mock_auth_provider):
        """Test that AuthProviderError raises HTTPException 401."""
        auth_error = AuthProviderError("Invalid token")
        mock_auth_provider.verify_token.side_effect = auth_error

        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"clerk_session_token": "expired_token"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"
