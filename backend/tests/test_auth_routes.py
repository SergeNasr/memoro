"""Tests for authentication routes."""

from unittest.mock import patch

from httpx import AsyncClient

from backend.tests.conftest import TEST_USER_ID


class TestAuth:
    """Auth flow tests."""

    async def test_login_page(self, client: AsyncClient):
        """Login page returns HTML."""
        response = await client.get("/auth/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_magic_link_success(self, client: AsyncClient, mock_firebase_settings):
        """Successful magic link sends confirmation."""
        with patch("backend.app.routers.auth.send_email_link"):
            response = await client.post("/auth/login", data={"email": "test@example.com"})
        assert response.status_code == 200
        assert b"Check your email" in response.content

    async def test_magic_link_failure(self, client: AsyncClient, mock_firebase_settings):
        """Failed magic link shows error."""
        with patch("backend.app.routers.auth.send_email_link", side_effect=ValueError("Failed")):
            response = await client.post("/auth/login", data={"email": "test@example.com"})
        assert response.status_code == 200
        assert b"Failed" in response.content or b"try again" in response.content.lower()

    async def test_callback_success(self, client: AsyncClient, mock_firebase_auth):
        """Successful callback sets cookie and redirects."""
        with patch(
            "backend.app.routers.auth.complete_email_link_signin", return_value="test-id-token"
        ):
            response = await client.get(
                "/auth/callback?oobCode=test-code&mode=signIn&email=test@example.com",
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert response.headers["location"] == "/"
        assert "access_token" in response.cookies

    async def test_callback_invalid(self, client: AsyncClient, mock_firebase_settings):
        """Invalid callback redirects to login."""
        with patch(
            "backend.app.routers.auth.complete_email_link_signin", side_effect=ValueError("Invalid")
        ):
            response = await client.get(
                "/auth/callback?oobCode=invalid&mode=signIn&email=test@example.com",
                follow_redirects=False,
            )
        assert response.status_code in (302, 307)
        assert "/auth/login" in response.headers["location"]

    async def test_logout(self, client: AsyncClient):
        """Logout clears cookie and redirects."""
        response = await client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    async def test_session_authenticated(self, client: AsyncClient, mock_firebase_auth):
        """Authenticated session returns user info."""
        client.cookies.set("access_token", "valid_token")
        response = await client.get("/auth/session")
        assert response.status_code == 200
        assert response.json()["authenticated"] is True
        assert response.json()["user_id"] == TEST_USER_ID

    async def test_session_unauthenticated(self, client: AsyncClient):
        """Unauthenticated session returns false."""
        response = await client.get("/auth/session")
        assert response.status_code == 200
        assert response.json()["authenticated"] is False
