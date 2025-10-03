"""Tests for contact endpoints."""

from datetime import date
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


class TestListContacts:
    """Tests for GET /api/contacts endpoint."""

    @pytest.mark.asyncio
    async def test_list_contacts_success(self, client: AsyncClient):
        """Test successful contact list retrieval."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock count query
            mock_instance.fetchrow.return_value = make_record(total=2)

            # Mock list query
            mock_instance.fetch.return_value = [
                make_record(
                    id=uuid4(),
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    first_name="Alice",
                    last_name="Anderson",
                    birthday=date(1990, 1, 1),
                    latest_news="Recent update about Alice",
                ),
                make_record(
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
    async def test_list_contacts_empty(self, client: AsyncClient):
        """Test contact list when no contacts exist."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock count query
            mock_instance.fetchrow.return_value = make_record(total=0)

            # Mock list query
            mock_instance.fetch.return_value = []

            response = await client.get("/api/contacts")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0
        assert len(data["contacts"]) == 0

    @pytest.mark.asyncio
    async def test_list_contacts_pagination(self, client: AsyncClient):
        """Test contact list pagination parameters."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock count query (50 total contacts)
            mock_instance.fetchrow.return_value = make_record(total=50)

            # Mock list query (return 10 contacts for page 2)
            mock_instance.fetch.return_value = [
                make_record(
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
    async def test_list_contacts_invalid_page(self, client: AsyncClient):
        """Test contact list with invalid page parameter."""
        response = await client.get("/api/contacts?page=0")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_list_contacts_invalid_page_size(self, client: AsyncClient):
        """Test contact list with invalid page_size parameter."""
        response = await client.get("/api/contacts?page_size=101")
        assert response.status_code == 422  # Validation error (max 100)

        response = await client.get("/api/contacts?page_size=0")
        assert response.status_code == 422  # Validation error (min 1)


class TestGetContact:
    """Tests for GET /api/contacts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_contact_success(self, client: AsyncClient):
        """Test successful contact retrieval."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow
            mock_instance.fetchrow.return_value = make_record(
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
    async def test_get_contact_not_found(self, client: AsyncClient):
        """Test contact not found (404)."""

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow returns None (contact not found)
            mock_instance.fetchrow.return_value = None

            response = await client.get(f"/api/contacts/{contact_id}")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_contact_invalid_uuid(self, client: AsyncClient):
        """Test invalid UUID format."""
        response = await client.get("/api/contacts/not-a-uuid")
        assert response.status_code == 422  # Validation error


class TestUpdateContact:
    """Tests for PATCH /api/contacts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_contact_success(self, client: AsyncClient):
        """Test successful contact update."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow (update returns updated row)
            mock_instance.fetchrow.return_value = make_record(
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
    async def test_update_contact_not_found(self, client: AsyncClient):
        """Test updating non-existent contact."""

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow returns None (contact not found)
            mock_instance.fetchrow.return_value = None

            response = await client.patch(
                f"/api/contacts/{contact_id}", json={"first_name": "Updated"}
            )

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_contact_partial(self, client: AsyncClient):
        """Test partial update (only some fields)."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow - only first_name updated
            mock_instance.fetchrow.return_value = make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alicia",  # Updated
                last_name="Anderson",  # Unchanged
                birthday=date(1990, 1, 1),
                latest_news="Old news",  # Unchanged
            )

            response = await client.patch(
                f"/api/contacts/{contact_id}", json={"first_name": "Alicia"}
            )

        assert response.status_code == 200
        data = response.json()

        assert data["first_name"] == "Alicia"
        assert data["last_name"] == "Anderson"

    @pytest.mark.asyncio
    async def test_update_contact_empty_body(self, client: AsyncClient):
        """Test update with empty body (no fields to update)."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow - nothing changed
            mock_instance.fetchrow.return_value = make_record(
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
    async def test_delete_contact_success(self, client: AsyncClient):
        """Test successful contact deletion."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow (delete returns deleted row id)
            mock_instance.fetchrow.return_value = make_record(id=contact_id)

            response = await client.delete(f"/api/contacts/{contact_id}")

        assert response.status_code == 204
        assert response.content == b""  # No content for 204

    @pytest.mark.asyncio
    async def test_delete_contact_not_found(self, client: AsyncClient):
        """Test deleting non-existent contact."""

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock fetchrow returns None (contact not found)
            mock_instance.fetchrow.return_value = None

            response = await client.delete(f"/api/contacts/{contact_id}")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_contact_invalid_uuid(self, client: AsyncClient):
        """Test deleting with invalid UUID."""
        response = await client.delete("/api/contacts/not-a-uuid")
        assert response.status_code == 422  # Validation error


class TestListContactInteractions:
    """Tests for GET /api/contacts/{id}/interactions endpoint."""

    @pytest.mark.asyncio
    async def test_list_contact_interactions_success(self, client: AsyncClient):
        """Test successful retrieval of contact interactions."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()
        interaction1_id = uuid4()
        interaction2_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Mock two calls: first fetchrow for contact check, then fetch for interactions
            mock_instance.fetchrow.return_value = make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Alice",
                last_name="Anderson",
                birthday=date(1990, 1, 1),
                latest_news="Recent news",
            )

            mock_instance.fetch.return_value = [
                make_record(
                    id=interaction1_id,
                    contact_id=contact_id,
                    interaction_date=date(2024, 1, 15),
                    notes="Met for coffee",
                    location="Starbucks",
                ),
                make_record(
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
    async def test_list_contact_interactions_empty(self, client: AsyncClient):
        """Test listing interactions for contact with no interactions."""

        def make_record(**kwargs):
            class MockRecord(dict):
                def __getitem__(self, key):
                    return super().__getitem__(key)

            return MockRecord(**kwargs)

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Contact exists
            mock_instance.fetchrow.return_value = make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Bob",
                last_name="Brown",
                birthday=None,
                latest_news=None,
            )

            # No interactions
            mock_instance.fetch.return_value = []

            response = await client.get(f"/api/contacts/{contact_id}/interactions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        assert data == []

    @pytest.mark.asyncio
    async def test_list_contact_interactions_contact_not_found(self, client: AsyncClient):
        """Test listing interactions for non-existent contact."""

        mock_conn = patch("backend.app.routers.contacts.get_db_connection")
        contact_id = uuid4()

        with mock_conn as mock:
            mock_instance = mock.return_value.__aenter__.return_value

            # Contact not found
            mock_instance.fetchrow.return_value = None

            response = await client.get(f"/api/contacts/{contact_id}/interactions")

        assert response.status_code == 404
        assert "Contact not found" in response.json()["detail"]
