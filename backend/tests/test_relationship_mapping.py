"""Test bidirectional family relationship creation."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.app.models import (
    ConfirmInteractionRequest,
    ExtractedContact,
    ExtractedFamilyMember,
    ExtractedInteraction,
)
from backend.app.services.interactions import confirm_and_persist_interaction


class TestBidirectionalFamilyRelationships:
    """Test that family relationships are created bidirectionally."""

    @pytest.mark.parametrize(
        "relationship,expected_inverse",
        [
            ("parent", "child"),
            ("child", "parent"),
            ("spouse", "spouse"),
            ("sibling", "sibling"),
        ],
    )
    async def test_family_relationship_creates_bidirectional_links(
        self, test_user_id, relationship, expected_inverse
    ):
        """Test that creating a family relationship creates both forward and reverse links."""
        # Set up mock database connection that tracks insertions
        mock_conn = AsyncMock()
        family_insertions = []

        async def mock_fetchrow(query, *args):
            if "INSERT INTO family_member" in query:
                contact_id, family_contact_id, rel = args[:3]
                family_insertions.append((contact_id, family_contact_id, rel))
                return {"id": uuid4()}
            elif "INSERT INTO contact" in query:
                return {"id": uuid4()}
            elif "INSERT INTO interaction" in query:
                return {"id": uuid4()}
            return None

        mock_conn.fetchrow = mock_fetchrow
        mock_conn.execute = AsyncMock()

        # Create test data
        contact = ExtractedContact(first_name="John", last_name="Doe", confidence=0.9)

        family_member = ExtractedFamilyMember(
            first_name="Jane", last_name="Doe", relationship=relationship, confidence=0.8
        )

        interaction = ExtractedInteraction(
            notes="Had dinner with family", interaction_date="2024-01-15", confidence=0.9
        )

        request = ConfirmInteractionRequest(
            contact=contact, interaction=interaction, family_members=[family_member]
        )

        # Create the interaction and relationships
        contact_id, interaction_id, family_count = await confirm_and_persist_interaction(
            mock_conn, test_user_id, request
        )

        # Verify one family member was linked
        assert family_count == 1

        # Verify that both forward and reverse relationships were created

        # Should have exactly 2 insertions (forward + reverse)
        assert len(family_insertions) == 2

        # Extract the relationships that were inserted
        inserted_relationships = [rel for contact_id, family_contact_id, rel in family_insertions]

        # Verify both relationships were created
        assert relationship in inserted_relationships
        assert expected_inverse in inserted_relationships

        # Verify the relationships are between the same two contacts
        contact_ids = set()
        family_contact_ids = set()
        for contact_id, family_contact_id, _ in family_insertions:
            contact_ids.add(contact_id)
            family_contact_ids.add(family_contact_id)

        # Should have exactly 2 unique contact IDs (John and Jane)
        assert len(contact_ids) == 2
        assert len(family_contact_ids) == 2
