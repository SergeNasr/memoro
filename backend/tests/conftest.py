"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock
from uuid import UUID

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    # Clear any existing overrides before tests
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Clean up after tests
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_id() -> UUID:
    """Test user ID for database operations."""
    return UUID("00000000-0000-0000-0000-000000000001")


def make_openai_completion(contact, interaction, family_members=None):
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
                    family_members=family_members or [],
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
