"""Tests for authentication routes."""

import pytest
from httpx import AsyncClient

from backend.app.auth_provider import AuthProviderError
from backend.tests.conftest import make_mock_user_response

TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"


class TestLoginPage:
    """Tests for GET /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_page_returns_html(self, client: AsyncClient):
        """Test that login page returns HTML form."""
        response = await client.get("/auth/login")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Email" in response.content or b"email" in response.content

    @pytest.mark.asyncio
    async def test_login_page_renders_template(self, client: AsyncClient):
        """Test that login page renders correct template."""
        response = await client.get("/auth/login")

        assert response.status_code == 200
        # Should contain form elements
        assert b"<form" in response.content or b"form" in response.content.lower()


class TestSendMagicLink:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_send_magic_link_success(self, client: AsyncClient, mock_auth_provider):
        """Test successful magic link sending."""
        mock_auth_provider.send_magic_link.return_value = None

        response = await client.post(
            "/auth/login",
            data={"email": "test@example.com"},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Check your email" in response.content
        mock_auth_provider.send_magic_link.assert_called_once()
        call_args = mock_auth_provider.send_magic_link.call_args[0]
        assert call_args[0] == "test@example.com"
        assert "/auth/callback" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_magic_link_missing_email(self, client: AsyncClient):
        """Test that missing email returns 422."""
        response = await client.post("/auth/login", data={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_magic_link_invalid_email(self, client: AsyncClient, mock_auth_provider):
        """Test that invalid email format still processes (FastAPI Form doesn't validate format)."""
        # FastAPI Form(...) only ensures field is present, doesn't validate email format
        # Auth provider will receive the invalid email and handle it
        mock_auth_provider.send_magic_link.return_value = None

        response = await client.post(
            "/auth/login",
            data={"email": "not-an-email"},
        )

        # Route executes successfully (auth provider handles validation)
        assert response.status_code == 200
        mock_auth_provider.send_magic_link.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_magic_link_callback_url(self, client: AsyncClient, mock_auth_provider):
        """Test that callback URL is correctly set in auth provider call."""
        mock_auth_provider.send_magic_link.return_value = None

        await client.post(
            "/auth/login",
            data={"email": "test@example.com"},
        )

        # Verify send_magic_link was called with correct callback URL
        call_args = mock_auth_provider.send_magic_link.call_args[0]
        assert call_args[0] == "test@example.com"
        assert "/auth/callback" in call_args[1]


class TestCallback:
    """Tests for GET /auth/callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_hash_fragment_serves_template(self, client: AsyncClient):
        """Test that callback without query param serves template."""
        response = await client.get("/auth/callback")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain JavaScript to extract hash
        assert b"<script" in response.content or b"script" in response.content.lower()

    @pytest.mark.asyncio
    async def test_callback_valid_session_sets_cookie(
        self, client: AsyncClient, mock_auth_provider
    ):
        """Test that valid Clerk session ID sets cookie and redirects."""
        mock_auth_provider.get_session_token.return_value = "token_from_session"
        mock_auth_provider.get_user_from_token.return_value = make_mock_user_response(TEST_USER_ID)

        response = await client.get(
            "/auth/callback?__clerk_created_session=session_id_123",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

        # Check cookie is set
        cookies = response.cookies
        assert "clerk_session_token" in cookies
        assert cookies["clerk_session_token"] == "token_from_session"
        mock_auth_provider.get_session_token.assert_called_once_with("session_id_123")

    @pytest.mark.asyncio
    async def test_callback_invalid_session_redirects_to_login(
        self, client: AsyncClient, mock_auth_provider
    ):
        """Test that invalid session ID redirects to login with error."""
        mock_auth_provider.get_session_token.side_effect = AuthProviderError("Invalid session")

        response = await client.get(
            "/auth/callback?__clerk_created_session=invalid_session",
            follow_redirects=False,
        )

        # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
        assert response.status_code in (302, 307)
        assert "/auth/login?error=invalid_token" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_auth_error_redirects_to_login(
        self, client: AsyncClient, mock_auth_provider
    ):
        """Test that AuthProviderError during token validation redirects to login."""
        mock_auth_provider.get_session_token.return_value = "token"
        auth_error = AuthProviderError("Token expired")
        mock_auth_provider.get_user_from_token.side_effect = auth_error

        response = await client.get(
            "/auth/callback?__clerk_created_session=session_id",
            follow_redirects=False,
        )

        # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
        assert response.status_code in (302, 307)
        assert "/auth/login?error=invalid_token" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_cookie_settings(self, client: AsyncClient, mock_auth_provider):
        """Test that cookie has correct security settings."""
        mock_auth_provider.get_session_token.return_value = "token"
        mock_auth_provider.get_user_from_token.return_value = make_mock_user_response(TEST_USER_ID)

        response = await client.get(
            "/auth/callback?__clerk_created_session=session_id",
            follow_redirects=False,
        )

        # Check Set-Cookie header contains security settings
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie
        assert "clerk_session_token" in set_cookie


class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookie_and_redirects(self, client: AsyncClient):
        """Test that logout clears cookie and redirects to login."""
        response = await client.post("/auth/logout", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

        # Check cookie is deleted (max-age=0 or expires in past)
        set_cookie = response.headers.get("set-cookie", "")
        assert "clerk_session_token" in set_cookie
        # Cookie deletion typically has max-age=0 or expires
        assert "max-age=0" in set_cookie or "expires=" in set_cookie.lower()

    @pytest.mark.asyncio
    async def test_logout_cookie_deletion_settings(self, client: AsyncClient):
        """Test that cookie deletion has correct settings."""
        response = await client.post("/auth/logout", follow_redirects=False)

        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie


class TestSession:
    """Tests for GET /auth/session endpoint."""

    @pytest.mark.asyncio
    async def test_session_authenticated_returns_user_id(
        self, client: AsyncClient, mock_auth_provider
    ):
        """Test that authenticated session returns user info."""
        mock_auth_provider.verify_token.return_value = make_mock_user_response(TEST_USER_ID)

        client.cookies.set("clerk_session_token", "valid_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_session_not_authenticated_returns_false(self, client: AsyncClient):
        """Test that unauthenticated session returns false."""
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_session_invalid_token_returns_false(
        self, client: AsyncClient, mock_auth_provider
    ):
        """Test that invalid token returns false."""
        mock_auth_provider.verify_token.return_value = {}

        client.cookies.set("clerk_session_token", "invalid_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_session_auth_error_returns_false(self, client: AsyncClient, mock_auth_provider):
        """Test that AuthProviderError returns false."""
        auth_error = AuthProviderError("Invalid token")
        mock_auth_provider.verify_token.side_effect = auth_error

        client.cookies.set("clerk_session_token", "expired_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
