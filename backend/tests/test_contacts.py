"""Tests for contact endpoints."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


class TestListContacts:
    """Tests for GET /api/contacts endpoint."""

    @pytest.mark.asyncio
    async def test_list_contacts_success(self, client: AsyncClient, mock_db_connection):
        """Test successful contact list retrieval."""

        # Mock count query
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(total=2)

        # Mock list query
        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(),
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alice",
                last_name="Anderson",
                birthday=date(1990, 1, 1),
                latest_news="Recent update about Alice",
            ),
            mock_db_connection.make_record(
                id=uuid4(),
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Bob",
                last_name="Brown",
                birthday=None,
                latest_news="Recent update about Bob",
            ),
        ]

        response = await client.get("/api/contacts")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination metadata
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 1

        # Verify contacts
        assert len(data["contacts"]) == 2
        assert data["contacts"][0]["first_name"] == "Alice"
        assert data["contacts"][1]["first_name"] == "Bob"

    @pytest.mark.asyncio
    async def test_list_contacts_empty(self, client: AsyncClient, mock_db_connection):
        """Test contact list when no contacts exist."""

        # Mock count query
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(total=0)

        # Mock list query
        mock_db_connection.fetch.return_value = []

        response = await client.get("/api/contacts")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0
        assert len(data["contacts"]) == 0

    @pytest.mark.asyncio
    async def test_list_contacts_pagination(self, client: AsyncClient, mock_db_connection):
        """Test contact list pagination parameters."""

        # Mock count query (50 total contacts)
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(total=50)

        # Mock list query (return 10 contacts for page 2)
        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(),
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name=f"User{i}",
                last_name=f"Name{i}",
                birthday=None,
                latest_news=None,
            )
            for i in range(10, 20)
        ]

        response = await client.get("/api/contacts?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 50
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_pages"] == 5
        assert len(data["contacts"]) == 10

    @pytest.mark.asyncio
    async def test_list_contacts_invalid_page(self, client: AsyncClient, mock_db_connection):
        """Test contact list with invalid page parameter."""
        response = await client.get("/api/contacts?page=0")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_list_contacts_invalid_page_size(self, client: AsyncClient, mock_db_connection):
        """Test contact list with invalid page_size parameter."""
        response = await client.get("/api/contacts?page_size=101")
        assert response.status_code == 422  # Validation error (max 100)

        response = await client.get("/api/contacts?page_size=0")
        assert response.status_code == 422  # Validation error (min 1)


class TestGetContact:
    """Tests for GET /api/contacts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_contact_success(self, client: AsyncClient, mock_db_connection):
        """Test successful contact retrieval."""

        contact_id = uuid4()

        # Mock fetchrow
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Anderson",
            birthday=date(1990, 1, 1),
            latest_news="Recent update about Alice",
        )

        response = await client.get(f"/api/contacts/{contact_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(contact_id)
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Anderson"
        assert data["birthday"] == "1990-01-01"
        assert data["latest_news"] == "Recent update about Alice"

    @pytest.mark.asyncio
    async def test_get_contact_not_found(self, client: AsyncClient, mock_db_connection):
        """Test contact not found (404)."""

        contact_id = uuid4()

        # Mock fetchrow returns None (contact not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/api/contacts/{contact_id}")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_contact_invalid_uuid(self, client: AsyncClient, mock_db_connection):
        """Test invalid UUID format."""
        response = await client.get("/api/contacts/not-a-uuid")
        assert response.status_code == 422  # Validation error


class TestUpdateContact:
    """Tests for PATCH /api/contacts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_contact_success(self, client: AsyncClient, mock_db_connection):
        """Test successful contact update."""

        contact_id = uuid4()

        # Mock fetchrow (update returns updated row)
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Smith",  # Updated last name
            birthday=date(1990, 1, 1),
            latest_news="Updated news",  # Updated news
        )

        response = await client.patch(
            f"/api/contacts/{contact_id}",
            json={"last_name": "Smith", "latest_news": "Updated news"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(contact_id)
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Smith"
        assert data["latest_news"] == "Updated news"

    @pytest.mark.asyncio
    async def test_update_contact_not_found(self, client: AsyncClient, mock_db_connection):
        """Test updating non-existent contact."""

        contact_id = uuid4()

        # Mock fetchrow returns None (contact not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.patch(f"/api/contacts/{contact_id}", json={"first_name": "Updated"})

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_contact_partial(self, client: AsyncClient, mock_db_connection):
        """Test partial update (only some fields)."""

        contact_id = uuid4()

        # Mock fetchrow - only first_name updated
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alicia",  # Updated
            last_name="Anderson",  # Unchanged
            birthday=date(1990, 1, 1),
            latest_news="Old news",  # Unchanged
        )

        response = await client.patch(f"/api/contacts/{contact_id}", json={"first_name": "Alicia"})

        assert response.status_code == 200
        data = response.json()

        assert data["first_name"] == "Alicia"
        assert data["last_name"] == "Anderson"

    @pytest.mark.asyncio
    async def test_update_contact_empty_body(self, client: AsyncClient, mock_db_connection):
        """Test update with empty body (no fields to update)."""

        contact_id = uuid4()

        # Mock fetchrow - nothing changed
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Anderson",
            birthday=date(1990, 1, 1),
            latest_news="News",
        )

        response = await client.patch(f"/api/contacts/{contact_id}", json={})

        assert response.status_code == 200


class TestDeleteContact:
    """Tests for DELETE /api/contacts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_contact_success(self, client: AsyncClient, mock_db_connection):
        """Test successful contact deletion."""

        contact_id = uuid4()

        # Mock fetchrow (delete returns deleted row id)
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(id=contact_id)

        response = await client.delete(f"/api/contacts/{contact_id}")

        assert response.status_code == 204
        assert response.content == b""  # No content for 204

    @pytest.mark.asyncio
    async def test_delete_contact_not_found(self, client: AsyncClient, mock_db_connection):
        """Test deleting non-existent contact."""

        contact_id = uuid4()

        # Mock fetchrow returns None (contact not found)
        mock_db_connection.fetchrow.return_value = None

        response = await client.delete(f"/api/contacts/{contact_id}")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_contact_invalid_uuid(self, client: AsyncClient, mock_db_connection):
        """Test deleting with invalid UUID."""
        response = await client.delete("/api/contacts/not-a-uuid")
        assert response.status_code == 422  # Validation error


class TestListContactInteractions:
    """Tests for GET /api/contacts/{id}/interactions endpoint."""

    @pytest.mark.asyncio
    async def test_list_contact_interactions_success(self, client: AsyncClient, mock_db_connection):
        """Test successful retrieval of contact interactions."""

        contact_id = uuid4()
        interaction1_id = uuid4()
        interaction2_id = uuid4()

        # Mock two calls: first fetchrow for contact check, then fetch for interactions
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Alice",
            last_name="Anderson",
            birthday=date(1990, 1, 1),
            latest_news="Recent news",
        )

        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=interaction1_id,
                contact_id=contact_id,
                interaction_date=date(2024, 1, 15),
                notes="Met for coffee",
                location="Starbucks",
            ),
            mock_db_connection.make_record(
                id=interaction2_id,
                contact_id=contact_id,
                interaction_date=date(2024, 1, 10),
                notes="Phone call",
                location=None,
            ),
        ]

        response = await client.get(f"/api/contacts/{contact_id}/interactions")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["id"] == str(interaction1_id)
        assert data[0]["notes"] == "Met for coffee"
        assert data[0]["location"] == "Starbucks"
        assert data[1]["id"] == str(interaction2_id)
        assert data[1]["notes"] == "Phone call"
        assert data[1]["location"] is None

    @pytest.mark.asyncio
    async def test_list_contact_interactions_empty(self, client: AsyncClient, mock_db_connection):
        """Test listing interactions for contact with no interactions."""

        contact_id = uuid4()

        # Contact exists
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=contact_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            first_name="Bob",
            last_name="Brown",
            birthday=None,
            latest_news=None,
        )

        # No interactions
        mock_db_connection.fetch.return_value = []

        response = await client.get(f"/api/contacts/{contact_id}/interactions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        assert data == []

    @pytest.mark.asyncio
    async def test_list_contact_interactions_contact_not_found(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test listing interactions for non-existent contact."""

        contact_id = uuid4()

        # Contact not found
        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/api/contacts/{contact_id}/interactions")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]


class TestGetContactSummary:
    """Tests for GET /api/contacts/{id}/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_contact_summary_success(self, client: AsyncClient, mock_db_connection):
        """Test successful contact summary retrieval with all data."""

        contact_id = uuid4()
        family_member_id = uuid4()
        interaction1_id = uuid4()
        interaction2_id = uuid4()

        # Mock 5 sequential fetchrow/fetch calls:
        # 1. Contact basic info
        # 2. Interaction count
        # 3. Recent interactions
        # 4. Family members
        # 5. Last interaction date

        mock_db_connection.fetchrow.side_effect = [
            # 1. Contact basic info
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alice",
                last_name="Anderson",
                birthday=date(1990, 1, 1),
                latest_news="Recent update",
            ),
            # 2. Interaction count
            mock_db_connection.make_record(total=10),
            # 5. Last interaction date
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 15)),
        ]

        mock_db_connection.fetch.side_effect = [
            # 3. Recent interactions
            [
                mock_db_connection.make_record(
                    id=interaction1_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 15),
                    notes="Coffee meeting",
                    location="Starbucks",
                ),
                mock_db_connection.make_record(
                    id=interaction2_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 10),
                    notes="Phone call",
                    location=None,
                ),
            ],
            # 4. Family members
            [
                mock_db_connection.make_record(
                    id=uuid4(),
                    family_contact_id=family_member_id,
                    relationship="spouse",
                    first_name="Bob",
                    last_name="Anderson",
                ),
            ],
        ]

        response = await client.get(f"/api/contacts/{contact_id}/summary")

        assert response.status_code == 200
        data = response.json()

        # Verify contact info
        assert data["contact"]["id"] == str(contact_id)
        assert data["contact"]["first_name"] == "Alice"
        assert data["contact"]["last_name"] == "Anderson"
        assert data["contact"]["birthday"] == "1990-01-01"
        assert data["contact"]["latest_news"] == "Recent update"

        # Verify statistics
        assert data["total_interactions"] == 10
        assert data["last_interaction_date"] == "2024-01-15"

        # Verify recent interactions
        assert len(data["recent_interactions"]) == 2
        assert data["recent_interactions"][0]["id"] == str(interaction1_id)
        assert data["recent_interactions"][0]["notes"] == "Coffee meeting"
        assert data["recent_interactions"][1]["id"] == str(interaction2_id)

        # Verify family members
        assert len(data["family_members"]) == 1
        assert data["family_members"][0]["family_contact_id"] == str(family_member_id)
        assert data["family_members"][0]["relationship"] == "spouse"
        assert data["family_members"][0]["first_name"] == "Bob"

    @pytest.mark.asyncio
    async def test_get_contact_summary_no_interactions(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test contact summary with no interactions."""

        contact_id = uuid4()

        mock_db_connection.fetchrow.side_effect = [
            # Contact basic info
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Charlie",
                last_name="Chen",
                birthday=None,
                latest_news=None,
            ),
            # Interaction count (0)
            mock_db_connection.make_record(total=0),
            # Last interaction date (None)
            mock_db_connection.make_record(last_interaction_date=None),
        ]

        mock_db_connection.fetch.side_effect = [
            # Recent interactions (empty)
            [],
            # Family members (empty)
            [],
        ]

        response = await client.get(f"/api/contacts/{contact_id}/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["contact"]["first_name"] == "Charlie"
        assert data["total_interactions"] == 0
        assert data["last_interaction_date"] is None
        assert len(data["recent_interactions"]) == 0
        assert len(data["family_members"]) == 0

    @pytest.mark.asyncio
    async def test_get_contact_summary_no_family(self, client: AsyncClient, mock_db_connection):
        """Test contact summary with no family members."""

        contact_id = uuid4()
        interaction_id = uuid4()

        mock_db_connection.fetchrow.side_effect = [
            # Contact basic info
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Diana",
                last_name="Davis",
                birthday=date(1995, 5, 5),
                latest_news="Promoted to manager",
            ),
            # Interaction count
            mock_db_connection.make_record(total=3),
            # Last interaction date
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 20)),
        ]

        mock_db_connection.fetch.side_effect = [
            # Recent interactions
            [
                mock_db_connection.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 20),
                    notes="Lunch",
                    location="Restaurant",
                ),
            ],
            # Family members (empty)
            [],
        ]

        response = await client.get(f"/api/contacts/{contact_id}/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["contact"]["first_name"] == "Diana"
        assert data["total_interactions"] == 3
        assert len(data["recent_interactions"]) == 1
        assert len(data["family_members"]) == 0

    @pytest.mark.asyncio
    async def test_get_contact_summary_not_found(self, client: AsyncClient, mock_db_connection):
        """Test contact summary for non-existent contact."""

        contact_id = uuid4()

        # Contact not found
        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/api/contacts/{contact_id}/summary")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_contact_summary_invalid_uuid(self, client: AsyncClient, mock_db_connection):
        """Test contact summary with invalid UUID."""
        response = await client.get("/api/contacts/not-a-uuid/summary")
        assert response.status_code == 422  # Validation error
