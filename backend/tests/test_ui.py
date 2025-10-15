"""Tests for UI endpoints."""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from backend.app.models import ExtractedContact, ExtractedInteraction
from backend.tests.conftest import make_openai_completion


class TestAnalyzeInteractionUI:
    """Tests for POST /ui/interactions/analyze endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_interaction_ui_success(
        self, client: AsyncClient, mock_openai_client, mock_db_connection
    ):
        """Test successful interaction analysis via UI."""
        mock_completion = make_openai_completion(
            contact=ExtractedContact(
                first_name="Sarah",
                last_name="Johnson",
                birthday=None,
                confidence=0.95,
            ),
            interaction=ExtractedInteraction(
                notes="Had coffee together at Starbucks",
                location="Starbucks",
                interaction_date=date(2025, 10, 15),
                confidence=0.9,
            ),
            family_members=[],
        )

        mock_openai_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        response = await client.post(
            "/ui/interactions/analyze",
            data={
                "text": "Had coffee with Sarah at Starbucks today.",
            },
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Sarah" in response.content
        assert b"Starbucks" in response.content

    @pytest.mark.asyncio
    async def test_analyze_interaction_ui_with_contact_context(
        self, client: AsyncClient, mock_openai_client, mock_db_connection
    ):
        """Test interaction analysis with pre-filled contact info."""
        contact_id = uuid4()

        # Mock contact lookup
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Sarah",
            last_name="Johnson",
            birthday=date(1990, 5, 15),
            latest_news="Recent update",
        )

        mock_completion = make_openai_completion(
            contact=ExtractedContact(
                first_name="Unknown",
                last_name="Person",
                birthday=None,
                confidence=0.5,
            ),
            interaction=ExtractedInteraction(
                notes="Had coffee at Starbucks",
                location="Starbucks",
                interaction_date=date(2025, 10, 15),
                confidence=0.9,
            ),
            family_members=[],
        )

        mock_openai_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        response = await client.post(
            "/ui/interactions/analyze",
            data={
                "text": "Had coffee at Starbucks today.",
                "contact_id": str(contact_id),
            },
        )

        assert response.status_code == 200
        # Should show Sarah (from DB) not Unknown (from LLM)
        assert b"Sarah" in response.content
        assert b"Johnson" in response.content

    @pytest.mark.asyncio
    async def test_analyze_interaction_ui_missing_text(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test validation error for missing text field."""
        response = await client.post(
            "/ui/interactions/analyze",
            data={},
        )

        assert response.status_code == 422


class TestGetInteractionFragment:
    """Tests for GET /ui/interactions/{interaction_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_interaction_fragment_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction fragment retrieval."""
        interaction_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Met for coffee",
            location="Starbucks",
        )

        response = await client.get(f"/ui/interactions/{interaction_id}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Met for coffee" in response.content
        assert b"Starbucks" in response.content
        assert b"[edit]" in response.content
        assert b"[delete]" in response.content

    @pytest.mark.asyncio
    async def test_get_interaction_fragment_not_found(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test interaction fragment not found."""
        interaction_id = uuid4()

        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/ui/interactions/{interaction_id}")

        assert response.status_code == 404
        assert b"Interaction not found" in response.content


class TestGetInteractionEditForm:
    """Tests for GET /ui/interactions/{interaction_id}/edit endpoint."""

    @pytest.mark.asyncio
    async def test_get_interaction_edit_form_success(self, client: AsyncClient, mock_db_connection):
        """Test successful edit form retrieval."""
        interaction_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Met for coffee",
            location="Starbucks",
        )

        response = await client.get(f"/ui/interactions/{interaction_id}/edit")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Met for coffee" in response.content
        assert b"Starbucks" in response.content
        assert b"Save" in response.content
        assert b"Cancel" in response.content

    @pytest.mark.asyncio
    async def test_get_interaction_edit_form_not_found(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test edit form for non-existent interaction."""
        interaction_id = uuid4()

        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/ui/interactions/{interaction_id}/edit")

        assert response.status_code == 404
        assert b"Interaction not found" in response.content


class TestUpdateInteractionUI:
    """Tests for PATCH /ui/interactions/{interaction_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_interaction_ui_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction update via UI."""
        interaction_id = uuid4()
        contact_id = uuid4()

        # Mock update returns updated interaction
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2025, 10, 16),
            notes="Updated notes",
            location="New Location",
        )

        response = await client.patch(
            f"/ui/interactions/{interaction_id}",
            data={
                "interaction_date": "2025-10-16",
                "notes": "Updated notes",
                "location": "New Location",
            },
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Updated notes" in response.content
        assert b"New Location" in response.content

    @pytest.mark.asyncio
    async def test_update_interaction_ui_not_found(self, client: AsyncClient, mock_db_connection):
        """Test updating non-existent interaction."""
        interaction_id = uuid4()

        mock_db_connection.fetchrow.return_value = None

        response = await client.patch(
            f"/ui/interactions/{interaction_id}",
            data={
                "interaction_date": "2025-10-16",
                "notes": "Updated notes",
                "location": "",
            },
        )

        assert response.status_code == 404
        assert b"Interaction not found" in response.content

    @pytest.mark.asyncio
    async def test_update_interaction_ui_partial(self, client: AsyncClient, mock_db_connection):
        """Test partial update via UI."""
        interaction_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Just notes updated",
            location="Original Location",
        )

        response = await client.patch(
            f"/ui/interactions/{interaction_id}",
            data={
                "interaction_date": "2024-01-15",
                "notes": "Just notes updated",
                "location": "Original Location",
            },
        )

        assert response.status_code == 200
        assert b"Just notes updated" in response.content


class TestDeleteInteractionUI:
    """Tests for DELETE /ui/interactions/{interaction_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_interaction_ui_success(self, client: AsyncClient, mock_db_connection):
        """Test successful interaction deletion via UI."""
        interaction_id = uuid4()
        contact_id = uuid4()

        # First fetchrow: get interaction to find contact_id
        # Second fetchrow: delete interaction
        # Then fetchrow for contact summary
        # Then fetch calls for summary data

        mock_db_connection.fetchrow.side_effect = [
            # Get interaction
            mock_db_connection.make_record(
                id=interaction_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                contact_id=contact_id,
                interaction_date=date(2024, 1, 15),
                notes="To be deleted",
                location="Starbucks",
            ),
            # Delete interaction
            mock_db_connection.make_record(id=interaction_id),
            # Get contact for summary
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Sarah",
                last_name="Johnson",
                birthday=None,
                latest_news="News",
            ),
            # Interaction count
            mock_db_connection.make_record(total=1),
            # Last interaction date
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 10)),
        ]

        mock_db_connection.fetch.side_effect = [
            # Recent interactions
            [
                mock_db_connection.make_record(
                    id=uuid4(),
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 10),
                    notes="Remaining interaction",
                    location="Coffee shop",
                )
            ],
            # Family members
            [],
        ]

        response = await client.delete(f"/ui/interactions/{interaction_id}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Remaining interaction" in response.content
        assert b"To be deleted" not in response.content

    @pytest.mark.asyncio
    async def test_delete_interaction_ui_not_found(self, client: AsyncClient, mock_db_connection):
        """Test deleting non-existent interaction."""
        interaction_id = uuid4()

        mock_db_connection.fetchrow.return_value = None

        response = await client.delete(f"/ui/interactions/{interaction_id}")

        assert response.status_code == 404
        assert b"Interaction not found" in response.content

    @pytest.mark.asyncio
    async def test_delete_interaction_ui_delete_fails(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test when deletion operation fails."""
        interaction_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.side_effect = [
            # Get interaction
            mock_db_connection.make_record(
                id=interaction_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                contact_id=contact_id,
                interaction_date=date(2024, 1, 15),
                notes="To be deleted",
                location="Starbucks",
            ),
            # Delete fails (returns None)
            None,
        ]

        response = await client.delete(f"/ui/interactions/{interaction_id}")

        assert response.status_code == 500
        assert b"Failed to delete" in response.content


class TestConfirmInteractionUI:
    """Tests for POST /ui/interactions/confirm endpoint."""

    @pytest.mark.asyncio
    async def test_confirm_interaction_ui_success(self, client: AsyncClient, mock_db_transaction):
        """Test successful confirmation and redirect via UI."""
        contact_id = uuid4()
        interaction_id = uuid4()

        def mock_fetchrow_side_effect(*args, **kwargs):
            if "contact" in str(args[0]).lower() or "first_name" in str(args[0]).lower():
                return mock_db_transaction.make_record(
                    id=contact_id,
                    first_name="Sarah",
                    last_name="Johnson",
                    birthday=None,
                    latest_news="Test interaction",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )
            elif "interaction" in str(args[0]).lower():
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 15),
                    notes="Had coffee together",
                    location="Starbucks",
                    created_at=None,
                    updated_at=None,
                )
            else:
                return None

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow_side_effect

        response = await client.post(
            "/ui/interactions/confirm",
            data={
                "contact.first_name": "Sarah",
                "contact.last_name": "Johnson",
                "interaction.interaction_date": "2025-10-15",
                "interaction.notes": "Had coffee together",
                "interaction.location": "Starbucks",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/contacts/{contact_id}"

    @pytest.mark.asyncio
    async def test_confirm_interaction_ui_with_family(
        self, client: AsyncClient, mock_db_transaction
    ):
        """Test confirmation with family members via UI."""
        contact_id = uuid4()
        interaction_id = uuid4()
        family_id = uuid4()

        def mock_fetchrow_side_effect(*args, **kwargs):
            query = str(args[0]).lower()
            if "interaction" in query and "insert" in query:
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 15),
                    notes="Met family",
                    location="Park",
                    created_at=None,
                    updated_at=None,
                )
            elif "family" in query or "spouse" in str(args):
                return mock_db_transaction.make_record(
                    id=family_id,
                    first_name="Emma",
                    last_name="Johnson",
                    birthday=None,
                    latest_news="Family",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )
            else:
                return mock_db_transaction.make_record(
                    id=contact_id,
                    first_name="Sarah",
                    last_name="Johnson",
                    birthday=None,
                    latest_news="Met family",
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                )

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow_side_effect

        response = await client.post(
            "/ui/interactions/confirm",
            data={
                "contact.first_name": "Sarah",
                "contact.last_name": "Johnson",
                "interaction.interaction_date": "2025-10-15",
                "interaction.notes": "Met family",
                "interaction.location": "Park",
                "family_members[0].first_name": "Emma",
                "family_members[0].last_name": "Johnson",
                "family_members[0].relationship": "child",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/contacts/{contact_id}"
