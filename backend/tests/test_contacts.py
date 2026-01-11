"""Tests for contact API endpoints."""

from datetime import date
from uuid import UUID, uuid4

from httpx import AsyncClient


class TestContactsCRUD:
    """Contact CRUD operations."""

    async def test_list(self, client: AsyncClient, mock_db_connection):
        """List contacts with pagination."""
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(total=2)
        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(),
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alice",
                last_name="Anderson",
                birthday=date(1990, 1, 1),
                latest_news=None,
            ),
            mock_db_connection.make_record(
                id=uuid4(),
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Bob",
                last_name="Brown",
                birthday=None,
                latest_news=None,
            ),
        ]

        response = await client.get("/api/contacts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["contacts"]) == 2
        assert data["contacts"][0]["first_name"] == "Alice"

    async def test_list_empty(self, client: AsyncClient, mock_db_connection):
        """List contacts when empty."""
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(total=0)
        mock_db_connection.fetch.return_value = []

        response = await client.get("/api/contacts")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_get(self, client: AsyncClient, mock_db_connection):
        """Get single contact."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Anderson",
            birthday=date(1990, 1, 1),
            latest_news="News",
        )

        response = await client.get(f"/api/contacts/{contact_id}")
        assert response.status_code == 200
        assert response.json()["first_name"] == "Alice"

    async def test_get_not_found(self, client: AsyncClient, mock_db_connection):
        """Get non-existent contact returns 404."""
        mock_db_connection.fetchrow.return_value = None
        response = await client.get(f"/api/contacts/{uuid4()}")
        assert response.status_code == 404

    async def test_update(self, client: AsyncClient, mock_db_connection):
        """Update contact."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Smith",
            birthday=date(1990, 1, 1),
            latest_news="Updated",
        )

        response = await client.patch(
            f"/api/contacts/{contact_id}", json={"last_name": "Smith", "latest_news": "Updated"}
        )
        assert response.status_code == 200
        assert response.json()["last_name"] == "Smith"

    async def test_delete(self, client: AsyncClient, mock_db_connection):
        """Delete contact."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(id=contact_id)

        response = await client.delete(f"/api/contacts/{contact_id}")
        assert response.status_code == 204

    async def test_delete_not_found(self, client: AsyncClient, mock_db_connection):
        """Delete non-existent contact returns 404."""
        mock_db_connection.fetchrow.return_value = None
        response = await client.delete(f"/api/contacts/{uuid4()}")
        assert response.status_code == 404


class TestContactInteractions:
    """Contact interactions listing."""

    async def test_list_interactions(self, client: AsyncClient, mock_db_connection):
        """List contact's interactions."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Anderson",
            birthday=None,
            latest_news=None,
        )
        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(),
                contact_id=contact_id,
                interaction_date=date(2024, 1, 15),
                notes="Coffee",
                location="Starbucks",
            ),
        ]

        response = await client.get(f"/api/contacts/{contact_id}/interactions")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["notes"] == "Coffee"


class TestContactSummary:
    """Contact summary endpoint."""

    async def test_summary(self, client: AsyncClient, mock_db_connection):
        """Get contact summary with stats."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alice",
                last_name="Anderson",
                birthday=date(1990, 1, 1),
                latest_news="News",
            ),
            mock_db_connection.make_record(total=5),
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 15)),
        ]
        mock_db_connection.fetch.side_effect = [[], []]  # interactions, relationships

        response = await client.get(f"/api/contacts/{contact_id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["first_name"] == "Alice"
        assert data["total_interactions"] == 5
