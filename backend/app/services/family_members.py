"""Family member business logic - shared between API and UI."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import Contact, FamilyMember, FamilyMemberWithDetails

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_CREATE_FAMILY_MEMBER = load_sql("family_members/create.sql")
SQL_GET_FAMILY_MEMBER_BY_ID = load_sql("family_members/get_by_id.sql")
SQL_UPDATE_FAMILY_MEMBER = load_sql("family_members/update.sql")
SQL_DELETE_FAMILY_MEMBER = load_sql("family_members/delete.sql")
SQL_LIST_CONTACTS_FOR_SELECTION = load_sql("contacts/list_for_selection.sql")
SQL_FAMILY_MEMBERS_WITH_DETAILS = load_sql("contacts/family_members_with_details.sql")

# Relationship inverse mapping
RELATIONSHIP_INVERSES = {
    "parent": "child",
    "child": "parent",
    "spouse": "spouse",
    "sibling": "sibling",
    "partner": "partner",
    "friend": "friend",
    "grandparent": "grandchild",
    "grandchild": "grandparent",
    "aunt/uncle": "niece/nephew",
    "niece/nephew": "aunt/uncle",
    "cousin": "cousin",
}


def get_inverse_relationship(relationship: str) -> str:
    """Get the inverse relationship type."""
    return RELATIONSHIP_INVERSES.get(relationship.lower(), "related_to")


async def create_family_member_relationship(
    conn: asyncpg.Connection,
    user_id: UUID,
    contact_id: UUID,
    family_contact_id: UUID,
    relationship: str,
    bidirectional: bool = True,
) -> FamilyMember | None:
    """
    Create a family member relationship between two contacts.

    Args:
        conn: Database connection
        user_id: User ID
        contact_id: ID of the primary contact
        family_contact_id: ID of the related family member contact
        relationship: Relationship type (e.g., "parent", "spouse")
        bidirectional: If True, creates inverse relationship automatically

    Returns:
        FamilyMember if created, None if already exists or invalid
    """
    # Prevent self-relationships
    if contact_id == family_contact_id:
        logger.warning(
            "attempted_self_relationship",
            contact_id=str(contact_id),
            user_id=str(user_id),
        )
        return None

    # Create forward relationship
    forward_row = await conn.fetchrow(
        SQL_CREATE_FAMILY_MEMBER,
        contact_id,
        family_contact_id,
        relationship,
    )

    if not forward_row:
        logger.info(
            "family_relationship_already_exists",
            contact_id=str(contact_id),
            family_contact_id=str(family_contact_id),
            relationship=relationship,
        )
        return None

    # Create reverse relationship if bidirectional
    if bidirectional:
        inverse_relationship = get_inverse_relationship(relationship)
        await conn.fetchrow(
            SQL_CREATE_FAMILY_MEMBER,
            family_contact_id,
            contact_id,
            inverse_relationship,
        )
        logger.info(
            "bidirectional_relationship_created",
            forward_relationship=relationship,
            inverse_relationship=inverse_relationship,
        )

    family_member = FamilyMember(
        id=forward_row["id"],
        contact_id=forward_row["contact_id"],
        family_contact_id=forward_row["family_contact_id"],
        relationship=forward_row["relationship"],
    )

    logger.info(
        "family_member_relationship_created",
        family_member_id=str(family_member.id),
        contact_id=str(contact_id),
        family_contact_id=str(family_contact_id),
        relationship=relationship,
    )

    return family_member


async def get_family_member_by_id(
    conn: asyncpg.Connection, family_member_id: UUID, user_id: UUID
) -> FamilyMember | None:
    """Get a family member relationship by ID."""
    row = await conn.fetchrow(SQL_GET_FAMILY_MEMBER_BY_ID, family_member_id, user_id)

    if row is None:
        logger.warning(
            "family_member_not_found",
            family_member_id=str(family_member_id),
            user_id=str(user_id),
        )
        return None

    return FamilyMember(
        id=row["id"],
        contact_id=row["contact_id"],
        family_contact_id=row["family_contact_id"],
        relationship=row["relationship"],
    )


async def update_family_member_relationship(
    conn: asyncpg.Connection,
    family_member_id: UUID,
    user_id: UUID,
    relationship: str,
) -> FamilyMember | None:
    """
    Update a family member relationship type.

    Note: This only updates one direction. For bidirectional updates,
    you need to find and update the inverse relationship separately.
    """
    row = await conn.fetchrow(
        SQL_UPDATE_FAMILY_MEMBER,
        family_member_id,
        user_id,
        None,  # $3 is unused but kept for consistency
        relationship,
    )

    if row is None:
        logger.warning(
            "family_member_not_found_for_update",
            family_member_id=str(family_member_id),
            user_id=str(user_id),
        )
        return None

    family_member = FamilyMember(
        id=row["id"],
        contact_id=row["contact_id"],
        family_contact_id=row["family_contact_id"],
        relationship=row["relationship"],
    )

    logger.info(
        "family_member_relationship_updated",
        family_member_id=str(family_member_id),
        new_relationship=relationship,
    )

    return family_member


async def delete_family_member_relationship(
    conn: asyncpg.Connection,
    family_member_id: UUID,
    user_id: UUID,
    bidirectional: bool = True,
) -> bool:
    """
    Delete a family member relationship.

    Args:
        conn: Database connection
        family_member_id: ID of the family member relationship to delete
        user_id: User ID
        bidirectional: If True, also deletes the inverse relationship

    Returns:
        True if deleted, False if not found
    """
    # Get the relationship details first if we need to delete bidirectionally
    if bidirectional:
        family_member = await get_family_member_by_id(conn, family_member_id, user_id)
        if family_member:
            # Find and delete the inverse relationship
            inverse_row = await conn.fetchrow(
                """
                SELECT id FROM family_member
                WHERE contact_id = $1 AND family_contact_id = $2
                """,
                family_member.family_contact_id,
                family_member.contact_id,
            )
            if inverse_row:
                await conn.fetchrow(SQL_DELETE_FAMILY_MEMBER, inverse_row["id"], user_id)
                logger.info(
                    "inverse_family_relationship_deleted",
                    family_member_id=str(inverse_row["id"]),
                )

    # Delete the primary relationship
    row = await conn.fetchrow(SQL_DELETE_FAMILY_MEMBER, family_member_id, user_id)

    if row is None:
        logger.warning(
            "family_member_not_found_for_delete",
            family_member_id=str(family_member_id),
            user_id=str(user_id),
        )
        return False

    logger.info(
        "family_member_relationship_deleted",
        family_member_id=str(family_member_id),
    )

    return True


async def list_contacts_for_selection(
    conn: asyncpg.Connection, user_id: UUID, exclude_contact_id: UUID
) -> list[Contact]:
    """
    List contacts available for family member selection.

    Excludes the specified contact to prevent self-relationships.
    """
    rows = await conn.fetch(SQL_LIST_CONTACTS_FOR_SELECTION, user_id, exclude_contact_id)

    contacts = [
        Contact(
            id=row["id"],
            user_id=user_id,
            first_name=row["first_name"],
            last_name=row["last_name"],
            birthday=row["birthday"],
            latest_news=None,
        )
        for row in rows
    ]

    logger.info(
        "contacts_listed_for_selection",
        user_id=str(user_id),
        exclude_contact_id=str(exclude_contact_id),
        count=len(contacts),
    )

    return contacts


async def get_family_members_with_details(
    conn: asyncpg.Connection, contact_id: UUID, user_id: UUID
) -> list[FamilyMemberWithDetails]:
    """Get family members with full contact details for a contact."""
    rows = await conn.fetch(SQL_FAMILY_MEMBERS_WITH_DETAILS, contact_id, user_id)

    family_members = [
        FamilyMemberWithDetails(
            id=row["id"],
            family_contact_id=row["family_contact_id"],
            relationship=row["relationship"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )
        for row in rows
    ]

    return family_members
