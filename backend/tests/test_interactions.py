"""Tests for interaction endpoints."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


class TestAnalyzeInteraction:
    """Tests for POST /api/interactions/analyze endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_interaction_success(self, client: AsyncClient, mock_openrouter_client):
        """Test successful interaction analysis."""
        with patch("backend.app.services.llm.httpx.AsyncClient", return_value=mock_openrouter_client):
            response = await client.post(
                "/api/interactions/analyze",
                json={
                    "text": "Had coffee with Sarah Johnson at Starbucks today. "
                    "She mentioned her birthday is March 15th and her daughter Emma just started college."
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Verify contact extraction
        assert data["contact"]["first_name"] == "Sarah"
        assert data["contact"]["last_name"] == "Johnson"
        assert data["contact"]["birthday"] == "1985-03-15"
        assert data["contact"]["confidence"] == 0.95

        # Verify interaction extraction
        assert "coffee" in data["interaction"]["notes"].lower()
        assert data["interaction"]["location"] == "Starbucks"
        assert data["interaction"]["interaction_date"] == "2025-10-02"
        assert data["interaction"]["confidence"] == 0.9

        # Verify family members
        assert len(data["family_members"]) == 1
        assert data["family_members"][0]["first_name"] == "Emma"
        assert data["family_members"][0]["relationship"] == "child"

        # Verify raw text is preserved
        assert "Sarah Johnson" in data["raw_text"]

    @pytest.mark.asyncio
    async def test_analyze_interaction_empty_text(self, client: AsyncClient):
        """Test validation error for empty text."""
        response = await client.post(
            "/api/interactions/analyze",
            json={"text": ""},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_analyze_interaction_missing_text(self, client: AsyncClient):
        """Test validation error for missing text field."""
        response = await client.post(
            "/api/interactions/analyze",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_analyze_interaction_api_error(self, client: AsyncClient):
        """Test handling of OpenRouter API errors."""
        from httpx import HTTPStatusError, Request, Response

        mock_client = patch("backend.app.services.llm.httpx.AsyncClient")

        with mock_client as mock:
            mock_instance = mock.return_value.__aenter__.return_value
            mock_response = Response(500, request=Request("POST", "http://test"))
            mock_instance.post.return_value = mock_response

            # Configure raise_for_status to raise an error
            def raise_error():
                raise HTTPStatusError("API Error", request=mock_response.request, response=mock_response)

            mock_response.raise_for_status = raise_error

            response = await client.post(
                "/api/interactions/analyze",
                json={"text": "Test interaction text"},
            )

        assert response.status_code == 500
        assert "Failed to analyze interaction" in response.json()["detail"]


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
