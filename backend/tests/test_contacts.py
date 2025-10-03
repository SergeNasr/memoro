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
