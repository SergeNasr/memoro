"""Tests for search endpoint."""

from datetime import date
from uuid import uuid4

from httpx import AsyncClient


class TestSearch:
    """Search functionality tests."""

    async def test_empty_results(self, client: AsyncClient, mock_db_connection, mock_openai_client):
        """Search with no results."""
        mock_db_connection.fetch.side_effect = [[], [], [], [], []]  # All search types empty

        response = await client.post("/api/search", json={"query": "nonexistent", "limit": 10})
        assert response.status_code == 200
        assert response.json()["total_results"] == 0

    async def test_hybrid_combines_results(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Hybrid search combines fuzzy, term, and semantic results."""
        contact_id = uuid4()
        mock_interaction = mock_db_connection.make_record(
            id=uuid4(),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Coffee meeting",
            location="Starbucks",
            first_name="Alice",
            last_name="Smith",
            birthday=None,
            latest_news=None,
            score=0.8,
        )

        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [dict(mock_interaction, score=0.7)],  # interaction_fuzzy
            [],  # contact_term
            [dict(mock_interaction, score=1.0)],  # interaction_term
            [dict(mock_interaction, score=0.9)],  # interaction_semantic
        ]

        response = await client.post("/api/search", json={"query": "coffee meeting", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        # Weighted score: 0.9*0.5 + 0.7*0.3 + 1.0*0.2 = 0.86
        assert abs(data["results"][0]["score"] - 0.86) < 0.01

    async def test_deduplicates(self, client: AsyncClient, mock_db_connection, mock_openai_client):
        """Deduplicates same interaction across search types."""
        contact_id = uuid4()
        mock_interaction = mock_db_connection.make_record(
            id=uuid4(),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Meeting",
            location="Office",
            first_name="Bob",
            last_name="Jones",
            birthday=None,
            latest_news=None,
            score=0.8,
        )

        mock_db_connection.fetch.side_effect = [
            [],
            [mock_interaction],
            [],
            [mock_interaction],
            [mock_interaction],
        ]

        response = await client.post("/api/search", json={"query": "meeting", "limit": 10})
        assert response.status_code == 200
        assert response.json()["total_results"] == 1

    async def test_respects_limit(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Search respects result limit."""
        contacts = [
            mock_db_connection.make_record(
                contact_id=uuid4(),
                first_name=f"User{i}",
                last_name=f"Name{i}",
                birthday=None,
                latest_news=None,
                score=0.9 - (i * 0.1),
            )
            for i in range(5)
        ]

        mock_db_connection.fetch.side_effect = [contacts[:3], [], contacts[1:4], [], contacts[:4]]

        response = await client.post("/api/search", json={"query": "test", "limit": 3})
        assert response.status_code == 200
        assert response.json()["total_results"] == 3

    async def test_validation(self, client: AsyncClient, mock_db_connection):
        """Search validates input."""
        # Missing query
        response = await client.post("/api/search", json={"limit": 10})
        assert response.status_code == 422

        # Empty query
        response = await client.post("/api/search", json={"query": "", "limit": 10})
        assert response.status_code == 422

        # Invalid limit
        response = await client.post("/api/search", json={"query": "test", "limit": 101})
        assert response.status_code == 422
