"""Tests for interaction API endpoints."""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from httpx import AsyncClient

from backend.app.models import ExtractedContact, ExtractedInteraction, ExtractedRelationship
from backend.tests.conftest import make_openai_completion


class TestAnalyze:
    """Interaction analysis via LLM."""

    async def test_analyze(self, client: AsyncClient, mock_openai_client):
        """Analyze interaction text extracts contact and interaction."""
        mock_completion = make_openai_completion(
            contact=ExtractedContact(
                first_name="Sarah", last_name="Johnson", birthday=date(1985, 3, 15), confidence=0.95
            ),
            interaction=ExtractedInteraction(
                notes="Coffee at Starbucks",
                location="Starbucks",
                interaction_date=date(2025, 10, 2),
                confidence=0.9,
            ),
            relationships=[
                ExtractedRelationship(
                    first_name="Emma", last_name=None, relationship="child", confidence=0.85
                )
            ],
        )
        mock_openai_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        response = await client.post(
            "/api/interactions/analyze", json={"text": "Had coffee with Sarah Johnson"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["first_name"] == "Sarah"
        assert data["interaction"]["location"] == "Starbucks"
        assert len(data["relationships"]) == 1

    async def test_analyze_empty_text(self, client: AsyncClient):
        """Empty text returns validation error."""
        response = await client.post("/api/interactions/analyze", json={"text": ""})
        assert response.status_code == 422


class TestConfirm:
    """Interaction confirmation and persistence."""

    async def test_confirm(self, client: AsyncClient, mock_db_transaction, mock_openai_client):
        """Confirm creates contact and interaction."""
        contact_id, interaction_id = uuid4(), uuid4()

        def mock_fetchrow(*args, **kwargs):
            query = str(args[0]).lower()
            if "interaction" in query and "insert" in query:
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 2),
                    notes="Coffee",
                    location="Starbucks",
                    created_at=None,
                    updated_at=None,
                )
            return mock_db_transaction.make_record(
                id=contact_id,
                first_name="Sarah",
                last_name="Johnson",
                birthday=None,
                latest_news="Coffee",
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
            )

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow

        response = await client.post(
            "/api/interactions/confirm",
            json={
                "contact": {
                    "first_name": "Sarah",
                    "last_name": "Johnson",
                    "birthday": None,
                    "confidence": 0.95,
                },
                "interaction": {
                    "notes": "Coffee",
                    "location": "Starbucks",
                    "interaction_date": "2025-10-02",
                    "confidence": 0.9,
                },
                "relationships": [],
            },
        )
        assert response.status_code == 201
        assert "contact_id" in response.json()
        assert "interaction_id" in response.json()


class TestInteractionsCRUD:
    """Interaction CRUD operations."""

    async def test_get(self, client: AsyncClient, mock_db_connection):
        """Get single interaction."""
        interaction_id, contact_id = uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Coffee meeting",
            location="Starbucks",
        )

        response = await client.get(f"/api/interactions/{interaction_id}")
        assert response.status_code == 200
        assert response.json()["notes"] == "Coffee meeting"

    async def test_get_not_found(self, client: AsyncClient, mock_db_connection):
        """Get non-existent interaction returns 404."""
        mock_db_connection.fetchrow.return_value = None
        response = await client.get(f"/api/interactions/{uuid4()}")
        assert response.status_code == 404

    async def test_update(self, client: AsyncClient, mock_db_connection, mock_openai_client):
        """Update interaction regenerates embedding."""
        interaction_id, contact_id = uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2025, 10, 3),
            notes="Updated notes",
            location="New place",
        )

        response = await client.patch(
            f"/api/interactions/{interaction_id}",
            json={"notes": "Updated notes", "location": "New place"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"
        mock_openai_client.embeddings.create.assert_called()

    async def test_delete(self, client: AsyncClient, mock_db_connection):
        """Delete interaction."""
        interaction_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(id=interaction_id)

        response = await client.delete(f"/api/interactions/{interaction_id}")
        assert response.status_code == 204


class TestHealthCheck:
    """Health check endpoint."""

    async def test_health(self, client: AsyncClient):
        """Health check returns healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
