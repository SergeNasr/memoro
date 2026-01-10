"""Tests for authentication module."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException, Request

from backend.app.auth import get_current_user, get_current_user_firebase

TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"
FIREBASE_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f5"  # Valid UUID format


class TestGetCurrentUserFirebase:
    """Tests for get_current_user_firebase dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_uuid(self, mock_firebase_settings):
        """Test that valid Firebase token returns correct UUID."""
        mock_decoded_token = {"uid": FIREBASE_USER_ID, "email": "test@example.com"}
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "valid_firebase_token"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.return_value = mock_decoded_token

            user_id = await get_current_user_firebase(mock_request)

            assert user_id == UUID(FIREBASE_USER_ID)
            mock_auth.verify_id_token.assert_called_once_with(
                "valid_firebase_token", app=mock_firebase_app
            )

    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        """Test that missing token raises HTTPException 401."""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_firebase(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_firebase_settings):
        """Test that invalid Firebase token raises HTTPException 401."""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "invalid_token"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.side_effect = ValueError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_firebase(mock_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_no_uid_in_token_raises_401(self, mock_firebase_settings):
        """Test that token without uid raises HTTPException 401."""
        mock_decoded_token = {"email": "test@example.com"}  # No uid
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "token_without_uid"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.return_value = mock_decoded_token

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_firebase(mock_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_exception_during_verification_raises_401(self, mock_firebase_settings):
        """Test that any exception during verification raises HTTPException 401."""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "token_that_raises_exception"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.side_effect = Exception("Firebase error")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_firebase(mock_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Unauthorized"


class TestGetCurrentUser:
    """Tests for get_current_user dependency (now uses Firebase)."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_uuid(self, mock_firebase_settings):
        """Test that valid Firebase token returns correct UUID via get_current_user."""
        mock_decoded_token = {"uid": FIREBASE_USER_ID, "email": "test@example.com"}
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "valid_firebase_token"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.return_value = mock_decoded_token

            user_id = await get_current_user(mock_request)

            assert user_id == UUID(FIREBASE_USER_ID)
            mock_auth.verify_id_token.assert_called_once_with(
                "valid_firebase_token", app=mock_firebase_app
            )

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
    async def test_invalid_token_raises_401(self, mock_firebase_settings):
        """Test that invalid Firebase token raises HTTPException 401."""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"supabase_access_token": "invalid_token"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.side_effect = ValueError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Unauthorized"
