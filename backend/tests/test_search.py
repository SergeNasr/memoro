"""Tests for search endpoints."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestSearch:
    """Tests for POST /api/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_fuzzy_contacts(self, client: AsyncClient, mock_db_connection):
        """Test fuzzy search for contacts."""

        contact_id = uuid4()

        # Mock fuzzy search on contacts
        mock_db_connection.fetch.side_effect = [
            # Contact results
            [
                mock_db_connection.make_record(
                    id=contact_id,
                    first_name="Alice",
                    last_name="Anderson",
                    birthday=date(1990, 1, 1),
                    latest_news="Recent update",
                    score=0.85,
                ),
            ],
            # Interaction results (empty)
            [],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "alice", "search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "alice"
        assert data["search_type"] == "fuzzy"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["result_type"] == "contact"
        assert data["results"][0]["contact"]["first_name"] == "Alice"
        assert data["results"][0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_search_fuzzy_interactions(self, client: AsyncClient, mock_db_connection):
        """Test fuzzy search for interactions."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock fuzzy search
        mock_db_connection.fetch.side_effect = [
            # Contact results (empty)
            [],
            # Interaction results
            [
                mock_db_connection.make_record(
                    id=interaction_id,
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 15),
                    notes="Had coffee at Starbucks",
                    location="Starbucks",
                    contact_first_name="Bob",
                    contact_last_name="Brown",
                    score=0.75,
                ),
            ],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "coffee", "search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 1
        assert data["results"][0]["result_type"] == "interaction"
        assert data["results"][0]["interaction"]["notes"] == "Had coffee at Starbucks"
        assert data["results"][0]["score"] == 0.75

    @pytest.mark.asyncio
    async def test_search_term_contacts(self, client: AsyncClient, mock_db_connection):
        """Test term search for contacts."""

        contact_id = uuid4()

        # Mock term search
        mock_db_connection.fetch.side_effect = [
            # Contact results
            [
                mock_db_connection.make_record(
                    id=contact_id,
                    first_name="Charlie",
                    last_name="Chen",
                    birthday=None,
                    latest_news="Working at Google",
                    score=1.0,
                ),
            ],
            # Interaction results (empty)
            [],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "google", "search_type": "term", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["search_type"] == "term"
        assert data["total_results"] == 1
        assert data["results"][0]["contact"]["latest_news"] == "Working at Google"
        assert data["results"][0]["score"] == 1.0

    @pytest.mark.asyncio
    async def test_search_term_interactions(self, client: AsyncClient, mock_db_connection):
        """Test term search for interactions."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock term search
        mock_db_connection.fetch.side_effect = [
            # Contact results (empty)
            [],
            # Interaction results
            [
                mock_db_connection.make_record(
                    id=interaction_id,
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 10),
                    notes="Discussed Python project",
                    location="Office",
                    contact_first_name="Diana",
                    contact_last_name="Davis",
                    score=1.0,
                ),
            ],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "python", "search_type": "term", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 1
        assert data["results"][0]["interaction"]["notes"] == "Discussed Python project"

    @pytest.mark.asyncio
    async def test_search_combined_results(self, client: AsyncClient, mock_db_connection):
        """Test search returning both contacts and interactions."""

        contact_id = uuid4()
        interaction_id = uuid4()

        # Mock fuzzy search with both types
        mock_db_connection.fetch.side_effect = [
            # Contact results
            [
                mock_db_connection.make_record(
                    id=contact_id,
                    first_name="Eve",
                    last_name="Evans",
                    birthday=None,
                    latest_news="Loves basketball",
                    score=0.90,
                ),
            ],
            # Interaction results
            [
                mock_db_connection.make_record(
                    id=interaction_id,
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 5),
                    notes="Played basketball together",
                    location="Park",
                    contact_first_name="Eve",
                    contact_last_name="Evans",
                    score=0.88,
                ),
            ],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "basketball", "search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 2
        # Results should be sorted by score (0.90, 0.88)
        assert data["results"][0]["result_type"] == "contact"
        assert data["results"][0]["score"] == 0.90
        assert data["results"][1]["result_type"] == "interaction"
        assert data["results"][1]["score"] == 0.88

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client: AsyncClient, mock_db_connection):
        """Test search with no results."""

        # Mock empty results
        mock_db_connection.fetch.side_effect = [
            [],  # Contact results
            [],  # Interaction results
        ]

        response = await client.post(
            "/api/search",
            json={"query": "nonexistent", "search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_limit_applied(self, client: AsyncClient, mock_db_connection):
        """Test that search limit is properly applied."""

        # Mock many results
        mock_db_connection.fetch.side_effect = [
            # 5 contact results
            [
                mock_db_connection.make_record(
                    id=uuid4(),
                    first_name=f"User{i}",
                    last_name=f"Name{i}",
                    birthday=None,
                    latest_news=None,
                    score=0.9 - (i * 0.1),
                )
                for i in range(5)
            ],
            # 5 interaction results
            [
                mock_db_connection.make_record(
                    id=uuid4(),
                    contact_id=uuid4(),
                    interaction_date=date(2024, 1, i + 1),
                    notes=f"Note {i}",
                    location=None,
                    contact_first_name="Test",
                    contact_last_name="User",
                    score=0.8 - (i * 0.1),
                )
                for i in range(5)
            ],
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "fuzzy", "limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return 3 results (top scored)
        assert data["total_results"] == 3
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_search_invalid_search_type(self, client: AsyncClient, mock_db_connection):
        """Test search with invalid search type."""

        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "invalid", "limit": 10},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client: AsyncClient, mock_db_connection):
        """Test search with missing query."""

        response = await client.post(
            "/api/search",
            json={"search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: AsyncClient, mock_db_connection):
        """Test search with empty query."""

        response = await client.post(
            "/api/search",
            json={"query": "", "search_type": "fuzzy", "limit": 10},
        )

        assert response.status_code == 422  # Validation error (min_length=1)

    @pytest.mark.asyncio
    async def test_search_default_search_type(self, client: AsyncClient, mock_db_connection):
        """Test search with default search type (semantic)."""

        response = await client.post(
            "/api/search",
            json={"query": "test", "limit": 10},
        )

        # Semantic search not yet implemented
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_semantic_not_implemented(self, client: AsyncClient, mock_db_connection):
        """Test that semantic search returns 501."""

        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "semantic", "limit": 10},
        )

        assert response.status_code == 501
        assert "Semantic search not yet implemented" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_limit_validation(self, client: AsyncClient, mock_db_connection):
        """Test search limit validation."""

        # Limit too large
        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "fuzzy", "limit": 101},
        )
        assert response.status_code == 422

        # Limit too small
        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "fuzzy", "limit": 0},
        )
        assert response.status_code == 422
