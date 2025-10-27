"""Tests for search endpoints."""

from datetime import date
from unittest.mock import AsyncMock
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
            contact_first_name="Alice",
            contact_last_name="Smith",
            score=0.8,
        )

        # Mock fetch to return different scores for each search type
        # Since asyncio.gather runs in parallel, we need to return results in order
        fuzzy_result = dict(mock_interaction, score=0.7)
        term_result = dict(mock_interaction, score=1.0)
        semantic_result = dict(mock_interaction, score=0.9)

        mock_db_connection.fetch.side_effect = [
            [fuzzy_result],  # First call: fuzzy
            [term_result],  # Second call: term
            [semantic_result],  # Third call: semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "coffee meeting", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["search_type"] == "hybrid"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1

        result = data["results"][0]
        assert result["result_type"] == "interaction"
        assert result["interaction"]["notes"] == "Coffee meeting to discuss project"

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
            contact_first_name="Bob",
            contact_last_name="Jones",
            score=0.8,
        )

        # All three searches return the same interaction
        mock_db_connection.fetch.side_effect = [
            [mock_interaction],  # Fuzzy
            [mock_interaction],  # Term
            [mock_interaction],  # Semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "meeting", "search_type": "hybrid", "limit": 10},
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
        contact_id = uuid4()

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Different interactions from each search type
        fuzzy_interaction = mock_db_connection.make_record(
            id=interaction1_id,
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Fuzzy match interaction",
            location="Park",
            contact_first_name="Alice",
            contact_last_name="Smith",
            score=0.9,
        )

        term_interaction = mock_db_connection.make_record(
            id=interaction2_id,
            contact_id=contact_id,
            interaction_date=date(2024, 1, 16),
            notes="Term match interaction",
            location="Cafe",
            contact_first_name="Bob",
            contact_last_name="Jones",
            score=1.0,
        )

        semantic_interaction = mock_db_connection.make_record(
            id=interaction3_id,
            contact_id=contact_id,
            interaction_date=date(2024, 1, 17),
            notes="Semantic match interaction",
            location="Office",
            contact_first_name="Carol",
            contact_last_name="White",
            score=0.95,
        )

        mock_db_connection.fetch.side_effect = [
            [fuzzy_interaction],  # Fuzzy
            [term_interaction],  # Term
            [semantic_interaction],  # Semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test query", "search_type": "hybrid", "limit": 10},
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
        contact_id = uuid4()

        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        mock_embedding_response = AsyncMock()
        mock_embedding_response.data = [AsyncMock(embedding=mock_embedding)]
        mock_embedding_response.usage = AsyncMock(total_tokens=10)
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        # Create 5 different interactions
        interactions = [
            mock_db_connection.make_record(
                id=uuid4(),
                contact_id=contact_id,
                interaction_date=date(2024, 1, i + 1),
                notes=f"Interaction {i}",
                location="Location",
                contact_first_name="User",
                contact_last_name="Name",
                score=0.9 - (i * 0.1),
            )
            for i in range(5)
        ]

        mock_db_connection.fetch.side_effect = [
            interactions[:3],  # Fuzzy
            interactions[2:],  # Term
            interactions[1:4],  # Semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "test", "search_type": "hybrid", "limit": 3},
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
            [],  # Fuzzy
            [],  # Term
            [],  # Semantic
        ]

        response = await client.post(
            "/api/search",
            json={"query": "nonexistent", "search_type": "hybrid", "limit": 10},
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

        mock_db_connection.fetch.side_effect = [[], [], []]

        response = await client.post(
            "/api/search",
            json={"query": "test query for embedding", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200

        # Verify embedding was generated
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test query for embedding",
        )
