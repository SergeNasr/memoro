"""Tests for interaction endpoints."""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from backend.app.models import ExtractedContact, ExtractedFamilyMember, ExtractedInteraction
from backend.tests.conftest import make_openai_completion


class TestAnalyzeInteraction:
    """Tests for POST /api/interactions/analyze endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_interaction_success(self, client: AsyncClient, mock_openai_client):
        """Test successful interaction analysis."""
        mock_completion = make_openai_completion(
            contact=ExtractedContact(
                first_name="Sarah",
                last_name="Johnson",
                birthday=date(1985, 3, 15),
                confidence=0.95,
            ),
            interaction=ExtractedInteraction(
                notes="Had coffee together at Starbucks",
                location="Starbucks",
                interaction_date=date(2025, 10, 2),
                confidence=0.9,
            ),
            family_members=[
                ExtractedFamilyMember(
                    first_name="Emma",
                    last_name=None,
                    relationship="child",
                    confidence=0.85,
                )
            ],
        )

        mock_openai_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

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
    async def test_analyze_interaction_api_error(self, client: AsyncClient, mock_openai_client):
        """Test handling of OpenAI API errors."""
        mock_openai_client.beta.chat.completions.parse = AsyncMock(
            side_effect=Exception("OpenAI API error")
        )

        with pytest.raises(Exception, match="OpenAI API error"):
            await client.post(
                "/api/interactions/analyze",
                json={"text": "Test interaction text"},
            )


class TestConfirmInteraction:
    """Tests for POST /api/interactions/confirm endpoint."""

    @pytest.mark.asyncio
    async def test_confirm_interaction_success(self, client: AsyncClient, mock_db_transaction):
        """Test successful confirmation and persistence of interaction."""
        contact_id = uuid4()
        interaction_id = uuid4()

        # Configure mock to return different values for different queries
        def mock_fetchrow_side_effect(*args, **kwargs):
            # First call: find/create contact
            if "contact" in str(args[0]).lower() or "first_name" in str(args[0]).lower():
                return mock_db_transaction.make_record(
                    id=contact_id,
                    first_name="Sarah",
                    last_name="Johnson",
                    birthday=None,
                    latest_news="Test interaction",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )
            # Second call: create interaction
            elif "interaction" in str(args[0]).lower():
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 2),
                    notes="Had coffee together",
                    location="Starbucks",
                    created_at=None,
                    updated_at=None,
                )
            # Family member calls
            else:
                return mock_db_transaction.make_record(
                    id=uuid4(),
                    first_name="Emma",
                    last_name="Johnson",
                    birthday=None,
                    latest_news="Family member",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow_side_effect

        response = await client.post(
            "/api/interactions/confirm",
            json={
                "contact": {
                    "first_name": "Sarah",
                    "last_name": "Johnson",
                    "birthday": "1985-03-15",
                    "confidence": 0.95,
                },
                "interaction": {
                    "notes": "Had coffee together, discussed daughter starting college",
                    "location": "Starbucks",
                    "interaction_date": "2025-10-02",
                    "confidence": 0.9,
                },
                "family_members": [
                    {
                        "first_name": "Emma",
                        "last_name": "Johnson",
                        "relationship": "child",
                        "confidence": 0.85,
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "contact_id" in data
        assert "interaction_id" in data
        assert "family_members_linked" in data
        assert data["family_members_linked"] == 1

    @pytest.mark.asyncio
    async def test_confirm_interaction_no_family_members(
        self, client: AsyncClient, mock_db_transaction
    ):
        """Test confirmation without family members."""
        contact_id = uuid4()
        interaction_id = uuid4()

        def mock_fetchrow_side_effect(*args, **kwargs):
            if "interaction" in str(args[0]).lower() and "INSERT" in str(args[0]):
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 2),
                    notes="Quick chat",
                    location=None,
                    created_at=None,
                    updated_at=None,
                )
            else:
                return mock_db_transaction.make_record(
                    id=contact_id,
                    first_name="John",
                    last_name="Doe",
                    birthday=None,
                    latest_news="Quick chat",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow_side_effect

        response = await client.post(
            "/api/interactions/confirm",
            json={
                "contact": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "birthday": None,
                    "confidence": 0.9,
                },
                "interaction": {
                    "notes": "Quick chat",
                    "location": None,
                    "interaction_date": "2025-10-02",
                    "confidence": 0.8,
                },
                "family_members": [],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["family_members_linked"] == 0

    @pytest.mark.asyncio
    async def test_confirm_interaction_validation_error(
        self, client: AsyncClient, mock_db_transaction
    ):
        """Test validation error for invalid request."""
        response = await client.post(
            "/api/interactions/confirm",
            json={
                "contact": {"first_name": "John", "confidence": 0.9},
                # Missing required fields
            },
        )
        assert response.status_code == 422  # Validation error


class TestGetInteraction:
    """Tests for GET /api/interactions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_interaction_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction retrieval."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock fetchrow
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Met for coffee and caught up",
            location="Starbucks Downtown",
        )

        response = await client.get(f"/api/interactions/{interaction_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(interaction_id)
        assert data["contact_id"] == str(contact_id)
        assert data["notes"] == "Met for coffee and caught up"
        assert data["location"] == "Starbucks Downtown"
        assert data["interaction_date"] == "2024-01-15"

    @pytest.mark.asyncio
    async def test_get_interaction_not_found(self, client: AsyncClient, mock_db_connection):
        """Test interaction not found (404)."""

        interaction_id = uuid4()

        # Mock fetchrow returns None (interaction not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/api/interactions/{interaction_id}")

        assert response.status_code == 404
        assert "Interaction not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_interaction_invalid_uuid(self, client: AsyncClient, mock_db_connection):
        """Test invalid UUID format."""
        response = await client.get("/api/interactions/not-a-uuid")
        assert response.status_code == 422  # Validation error


class TestUpdateInteraction:
    """Tests for PATCH /api/interactions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_interaction_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction update."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock fetchrow (update returns updated row)
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2025, 10, 3),  # Updated date
            notes="Updated notes about coffee",  # Updated notes
            location="Updated Starbucks",  # Updated location
        )

        response = await client.patch(
            f"/api/interactions/{interaction_id}",
            json={
                "notes": "Updated notes about coffee",
                "location": "Updated Starbucks",
                "interaction_date": "2025-10-03",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(interaction_id)
        assert data["contact_id"] == str(contact_id)
        assert data["notes"] == "Updated notes about coffee"
        assert data["location"] == "Updated Starbucks"
        assert data["interaction_date"] == "2025-10-03"

    @pytest.mark.asyncio
    async def test_update_interaction_not_found(self, client: AsyncClient, mock_db_connection):
        """Test updating non-existent interaction."""

        interaction_id = uuid4()

        # Mock fetchrow returns None (interaction not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.patch(
            f"/api/interactions/{interaction_id}", json={"notes": "Updated"}
        )

        assert response.status_code == 404
        assert "Interaction not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_interaction_partial(self, client: AsyncClient, mock_db_connection):
        """Test partial update (only some fields)."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock fetchrow - only notes updated
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2025, 10, 2),  # Unchanged
            notes="Updated notes only",  # Updated
            location="Starbucks",  # Unchanged
        )

        response = await client.patch(
            f"/api/interactions/{interaction_id}", json={"notes": "Updated notes only"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["notes"] == "Updated notes only"
        assert data["location"] == "Starbucks"
        assert data["interaction_date"] == "2025-10-02"

    @pytest.mark.asyncio
    async def test_update_interaction_empty_body(self, client: AsyncClient, mock_db_connection):
        """Test update with empty body (no fields to update)."""

        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock fetchrow - nothing changed
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2025, 10, 2),
            notes="Original notes",
            location="Starbucks",
        )

        response = await client.patch(f"/api/interactions/{interaction_id}", json={})

        assert response.status_code == 200


class TestDeleteInteraction:
    """Tests for DELETE /api/interactions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_interaction_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction deletion."""

        interaction_id = uuid4()

        # Mock fetchrow (delete returns deleted row id)
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(id=interaction_id)

        response = await client.delete(f"/api/interactions/{interaction_id}")

        assert response.status_code == 204
        assert response.content == b""  # No content for 204

    @pytest.mark.asyncio
    async def test_delete_interaction_not_found(self, client: AsyncClient, mock_db_connection):
        """Test deleting non-existent interaction."""

        interaction_id = uuid4()

        # Mock fetchrow returns None (interaction not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.delete(f"/api/interactions/{interaction_id}")

        assert response.status_code == 404
        assert "Interaction not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_interaction_invalid_uuid(self, client: AsyncClient, mock_db_connection):
        """Test deleting with invalid UUID."""
        response = await client.delete("/api/interactions/not-a-uuid")
        assert response.status_code == 422  # Validation error


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
