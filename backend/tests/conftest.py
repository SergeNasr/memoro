"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import asyncpg
import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from backend.app.auth import get_authenticated_user, get_supabase_client, require_auth
from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.main import app


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

    async def mock_get_authenticated_user(request: Request) -> UUID:
        return test_user_id

    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[get_authenticated_user] = mock_get_authenticated_user

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
    from unittest.mock import MagicMock

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
    from unittest.mock import patch

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

    # Mock fetchrow to return a record-like object
    def make_record(**kwargs):
        class MockRecord(dict):
            def __getitem__(self, key):
                return super().__getitem__(key)

        return MockRecord(**kwargs)

    mock_conn.make_record = make_record

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

    # Mock fetchrow to return a record-like object
    def make_record(**kwargs):
        class MockRecord(dict):
            def __getitem__(self, key):
                return super().__getitem__(key)

        return MockRecord(**kwargs)

    # Default contact record
    mock_conn.fetchrow.return_value = make_record(
        id=uuid4(),
        first_name="Sarah",
        last_name="Johnson",
        birthday=None,
        latest_news="Test interaction",
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
    )

    # Mock execute for UPDATE/DELETE
    mock_conn.execute.return_value = None
    mock_conn.make_record = make_record

    # Automatically override the dependency
    app.dependency_overrides[get_db_transaction_dependency] = lambda: mock_conn

    yield mock_conn

    # Clean up is handled by client fixture


def make_mock_user_response(user_id: str):
    """Helper to create mock Supabase user response."""
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user_response = MagicMock()
    mock_user_response.user = mock_user
    return mock_user_response


@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client for testing.

    Automatically overrides get_supabase_client dependency and patches
    the function call in auth.py for routes that use dependency injection
    and functions that call it directly.

    Usage:
        def test_something(client, mock_supabase_client):
            # Setup mock behavior
            mock_supabase_client.auth.get_user.return_value = make_mock_user_response("...")
            # Test will use the mocked client
            response = await client.post("/auth/login", ...)
    """
    mock_client = MagicMock()

    # Override dependency for routes using Depends(get_supabase_client)
    app.dependency_overrides[get_supabase_client] = lambda: mock_client

    # Patch for functions calling get_supabase_client() directly (like get_current_user)
    with patch("backend.app.auth.get_supabase_client", return_value=mock_client):
        yield mock_client

    # Clean up dependency override
    app.dependency_overrides.pop(get_supabase_client, None)
