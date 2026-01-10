"""Tests for authentication routes."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"
FIREBASE_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f5"  # Valid UUID format


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
        assert b"<form" in response.content or b"form" in response.content.lower()


class TestSendMagicLink:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_send_magic_link_success(self, client: AsyncClient, mock_firebase_settings):
        """Test successful magic link sending."""
        with patch("backend.app.routers.auth.send_email_link") as mock_send:
            mock_send.return_value = None

            response = await client.post(
                "/auth/login",
                data={"email": "test@example.com"},
            )

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert b"Check your email" in response.content
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_magic_link_missing_email(self, client: AsyncClient):
        """Test that missing email returns 422."""
        response = await client.post("/auth/login", data={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_magic_link_send_failure(self, client: AsyncClient, mock_firebase_settings):
        """Test that send failure shows error message."""
        with patch("backend.app.routers.auth.send_email_link") as mock_send:
            mock_send.side_effect = ValueError("Failed to send")

            response = await client.post(
                "/auth/login",
                data={"email": "test@example.com"},
            )

            assert response.status_code == 200
            assert b"Failed to send" in response.content or b"try again" in response.content.lower()


# Supabase magic link tests (kept for rollback)
# class TestSendMagicLink:
#     """Tests for POST /auth/login endpoint."""
#
#     @pytest.mark.asyncio
#     async def test_send_magic_link_success(self, client: AsyncClient, mock_supabase_client):
#         """Test successful magic link sending."""
#         mock_supabase_client.auth.sign_in_with_otp.return_value = None
#
#         response = await client.post(
#             "/auth/login",
#             data={"email": "test@example.com"},
#         )
#
#         assert response.status_code == 200
#         assert "text/html" in response.headers["content-type"]
#         assert b"Check your email" in response.content
#         mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_send_magic_link_missing_email(self, client: AsyncClient):
#         """Test that missing email returns 422."""
#         response = await client.post("/auth/login", data={})
#
#         assert response.status_code == 422
#
#     @pytest.mark.asyncio
#     async def test_send_magic_link_invalid_email(self, client: AsyncClient, mock_supabase_client):
#         """Test that invalid email format still processes (FastAPI Form doesn't validate format)."""
#         # FastAPI Form(...) only ensures field is present, doesn't validate email format
#         # Supabase will receive the invalid email and handle it
#         mock_supabase_client.auth.sign_in_with_otp.return_value = None
#
#         response = await client.post(
#             "/auth/login",
#             data={"email": "not-an-email"},
#         )
#
#         # Route executes successfully (Supabase handles validation)
#         assert response.status_code == 200
#         mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_send_magic_link_callback_url(self, client: AsyncClient, mock_supabase_client):
#         """Test that callback URL is correctly set in Supabase call."""
#         mock_supabase_client.auth.sign_in_with_otp.return_value = None
#
#         await client.post(
#             "/auth/login",
#             data={"email": "test@example.com"},
#         )
#
#         # Verify sign_in_with_otp was called with correct options
#         call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
#         assert call_args["email"] == "test@example.com"
#         assert "email_redirect_to" in call_args["options"]
#         assert "/auth/callback" in call_args["options"]["email_redirect_to"]


class TestCallback:
    """Tests for GET /auth/callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_no_params_serves_template(self, client: AsyncClient):
        """Test that callback without params serves template."""
        response = await client.get("/auth/callback")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"<script" in response.content or b"script" in response.content.lower()

    @pytest.mark.asyncio
    async def test_callback_auth_error_redirects(self, client: AsyncClient):
        """Test that auth error parameter redirects to login."""
        response = await client.get("/auth/callback?error=access_denied", follow_redirects=False)

        assert response.status_code in (302, 307)
        assert "/auth/login?error=auth_error" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_email_link_success(self, client: AsyncClient, mock_firebase_settings):
        """Test successful email link sign-in."""
        email = "test@example.com"
        oob_code = "test-oob-code"
        id_token = "test-id-token"

        with (
            patch(
                "backend.app.routers.auth.complete_email_link_signin", return_value=id_token
            ) as mock_complete,
            patch("backend.app.routers.auth.verify_firebase_token", return_value=FIREBASE_USER_ID),
        ):
            response = await client.get(
                f"/auth/callback?oobCode={oob_code}&mode=signIn&email={email}",
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert response.headers["location"] == "/"

            cookies = response.cookies
            assert "supabase_access_token" in cookies
            assert cookies["supabase_access_token"] == id_token

            mock_complete.assert_called_once_with(email, oob_code)

    @pytest.mark.asyncio
    async def test_callback_email_link_missing_email(self, client: AsyncClient):
        """Test that email link without email redirects to login."""
        response = await client.get(
            "/auth/callback?oobCode=test-code&mode=signIn",
            follow_redirects=False,
        )

        assert response.status_code in (302, 307)
        assert "/auth/login?error=missing_email" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_email_link_invalid_code(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that invalid email link code redirects to login."""
        email = "test@example.com"
        oob_code = "invalid-code"

        with patch(
            "backend.app.routers.auth.complete_email_link_signin",
            side_effect=ValueError("Invalid code"),
        ):
            response = await client.get(
                f"/auth/callback?oobCode={oob_code}&mode=signIn&email={email}",
                follow_redirects=False,
            )

            assert response.status_code in (302, 307)
            assert "/auth/login?error=invalid_link" in response.headers["location"]


# Supabase callback tests (kept for rollback)
# class TestCallback:
#     """Tests for GET /auth/callback endpoint."""
#
#     @pytest.mark.asyncio
#     async def test_callback_hash_fragment_serves_template(self, client: AsyncClient):
#         """Test that callback without query param serves template."""
#         response = await client.get("/auth/callback")
#
#         assert response.status_code == 200
#         assert "text/html" in response.headers["content-type"]
#         # Should contain JavaScript to extract hash
#         assert b"<script" in response.content or b"script" in response.content.lower()
#
#     @pytest.mark.asyncio
#     async def test_callback_valid_token_sets_cookie(
#         self, client: AsyncClient, mock_supabase_client
#     ):
#         """Test that valid token sets cookie and redirects."""
#         mock_supabase_client.auth.get_user.return_value = make_mock_user_response(TEST_USER_ID)
#
#         response = await client.get(
#             "/auth/callback?access_token=valid_token_here",
#             follow_redirects=False,
#         )
#
#         assert response.status_code == 302
#         assert response.headers["location"] == "/"
#
#         # Check cookie is set
#         cookies = response.cookies
#         assert "supabase_access_token" in cookies
#         assert cookies["supabase_access_token"] == "valid_token_here"
#
#     @pytest.mark.asyncio
#     async def test_callback_invalid_token_redirects_to_login(
#         self, client: AsyncClient, mock_supabase_client
#     ):
#         """Test that invalid token redirects to login with error."""
#         mock_supabase_client.auth.get_user.return_value = None
#
#         response = await client.get(
#             "/auth/callback?access_token=invalid_token",
#             follow_redirects=False,
#         )
#
#         # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
#         assert response.status_code in (302, 307)
#         assert "/auth/login?error=invalid_token" in response.headers["location"]
#
#     @pytest.mark.asyncio
#     async def test_callback_auth_error_redirects_to_login(
#         self, client: AsyncClient, mock_supabase_client
#     ):
#         """Test that AuthApiError redirects to login."""
#         auth_error = AuthApiError(message="Token expired", status=401, code="invalid_token")
#         mock_supabase_client.auth.get_user.side_effect = auth_error
#
#         response = await client.get(
#             "/auth/callback?access_token=expired_token",
#             follow_redirects=False,
#         )
#
#         # FastAPI RedirectResponse uses 307 by default, but 302 is also valid
#         assert response.status_code in (302, 307)
#         assert "/auth/login?error=invalid_token" in response.headers["location"]
#
#     @pytest.mark.asyncio
#     async def test_callback_cookie_settings(self, client: AsyncClient, mock_supabase_client):
#         """Test that cookie has correct security settings."""
#         mock_supabase_client.auth.get_user.return_value = make_mock_user_response(TEST_USER_ID)
#
#         response = await client.get(
#             "/auth/callback?access_token=valid_token",
#             follow_redirects=False,
#         )
#
#         # Check Set-Cookie header contains security settings
#         set_cookie = response.headers.get("set-cookie", "").lower()
#         assert "httponly" in set_cookie
#         assert "samesite=lax" in set_cookie
#         assert "supabase_access_token" in set_cookie


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
    """Tests for GET /auth/session endpoint (now uses Firebase)."""

    @pytest.mark.asyncio
    async def test_session_authenticated_returns_user_id(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that authenticated session returns user info."""
        from unittest.mock import patch

        mock_decoded_token = {"uid": FIREBASE_USER_ID, "email": "test@example.com"}

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.return_value = mock_decoded_token

            client.cookies.set("supabase_access_token", "valid_firebase_token")
            response = await client.get("/auth/session")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["user_id"] == FIREBASE_USER_ID

    @pytest.mark.asyncio
    async def test_session_not_authenticated_returns_false(self, client: AsyncClient):
        """Test that unauthenticated session returns false."""
        response = await client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_session_invalid_token_returns_false(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that invalid Firebase token returns false."""
        from unittest.mock import patch

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.side_effect = ValueError("Invalid token")

            client.cookies.set("supabase_access_token", "invalid_token")
            response = await client.get("/auth/session")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_session_exception_returns_false(
        self, client: AsyncClient, mock_firebase_settings
    ):
        """Test that exception during verification returns false."""
        from unittest.mock import patch

        with (
            patch("backend.app.auth.get_firebase_client") as mock_get_client,
            patch("backend.app.auth.auth") as mock_auth,
        ):
            mock_firebase_app = MagicMock()
            mock_get_client.return_value = mock_firebase_app
            mock_auth.verify_id_token.side_effect = Exception("Firebase error")

            client.cookies.set("supabase_access_token", "expired_token")
            response = await client.get("/auth/session")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
