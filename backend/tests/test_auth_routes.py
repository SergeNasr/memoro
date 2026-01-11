"""Tests for authentication routes."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from backend.tests.conftest import TEST_USER_ID


class TestLoginPage:
    """Tests for GET /auth/login."""

    @pytest.mark.asyncio
    async def test_login_page_returns_html(self, client: AsyncClient):
        """Login page returns HTML form."""
        response = await client.get("/auth/login")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestSendMagicLink:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_send_magic_link_success(self, client: AsyncClient, mock_firebase_settings):
        """Successful magic link sends confirmation."""
        with patch("backend.app.routers.auth.send_email_link"):
            response = await client.post("/auth/login", data={"email": "test@example.com"})

        assert response.status_code == 200
        assert b"Check your email" in response.content

    @pytest.mark.asyncio
    async def test_send_magic_link_failure(self, client: AsyncClient, mock_firebase_settings):
        """Failed magic link shows error."""
        with patch("backend.app.routers.auth.send_email_link", side_effect=ValueError("Failed")):
            response = await client.post("/auth/login", data={"email": "test@example.com"})

        assert response.status_code == 200
        assert b"Failed" in response.content or b"try again" in response.content.lower()


class TestCallback:
    """Tests for GET /auth/callback."""

    @pytest.mark.asyncio
    async def test_callback_email_link_success(self, client: AsyncClient, mock_firebase_auth):
        """Successful email link sign-in sets cookie and redirects."""
        with patch(
            "backend.app.routers.auth.complete_email_link_signin", return_value="test-id-token"
        ):
            response = await client.get(
                "/auth/callback?oobCode=test-code&mode=signIn&email=test@example.com",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        assert "supabase_access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_callback_invalid_code_redirects(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Invalid email link code redirects to login."""
        with patch(
            "backend.app.routers.auth.complete_email_link_signin",
            side_effect=ValueError("Invalid"),
        ):
            response = await client.get(
                "/auth/callback?oobCode=invalid&mode=signIn&email=test@example.com",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "/auth/login" in response.headers["location"]


class TestLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, client: AsyncClient):
        """Logout clears cookie and redirects to login."""
        response = await client.post("/auth/logout", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"
        assert "max-age=0" in response.headers.get("set-cookie", "").lower()


class TestSession:
    """Tests for GET /auth/session."""

    @pytest.mark.asyncio
    async def test_session_authenticated(self, client: AsyncClient, mock_firebase_auth):
        """Authenticated session returns user info."""
        client.cookies.set("supabase_access_token", "valid_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_session_not_authenticated(self, client: AsyncClient):
        """Unauthenticated session returns false."""
        response = await client.get("/auth/session")

        assert response.status_code == 200
        assert response.json()["authenticated"] is False
