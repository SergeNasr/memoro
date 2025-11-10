"""Tests for search endpoints."""

from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestSearch:
    """Tests for POST /api/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_empty_results(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test search with no results."""
        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Mock empty results (5 fetches for hybrid: contact_fuzzy, interaction_fuzzy, contact_term, interaction_term, interaction_semantic)
        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [],  # interaction_fuzzy
            [],  # contact_term
            [],  # interaction_term
            [],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "nonexistent", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_limit_applied(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that search limit is properly applied."""
        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Create 5 unique contacts/interactions
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

        interactions = [
            mock_db_connection.make_record(
                contact_id=uuid4(),
                first_name=f"Test{i}",
                last_name="User",
                birthday=None,
                latest_news=None,
                score=0.8 - (i * 0.1),
            )
            for i in range(5)
        ]

        # Mock hybrid search (5 fetches: contact_fuzzy, interaction_fuzzy, contact_term, interaction_term, interaction_semantic)
        mock_db_connection.fetch.side_effect = [
            contacts[:3],  # contact_fuzzy
            interactions[:2],  # interaction_fuzzy
            contacts[1:4],  # contact_term
            interactions[2:],  # interaction_term
            interactions[:4],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test", "limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return 3 results (top scored)
        assert data["total_results"] == 3
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client: AsyncClient, mock_db_connection):
        """Test search with missing query."""

        response = await client.post(
            "/api/search",
            json={"limit": 10},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: AsyncClient, mock_db_connection):
        """Test search with empty query."""

        response = await client.post(
            "/api/search",
            json={"query": "", "limit": 10},
        )

        assert response.status_code == 422  # Validation error (min_length=1)

    @pytest.mark.asyncio
    async def test_search_limit_validation(self, client: AsyncClient, mock_db_connection):
        """Test search limit validation."""

        # Limit too large
        response = await client.post(
            "/api/search",
            json={"query": "test", "limit": 101},
        )
        assert response.status_code == 422

        # Limit too small
        response = await client.post(
            "/api/search",
            json={"query": "test", "limit": 0},
        )
        assert response.status_code == 422


class TestHybridSearch:
    """Tests for hybrid search functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_all_types(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that hybrid search combines fuzzy, term, and semantic results."""
        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Mock all three search types returning the same interaction with different scores
        mock_interaction = mock_db_connection.make_record(
            id=interaction_id,
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Coffee meeting to discuss project",
            location="Starbucks",
            first_name="Alice",
            last_name="Smith",
            birthday=None,
            latest_news=None,
            score=0.8,
        )

        # Mock fetch to return different scores for each search type
        # Order: contact_fuzzy, interaction_fuzzy, contact_term, interaction_term, interaction_semantic
        fuzzy_result = dict(mock_interaction, score=0.7)
        term_result = dict(mock_interaction, score=1.0)
        semantic_result = dict(mock_interaction, score=0.9)

        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [fuzzy_result],  # interaction_fuzzy
            [],  # contact_term
            [term_result],  # interaction_term
            [semantic_result],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "coffee meeting", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["results"]) == 1

        result = data["results"][0]

        # Weighted score: 0.9*0.5 + 0.7*0.3 + 1.0*0.2 = 0.45 + 0.21 + 0.2 = 0.86
        assert abs(result["score"] - 0.86) < 0.01

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplicates_results(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that hybrid search properly deduplicates same interaction across search types."""
        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        mock_interaction = mock_db_connection.make_record(
            id=interaction_id,
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Important meeting",
            location="Office",
            first_name="Bob",
            last_name="Jones",
            birthday=None,
            latest_news=None,
            score=0.8,
        )

        # All searches return the same interaction (deduplicated by contact_id)
        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [mock_interaction],  # interaction_fuzzy
            [],  # contact_term
            [mock_interaction],  # interaction_term
            [mock_interaction],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "meeting", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return one result despite appearing in all three searches
        assert data["total_results"] == 1
        assert len(data["results"]) == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_merges_different_interactions(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that hybrid search merges different interactions from different search types."""
        interaction1_id = uuid4()
        interaction2_id = uuid4()
        interaction3_id = uuid4()
        contact1_id = uuid4()
        contact2_id = uuid4()
        contact3_id = uuid4()

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Different interactions from each search type (different contacts)
        fuzzy_interaction = mock_db_connection.make_record(
            id=interaction1_id,
            contact_id=contact1_id,
            interaction_date=date(2024, 1, 15),
            notes="Fuzzy match interaction",
            location="Park",
            first_name="Alice",
            last_name="Smith",
            birthday=None,
            latest_news=None,
            score=0.9,
        )

        term_interaction = mock_db_connection.make_record(
            id=interaction2_id,
            contact_id=contact2_id,
            interaction_date=date(2024, 1, 16),
            notes="Term match interaction",
            location="Cafe",
            first_name="Bob",
            last_name="Jones",
            birthday=None,
            latest_news=None,
            score=1.0,
        )

        semantic_interaction = mock_db_connection.make_record(
            id=interaction3_id,
            contact_id=contact3_id,
            interaction_date=date(2024, 1, 17),
            notes="Semantic match interaction",
            location="Office",
            first_name="Carol",
            last_name="White",
            birthday=None,
            latest_news=None,
            score=0.95,
        )

        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [fuzzy_interaction],  # interaction_fuzzy
            [],  # contact_term
            [term_interaction],  # interaction_term
            [semantic_interaction],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test query", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return all three unique interactions
        assert data["total_results"] == 3
        assert len(data["results"]) == 3

        # Results should be sorted by weighted score (descending)
        # Semantic: 0.95*0.5 = 0.475
        # Fuzzy: 0.9*0.3 = 0.27
        # Term: 1.0*0.2 = 0.2
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_limit(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that hybrid search respects the result limit."""
        # Create 5 different interactions with different contact_ids
        interactions = [
            mock_db_connection.make_record(
                id=uuid4(),
                contact_id=uuid4(),
                interaction_date=date(2024, 1, i + 1),
                notes=f"Interaction {i}",
                location="Location",
                first_name=f"User{i}",
                last_name="Name",
                birthday=None,
                latest_news=None,
                score=0.9 - (i * 0.1),
            )
            for i in range(5)
        ]

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            interactions[:3],  # interaction_fuzzy
            [],  # contact_term
            interactions[2:],  # interaction_term
            interactions[1:4],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test", "limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return 3 results despite more being available
        assert data["total_results"] == 3
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_results(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test hybrid search with no results."""
        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # All searches return empty
        mock_db_connection.fetch.side_effect = [
            [],  # contact_fuzzy
            [],  # interaction_fuzzy
            [],  # contact_term
            [],  # interaction_term
            [],  # interaction_semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "nonexistent", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_generates_embedding(
        self, client: AsyncClient, mock_db_connection, mock_openai_client
    ):
        """Test that hybrid search calls embedding generation."""
        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        mock_db_connection.fetch.side_effect = [[], [], [], [], []]

        response = await client.post(
            "/api/search",
            json={"query": "test query for embedding", "limit": 10},
        )

        assert response.status_code == 200

        # Verify embedding was generated
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test query for embedding",
        )
