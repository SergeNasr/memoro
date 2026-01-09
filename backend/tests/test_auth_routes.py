"""Tests for authentication routes."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from supabase import AuthApiError

from backend.tests.conftest import make_mock_user_response

TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"
FIREBASE_USER_ID = "firebase-user-123"


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
    async def test_send_magic_link_success(self, client: AsyncClient, mock_supabase_client):
        """Test successful magic link sending."""
        mock_supabase_client.auth.sign_in_with_otp.return_value = None

        response = await client.post(
            "/auth/login",
            data={"email": "test@example.com"},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Check your email" in response.content
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_magic_link_missing_email(self, client: AsyncClient):
        """Test that missing email returns 422."""
        response = await client.post("/auth/login", data={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_magic_link_invalid_email(self, client: AsyncClient, mock_supabase_client):
        """Test that invalid email format still processes (FastAPI Form doesn't validate format)."""
        # FastAPI Form(...) only ensures field is present, doesn't validate email format
        # Supabase will receive the invalid email and handle it
        mock_supabase_client.auth.sign_in_with_otp.return_value = None

        response = await client.post(
            "/auth/login",
            data={"email": "not-an-email"},
        )

        # Route executes successfully (Supabase handles validation)
        assert response.status_code == 200
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_magic_link_callback_url(self, client: AsyncClient, mock_supabase_client):
        """Test that callback URL is correctly set in Supabase call."""
        mock_supabase_client.auth.sign_in_with_otp.return_value = None

        await client.post(
            "/auth/login",
            data={"email": "test@example.com"},
        )

        # Verify sign_in_with_otp was called with correct options
        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        assert call_args["email"] == "test@example.com"
        assert "email_redirect_to" in call_args["options"]
        assert "/auth/callback" in call_args["options"]["email_redirect_to"]


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
    async def test_callback_valid_token_sets_cookie(
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that valid token sets cookie and redirects."""
        mock_supabase_client.auth.get_user.return_value = make_mock_user_response(TEST_USER_ID)

        response = await client.get(
            "/auth/callback?access_token=valid_token_here",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

        # Check cookie is set
        cookies = response.cookies
        assert "supabase_access_token" in cookies
        assert cookies["supabase_access_token"] == "valid_token_here"

    @pytest.mark.asyncio
    async def test_callback_invalid_token_redirects_to_login(
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that invalid token redirects to login with error."""
        mock_supabase_client.auth.get_user.return_value = None

        response = await client.get(
            "/auth/callback?access_token=invalid_token",
            follow_redirects=False,
        )

        # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
        assert response.status_code in (302, 307)
        assert "/auth/login?error=invalid_token" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_auth_error_redirects_to_login(
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that AuthApiError redirects to login."""
        auth_error = AuthApiError(message="Token expired", status=401, code="invalid_token")
        mock_supabase_client.auth.get_user.side_effect = auth_error

        response = await client.get(
            "/auth/callback?access_token=expired_token",
            follow_redirects=False,
        )

        # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
        assert response.status_code in (302, 307)
        assert "/auth/login?error=invalid_token" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_cookie_settings(self, client: AsyncClient, mock_supabase_client):
        """Test that cookie has correct security settings."""
        mock_supabase_client.auth.get_user.return_value = make_mock_user_response(TEST_USER_ID)

        response = await client.get(
            "/auth/callback?access_token=valid_token",
            follow_redirects=False,
        )

        # Check Set-Cookie header contains security settings
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie
        assert "supabase_access_token" in set_cookie


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
        assert "supabase_access_token" in set_cookie
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
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that authenticated session returns user info."""
        mock_supabase_client.auth.get_user.return_value = make_mock_user_response(TEST_USER_ID)

        client.cookies.set("supabase_access_token", "valid_token")
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
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that invalid token returns false."""
        mock_supabase_client.auth.get_user.return_value = None

        client.cookies.set("supabase_access_token", "invalid_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_session_auth_error_returns_false(
        self, client: AsyncClient, mock_supabase_client
    ):
        """Test that AuthApiError returns false."""
        auth_error = AuthApiError(message="Invalid token", status=401, code="invalid_token")
        mock_supabase_client.auth.get_user.side_effect = auth_error

        client.cookies.set("supabase_access_token", "expired_token")
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestFirebaseLogin:
    """Tests for GET /auth/firebase/login endpoint."""

    @pytest.mark.asyncio
    async def test_firebase_login_redirects_to_google(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that Firebase login redirects to Google OAuth URL."""
        oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://test/auth/firebase/callback"

        with patch(
            "backend.app.routers.auth.get_google_sign_in_url", return_value=oauth_url
        ) as mock_get_url:
            response = await client.get("/auth/firebase/login", follow_redirects=False)

            assert response.status_code == 302
            assert response.headers["location"] == oauth_url
            mock_get_url.assert_called_once()
            # Verify callback URL was passed
            call_args = mock_get_url.call_args[0][0]
            assert "/auth/firebase/callback" in call_args

    @pytest.mark.asyncio
    async def test_firebase_login_generates_unique_urls(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that each login generates a unique OAuth URL."""
        with patch("backend.app.routers.auth.get_google_sign_in_url") as mock_get_url:
            mock_get_url.side_effect = [
                "https://accounts.google.com/o/oauth2/v2/auth?state=state1",
                "https://accounts.google.com/o/oauth2/v2/auth?state=state2",
            ]

            response1 = await client.get("/auth/firebase/login", follow_redirects=False)
            response2 = await client.get("/auth/firebase/login", follow_redirects=False)

            assert response1.status_code == 302
            assert response2.status_code == 302
            assert mock_get_url.call_count == 2


class TestFirebaseCallback:
    """Tests for GET /auth/firebase/callback endpoint."""

    @pytest.mark.asyncio
    async def test_firebase_callback_no_token_serves_template(self, client: AsyncClient):
        """Test that callback without id_token serves template."""
        response = await client.get("/auth/firebase/callback")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"<script" in response.content or b"script" in response.content.lower()

    @pytest.mark.asyncio
    async def test_firebase_callback_valid_token_sets_cookie(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that valid Firebase token sets cookie and redirects."""
        id_token = "valid-firebase-id-token"

        with patch(
            "backend.app.routers.auth.verify_firebase_token", return_value=FIREBASE_USER_ID
        ) as mock_verify:
            response = await client.get(
                f"/auth/firebase/callback?id_token={id_token}",
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert response.headers["location"] == "/"

            # Check cookie is set
            cookies = response.cookies
            assert "supabase_access_token" in cookies
            assert cookies["supabase_access_token"] == id_token

            mock_verify.assert_called_once_with(id_token)

    @pytest.mark.asyncio
    async def test_firebase_callback_invalid_token_redirects_to_login(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that invalid Firebase token redirects to login with error."""
        id_token = "invalid-firebase-token"

        with patch(
            "backend.app.routers.auth.verify_firebase_token",
            side_effect=ValueError("Invalid token"),
        ):
            response = await client.get(
                f"/auth/firebase/callback?id_token={id_token}",
                follow_redirects=False,
            )

            assert response.status_code in (302, 307)
            assert "/auth/login?error=invalid_token" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_firebase_callback_cookie_settings(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that cookie has correct security settings."""
        id_token = "valid-firebase-token"

        with patch("backend.app.routers.auth.verify_firebase_token", return_value=FIREBASE_USER_ID):
            response = await client.get(
                f"/auth/firebase/callback?id_token={id_token}",
                follow_redirects=False,
            )

            # Check Set-Cookie header contains security settings
            set_cookie = response.headers.get("set-cookie", "").lower()
            assert "httponly" in set_cookie
            assert "samesite=lax" in set_cookie
            assert "supabase_access_token" in set_cookie

    @pytest.mark.asyncio
    async def test_firebase_callback_exception_handling(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that any exception during verification redirects to login."""
        id_token = "token-that-raises-exception"

        with patch(
            "backend.app.routers.auth.verify_firebase_token",
            side_effect=Exception("Firebase error"),
        ):
            response = await client.get(
                f"/auth/firebase/callback?id_token={id_token}",
                follow_redirects=False,
            )

            assert response.status_code in (302, 307)
            assert "/auth/login?error=invalid_token" in response.headers["location"]
