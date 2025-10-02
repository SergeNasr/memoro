"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_openrouter_response():
    """Mock OpenRouter API response for interaction analysis."""
    return {
        "choices": [
            {
                "message": {
                    "content": """{
                        "contact": {
                            "first_name": "Sarah",
                            "last_name": "Johnson",
                            "birthday": "1985-03-15",
                            "confidence": 0.95
                        },
                        "interaction": {
                            "notes": "Had coffee together, discussed daughter starting college",
                            "location": "Starbucks",
                            "interaction_date": "2025-10-02",
                            "confidence": 0.9
                        },
                        "family_members": [
                            {
                                "first_name": "Emma",
                                "last_name": "Johnson",
                                "relationship": "child",
                                "confidence": 0.85
                            }
                        ]
                    }"""
                }
            }
        ]
    }


@pytest.fixture
def mock_openrouter_client(mock_openrouter_response):
    """
    Mock httpx.AsyncClient for OpenRouter API calls.

    Usage in tests:
        async def test_something(mock_openrouter_client):
            with mock_openrouter_client:
                # Your test code that calls OpenRouter
                result = await analyze_interaction("test text")
    """
    mock_response = Mock()
    mock_response.json.return_value = mock_openrouter_response
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    return mock_client
