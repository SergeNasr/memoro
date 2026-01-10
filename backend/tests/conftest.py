"""Pytest configuration and fixtures."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import asyncpg
import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from backend.app.auth import get_current_user, require_auth
from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.main import app


def pytest_configure(config):
    """Configure pytest - runs before test collection."""
    # Mock firebase_admin before any service imports
    # This must happen in pytest_configure because imports happen before fixtures run
    mock_firebase_admin = MagicMock()
    mock_firebase_auth = MagicMock()
    mock_firebase_credentials = MagicMock()
    mock_firebase_initialize_app = MagicMock()

    mock_firebase_admin.auth = mock_firebase_auth
    mock_firebase_admin.credentials = mock_firebase_credentials
    mock_firebase_admin.initialize_app = mock_firebase_initialize_app

    # Patch firebase_admin module before any service imports
    patch.dict(sys.modules, {"firebase_admin": mock_firebase_admin}).start()


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    # Clear any existing overrides before tests
    app.dependency_overrides.clear()

    # Mock authentication dependencies to return test user_id
    # This allows all tests to pass authentication checks
    test_user_id = UUID("00000000-0000-0000-0000-000000000001")

    async def mock_require_auth(request: Request) -> UUID:
        return test_user_id

    async def mock_get_current_user(request: Request) -> UUID:
        return test_user_id

    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[get_current_user] = mock_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Clean up after tests
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_id() -> UUID:
    """Test user ID for database operations."""
    return UUID("00000000-0000-0000-0000-000000000001")


def make_openai_completion(contact, interaction, relationships=None):
    """Helper to create mock OpenAI completion response."""
    mock_completion = MagicMock()
    mock_completion.model = "gpt-4o-2024-08-06"
    mock_completion.choices = [
        MagicMock(
            finish_reason="stop",
            message=MagicMock(
                parsed=MagicMock(
                    contact=contact,
                    interaction=interaction,
                    relationships=relationships or [],
                )
            ),
        )
    ]
    mock_completion.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    return mock_completion


@pytest.fixture
def mock_openai_client():
    """Fixture to mock OpenAI client."""
    with patch("backend.app.services.llm.client") as mock_client:
        # Setup default async mock for embeddings.create()
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=[0.1] * 1536)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        yield mock_client


@pytest.fixture
def mock_db_connection():
    """
    Mock database connection for FastAPI dependency injection.

    Automatically overrides get_db_dependency in the app.

    Usage:
        def test_something(client, mock_db_connection):
            # Setup mock behavior
            mock_db_connection.fetchrow.return_value = {...}
            # Test will use the mocked connection
            response = await client.get("/api/contacts/...")
    """
    mock_conn = AsyncMock(spec=asyncpg.Connection)
    mock_conn.make_record = _make_mock_record

    # Automatically override the dependency
    app.dependency_overrides[get_db_dependency] = lambda: mock_conn

    yield mock_conn

    # Clean up is handled by client fixture


@pytest.fixture
def mock_db_transaction():
    """
    Mock database transaction for FastAPI dependency injection.

    Automatically overrides get_db_transaction_dependency in the app.

    Usage:
        def test_something(client, mock_db_transaction):
            # Setup mock behavior
            mock_db_transaction.fetchrow.return_value = {...}
            # Test will use the mocked transaction
            response = await client.post("/api/interactions/confirm", ...)
    """
    from uuid import uuid4

    mock_conn = AsyncMock(spec=asyncpg.Connection)

    # Default contact record
    mock_conn.fetchrow.return_value = _make_mock_record(
        id=uuid4(),
        first_name="Sarah",
        last_name="Johnson",
        birthday=None,
        latest_news="Test interaction",
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
    )

    # Mock execute for UPDATE/DELETE
    mock_conn.execute.return_value = None
    mock_conn.make_record = _make_mock_record

    # Automatically override the dependency
    app.dependency_overrides[get_db_transaction_dependency] = lambda: mock_conn

    yield mock_conn

    # Clean up is handled by client fixture


def _make_mock_record(**kwargs):
    """Helper to create a mock database record-like object."""

    class MockRecord(dict):
        def __getitem__(self, key):
            return super().__getitem__(key)

    return MockRecord(**kwargs)


TEST_USER_ID = "2276f96c-bc1a-4cf5-a20c-6b75cd2fe2f4"


@pytest.fixture
def mock_firebase_settings():
    """Mock Firebase settings for testing."""
    from backend.app.config import settings

    with (
        patch.object(
            settings, "firebase_service_account_path", "/path/to/service-account.json", create=True
        ),
        patch.object(settings, "firebase_project_id", "test-project-id", create=True),
        patch.object(settings, "firebase_web_api_key", "test-api-key", create=True),
        patch("backend.app.services.firebase_auth.settings", settings),
    ):
        yield settings


@pytest.fixture
def mock_firebase_auth(mock_firebase_settings):
    """
    Mock Firebase Auth for testing token verification.

    Usage:
        def test_something(mock_firebase_auth):
            mock_firebase_auth.set_user(user_id="...", email="...")
            # or
            mock_firebase_auth.set_error(ValueError("Invalid"))
    """

    class FirebaseMock:
        def __init__(self):
            self.app = MagicMock()
            self.auth = MagicMock()
            self._decoded_token = {"uid": TEST_USER_ID, "email": "test@example.com"}

        def set_user(self, user_id: str, email: str = "test@example.com"):
            self._decoded_token = {"uid": user_id, "email": email}
            self.auth.verify_id_token.return_value = self._decoded_token

        def set_error(self, error: Exception):
            self.auth.verify_id_token.side_effect = error

    mock = FirebaseMock()
    mock.auth.verify_id_token.return_value = mock._decoded_token

    with (
        patch("backend.app.auth.get_firebase_client", return_value=mock.app),
        patch("backend.app.auth.auth", mock.auth),
        patch("backend.app.services.firebase_auth.get_firebase_client", return_value=mock.app),
        patch("backend.app.services.firebase_auth.auth", mock.auth),
    ):
        yield mock
