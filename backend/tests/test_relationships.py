"""Tests for relationship/family member functionality."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


class TestRelationshipsAPI:
    """Relationship API endpoints."""

    async def test_create(self, client: AsyncClient, mock_db_connection):
        """Create relationship."""
        contact_id, family_contact_id, rel_id = uuid4(), uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=rel_id,
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
        assert response.json()["relationship"] == "spouse"

    async def test_create_duplicate(self, client: AsyncClient, mock_db_connection):
        """Duplicate relationship returns 400."""
        mock_db_connection.fetchrow.return_value = None
        response = await client.post(
            "/api/relationships",
            json={
                "contact_id": str(uuid4()),
                "family_contact_id": str(uuid4()),
                "relationship": "sibling",
            },
        )
        assert response.status_code == 400

    async def test_get(self, client: AsyncClient, mock_db_connection):
        """Get relationship."""
        rel_id, contact_id, family_contact_id = uuid4(), uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=rel_id,
            contact_id=contact_id,
            family_contact_id=family_contact_id,
            relationship="parent",
        )

        response = await client.get(f"/api/relationships/{rel_id}")
        assert response.status_code == 200
        assert response.json()["relationship"] == "parent"

    async def test_delete(self, client: AsyncClient, mock_db_connection):
        """Delete relationship removes both directions."""
        rel_id, contact_id, family_contact_id = uuid4(), uuid4(), uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=rel_id,
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="sibling",
            ),
            mock_db_connection.make_record(id=uuid4()),  # Inverse lookup
            mock_db_connection.make_record(id=uuid4()),  # Delete inverse
            mock_db_connection.make_record(id=rel_id),  # Delete primary
        ]

        response = await client.delete(f"/api/relationships/{rel_id}")
        assert response.status_code == 204

    async def test_available_contacts(self, client: AsyncClient, mock_db_connection):
        """List available contacts for relationship."""
        contact_id = uuid4()
        mock_db_connection.fetch.return_value = [
            mock_db_connection.make_record(
                id=uuid4(), first_name="Alice", last_name="Anderson", birthday=None
            ),
            mock_db_connection.make_record(
                id=uuid4(), first_name="Bob", last_name="Brown", birthday=None
            ),
        ]

        response = await client.get(f"/api/relationships/contacts/{contact_id}/available")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestRelationshipsUI:
    """Relationship UI endpoints."""

    async def test_new_form(self, client: AsyncClient, mock_db_connection):
        """Get new relationship form."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="John",
                last_name="Doe",
                birthday=None,
                latest_news=None,
            ),
            mock_db_connection.make_record(total=0),
            mock_db_connection.make_record(last_interaction_date=None),
        ]
        mock_db_connection.fetch.side_effect = [
            [],
            [],
            [
                mock_db_connection.make_record(
                    id=uuid4(), first_name="Jane", last_name="Smith", birthday=None
                )
            ],
        ]

        response = await client.get(f"/ui/contacts/{contact_id}/relationships/new")
        assert response.status_code == 200
        assert b"Select Contact" in response.content

    async def test_create_ui(self, client: AsyncClient, mock_db_connection):
        """Create relationship via UI."""
        contact_id, family_contact_id = uuid4(), uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=uuid4(),
                contact_id=contact_id,
                family_contact_id=family_contact_id,
                relationship="spouse",
            ),
            mock_db_connection.make_record(id=uuid4()),  # Reverse
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="John",
                last_name="Doe",
                birthday=None,
                latest_news=None,
            ),
            mock_db_connection.make_record(total=0),
            mock_db_connection.make_record(last_interaction_date=None),
        ]
        mock_db_connection.fetch.side_effect = [[], []]

        response = await client.post(
            f"/ui/contacts/{contact_id}/relationships",
            data={"related_contact_id": str(family_contact_id), "relationship": "spouse"},
        )
        assert response.status_code == 200


class TestRelationshipInverses:
    """Relationship inverse mapping."""

    def test_inverses(self):
        """Relationship inverses are correct."""
        from backend.app.services.relationships import get_inverse_relationship

        assert get_inverse_relationship("parent") == "child"
        assert get_inverse_relationship("child") == "parent"
        assert get_inverse_relationship("spouse") == "spouse"
        assert get_inverse_relationship("sibling") == "sibling"
        assert get_inverse_relationship("grandparent") == "grandchild"
        assert get_inverse_relationship("unknown") == "related_to"


class TestBidirectionalCreation:
    """Bidirectional relationship creation."""

    @pytest.mark.parametrize(
        "relationship,inverse",
        [("parent", "child"), ("child", "parent"), ("spouse", "spouse"), ("sibling", "sibling")],
    )
    async def test_creates_both_directions(
        self, test_user_id, relationship, inverse, mock_openai_client
    ):
        """Creating relationship creates both directions."""
        from unittest.mock import AsyncMock

        from backend.app.services.interactions import confirm_and_persist_interaction

        mock_conn = AsyncMock()
        insertions = []

        async def mock_fetchrow(query, *args):
            if "INSERT INTO relationship" in query:
                insertions.append(args[2])  # relationship type
                return {"id": uuid4()}
            return {"id": uuid4()}

        mock_conn.fetchrow = mock_fetchrow
        mock_conn.execute = AsyncMock()

        await confirm_and_persist_interaction(
            mock_conn,
            test_user_id,
            first_name="John",
            last_name="Doe",
            birthday=None,
            interaction_date="2024-01-15",
            notes="Dinner",
            location=None,
            relationships=[
                {"first_name": "Jane", "last_name": "Doe", "relationship": relationship}
            ],
        )

        assert relationship in insertions
        assert inverse in insertions
