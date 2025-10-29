"""Tests for family member endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


class TestCreateFamilyMember:
    """Tests for POST /api/relationships endpoint."""

    @pytest.mark.asyncio
    async def test_create_family_member_success(self, client: AsyncClient, mock_db_connection):
        """Test successful family member relationship creation."""
        contact_id = uuid4()
        family_contact_id = uuid4()
        family_member_id = uuid4()

        # Mock the family member creation
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=family_member_id,
            contact_id=contact_id,
            family_contact_id=family_contact_id,
            relationship="spouse",
        )

        response = await client.post(
            "/api/relationships",
            json={
                "contact_id": str(contact_id),
                "family_contact_id": str(family_contact_id),
                "relationship": "spouse",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["id"] == str(family_member_id)
        assert data["contact_id"] == str(contact_id)
        assert data["family_contact_id"] == str(family_contact_id)
        assert data["relationship"] == "spouse"

    @pytest.mark.asyncio
    async def test_create_family_member_already_exists(
        self, client: AsyncClient, mock_db_connection
    ):
        """Test creating duplicate family member relationship."""
        contact_id = uuid4()
        family_contact_id = uuid4()

        # Mock returns None when relationship already exists
        mock_db_connection.fetchrow.return_value = None

        response = await client.post(
            "/api/relationships",
            json={
                "contact_id": str(contact_id),
                "family_contact_id": str(family_contact_id),
                "relationship": "sibling",
            },
        )

        assert response.status_code == 400
        assert "already exist" in response.json()["detail"].lower()


class TestGetFamilyMember:
    """Tests for GET /api/relationships/{family_member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_family_member_success(self, client: AsyncClient, mock_db_connection):
        """Test successful family member retrieval."""
        family_member_id = uuid4()
        contact_id = uuid4()
        family_contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=family_member_id,
            contact_id=contact_id,
            family_contact_id=family_contact_id,
            relationship="parent",
        )

        response = await client.get(f"/api/relationships/{family_member_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(family_member_id)
        assert data["relationship"] == "parent"

    @pytest.mark.asyncio
    async def test_get_family_member_not_found(self, client: AsyncClient, mock_db_connection):
        """Test getting non-existent family member."""
        family_member_id = uuid4()
        mock_db_connection.fetchrow.return_value = None

        response = await client.get(f"/api/relationships/{family_member_id}")

        assert response.status_code == 404


class TestUpdateFamilyMember:
    """Tests for PATCH /api/relationships/{family_member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_family_member_success(self, client: AsyncClient, mock_db_connection):
        """Test successful family member relationship update."""
        family_member_id = uuid4()
        contact_id = uuid4()
        family_contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=family_member_id,
            contact_id=contact_id,
            family_contact_id=family_contact_id,
            relationship="child",
        )

        response = await client.patch(
            f"/api/relationships/{family_member_id}?relationship_type=child"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["relationship"] == "child"

    @pytest.mark.asyncio
    async def test_update_family_member_not_found(self, client: AsyncClient, mock_db_connection):
        """Test updating non-existent family member."""
        family_member_id = uuid4()
        mock_db_connection.fetchrow.return_value = None

        response = await client.patch(
            f"/api/relationships/{family_member_id}?relationship_type=cousin"
        )

        assert response.status_code == 404


class TestDeleteFamilyMember:
    """Tests for DELETE /api/relationships/{family_member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_family_member_success(self, client: AsyncClient, mock_db_connection):
        """Test successful family member deletion."""
        family_member_id = uuid4()
        contact_id = uuid4()
        family_contact_id = uuid4()

        # Mock get family member by id, find inverse, delete both
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=family_member_id,
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="sibling",
            ),
            mock_db_connection.make_record(id=uuid4()),  # Inverse relationship lookup
            mock_db_connection.make_record(id=uuid4()),  # Delete inverse
            mock_db_connection.make_record(id=family_member_id),  # Delete primary
        ]

        response = await client.delete(f"/api/relationships/{family_member_id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_family_member_not_found(self, client: AsyncClient, mock_db_connection):
        """Test deleting non-existent family member."""
        family_member_id = uuid4()

        # Mock returns None for all queries
        mock_db_connection.fetchrow.return_value = None

        response = await client.delete(f"/api/relationships/{family_member_id}")

        assert response.status_code == 404


class TestListAvailableContacts:
    """Tests for GET /api/relationships/contacts/{contact_id}/available endpoint."""

    @pytest.mark.asyncio
    async def test_list_available_contacts_success(self, client: AsyncClient, mock_db_connection):
        """Test listing available contacts for family member selection."""
        contact_id = uuid4()

        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(),
                first_name="Alice",
                last_name="Anderson",
                birthday=None,
            ),
            mock_db_connection.make_record(
                id=uuid4(),
                first_name="Bob",
                last_name="Brown",
                birthday=None,
            ),
        ]

        response = await client.get(f"/api/relationships/contacts/{contact_id}/available")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["first_name"] == "Alice"
        assert data[1]["first_name"] == "Bob"

    @pytest.mark.asyncio
    async def test_list_available_contacts_empty(self, client: AsyncClient, mock_db_connection):
        """Test listing available contacts when none exist."""
        contact_id = uuid4()

        mock_db_connection.fetch.return_value = []

        response = await client.get(f"/api/relationships/contacts/{contact_id}/available")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 0


class TestFamilyMemberUIEndpoints:
    """Tests for family member UI endpoints."""

    @pytest.mark.asyncio
    async def test_get_new_family_member_form(self, client: AsyncClient, mock_db_connection):
        """Test getting new family member form."""
        contact_id = uuid4()

        # Mock contact summary queries (contact, count, recent, family, last_date)
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="John",
                last_name="Doe",
                birthday=None,
                latest_news=None,
            ),
            mock_db_connection.make_record(total=0),  # count interactions
            mock_db_connection.make_record(last_interaction_date=None),  # last date
        ]

        mock_db_connection.fetch.side_effect = [
            [],  # recent interactions
            [],  # family members
            [  # available contacts for selection
                mock_db_connection.make_record(
                    id=uuid4(),
                    first_name="Jane",
                    last_name="Smith",
                    birthday=None,
                )
            ],
        ]

        response = await client.get(f"/ui/contacts/{contact_id}/relationships/new")

        assert response.status_code == 200
        assert b"Select Contact" in response.content
        assert b"Jane Smith" in response.content

    @pytest.mark.asyncio
    async def test_create_family_member_ui(self, client: AsyncClient, mock_db_connection):
        """Test creating family member via UI."""
        contact_id = uuid4()
        family_contact_id = uuid4()

        # Mock family member creation, reverse, then contact summary queries
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=uuid4(),
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="spouse",
            ),
            mock_db_connection.make_record(id=uuid4()),  # Reverse relationship
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="John",
                last_name="Doe",
                birthday=None,
                latest_news=None,
            ),
            mock_db_connection.make_record(total=0),  # count interactions
            mock_db_connection.make_record(last_interaction_date=None),  # last date
        ]

        mock_db_connection.fetch.side_effect = [
            [],  # recent interactions
            [],  # family members
        ]

        response = await client.post(
            f"/ui/contacts/{contact_id}/relationships",
            data={
                "related_contact_id": str(family_contact_id),
                "relationship": "spouse",
            },
        )

        assert response.status_code == 200
        assert b"relationship-section" in response.content

    @pytest.mark.asyncio
    async def test_get_family_member_edit_form(self, client: AsyncClient, mock_db_connection):
        """Test getting family member edit form."""
        family_member_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=family_member_id,
            contact_id=contact_id,
            family_contact_id=uuid4(),
            relationship="parent",
        )

        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=family_member_id,
                family_contact_id=uuid4(),
                relationship="parent",
                first_name="Jane",
                last_name="Doe",
            )
        ]

        response = await client.get(f"/ui/relationships/{family_member_id}/edit")

        assert response.status_code == 200
        assert b"Relationship:" in response.content
        assert b"parent" in response.content

    @pytest.mark.asyncio
    async def test_update_family_member_ui(self, client: AsyncClient, mock_db_connection):
        """Test updating family member via UI."""
        family_member_id = uuid4()
        contact_id = uuid4()

        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=family_member_id,
            contact_id=contact_id,
            family_contact_id=uuid4(),
            relationship="child",
        )

        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=family_member_id,
                family_contact_id=uuid4(),
                relationship="child",
                first_name="Jane",
                last_name="Doe",
            )
        ]

        response = await client.patch(
            f"/ui/relationships/{family_member_id}",
            data={"relationship": "child"},
        )

        assert response.status_code == 200
        assert b"relationship-item" in response.content

    @pytest.mark.asyncio
    async def test_delete_family_member_ui(self, client: AsyncClient, mock_db_connection):
        """Test deleting family member via UI."""
        family_member_id = uuid4()
        contact_id = uuid4()
        family_contact_id = uuid4()

        # Mock get, lookup inverse, delete inverse, delete primary
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=family_member_id,
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="sibling",
            ),
            mock_db_connection.make_record(
                id=family_member_id,
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="sibling",
            ),
            mock_db_connection.make_record(id=uuid4()),  # Find inverse relationship
            mock_db_connection.make_record(id=uuid4()),  # Delete inverse
            mock_db_connection.make_record(id=family_member_id),  # Delete primary
        ]

        response = await client.delete(f"/ui/relationships/{family_member_id}")

        assert response.status_code == 200


class TestFamilyMemberService:
    """Tests for family member service functions."""

    @pytest.mark.asyncio
    async def test_bidirectional_relationship_creation(self):
        """Test that bidirectional relationships are created correctly."""
        from unittest.mock import AsyncMock

        from backend.app.services.relationships import create_relationship

        mock_conn = AsyncMock()
        contact_id = uuid4()
        family_contact_id = uuid4()

        # Mock successful forward relationship creation
        mock_conn.fetchrow.side_effect = [
            {
                "id": uuid4(),
                "contact_id": contact_id,
                "family_contact_id": family_contact_id,
                "relationship": "parent",
            },
            {
                "id": uuid4(),
                "contact_id": family_contact_id,
                "family_contact_id": contact_id,
                "relationship": "child",
            },
        ]

        result = await create_relationship(
            mock_conn,
            UUID("00000000-0000-0000-0000-000000000000"),
            contact_id,
            family_contact_id,
            "parent",
            bidirectional=True,
        )

        assert result is not None
        assert result.relationship == "parent"

    @pytest.mark.asyncio
    async def test_prevent_self_relationship(self):
        """Test that self-relationships are prevented."""
        from unittest.mock import AsyncMock

        from backend.app.services.relationships import create_relationship

        mock_conn = AsyncMock()
        contact_id = uuid4()

        result = await create_relationship(
            mock_conn,
            UUID("00000000-0000-0000-0000-000000000000"),
            contact_id,
            contact_id,  # Same as contact_id
            "sibling",
            bidirectional=True,
        )

        assert result is None
        # No database calls should be made
        assert mock_conn.fetchrow.call_count == 0

    @pytest.mark.asyncio
    async def test_relationship_inverse_mapping(self):
        """Test that relationship inverses are correctly mapped."""
        from backend.app.services.relationships import get_inverse_relationship

        assert get_inverse_relationship("parent") == "child"
        assert get_inverse_relationship("child") == "parent"
        assert get_inverse_relationship("spouse") == "spouse"
        assert get_inverse_relationship("sibling") == "sibling"
        assert get_inverse_relationship("grandparent") == "grandchild"
        assert get_inverse_relationship("grandchild") == "grandparent"
        assert get_inverse_relationship("unknown") == "related_to"
