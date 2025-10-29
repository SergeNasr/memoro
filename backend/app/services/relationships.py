"""Relationship business logic - shared between API and UI."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import Contact, Relationship, RelationshipWithDetails

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_CREATE_RELATIONSHIP = load_sql("relationships/create.sql")
SQL_GET_RELATIONSHIP_BY_ID = load_sql("relationships/get_by_id.sql")
SQL_UPDATE_RELATIONSHIP = load_sql("relationships/update.sql")
SQL_DELETE_RELATIONSHIP = load_sql("relationships/delete.sql")
SQL_LIST_CONTACTS_FOR_SELECTION = load_sql("contacts/list_for_selection.sql")
SQL_RELATIONSHIPS_WITH_DETAILS = load_sql("contacts/relationships_with_details.sql")

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


async def create_relationship(
    conn: asyncpg.Connection,
    user_id: UUID,
    contact_id: UUID,
    family_contact_id: UUID,
    relationship: str,
    bidirectional: bool = True,
) -> Relationship | None:
    """
    Create a relationship between two contacts.

    Args:
        conn: Database connection
        user_id: User ID
        contact_id: ID of the primary contact
        family_contact_id: ID of the related contact
        relationship: Relationship type (e.g., "parent", "spouse")
        bidirectional: If True, creates inverse relationship automatically

    Returns:
        Relationship if created, None if already exists or invalid
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
        SQL_CREATE_RELATIONSHIP,
        contact_id,
        family_contact_id,
        relationship,
    )

    if not forward_row:
        logger.info(
            "relationship_already_exists",
            contact_id=str(contact_id),
            family_contact_id=str(family_contact_id),
            relationship=relationship,
        )
        return None

    # Create reverse relationship if bidirectional
    if bidirectional:
        inverse_relationship = get_inverse_relationship(relationship)
        await conn.fetchrow(
            SQL_CREATE_RELATIONSHIP,
            family_contact_id,
            contact_id,
            inverse_relationship,
        )
        logger.info(
            "bidirectional_relationship_created",
            forward_relationship=relationship,
            inverse_relationship=inverse_relationship,
        )

    relationship_obj = Relationship(
        id=forward_row["id"],
        contact_id=forward_row["contact_id"],
        family_contact_id=forward_row["family_contact_id"],
        relationship=forward_row["relationship"],
    )

    logger.info(
        "relationship_created",
        relationship_id=str(relationship_obj.id),
        contact_id=str(contact_id),
        family_contact_id=str(family_contact_id),
        relationship=relationship,
    )

    return relationship_obj


async def get_relationship_by_id(
    conn: asyncpg.Connection, relationship_id: UUID, user_id: UUID
) -> Relationship | None:
    """Get a relationship by ID."""
    row = await conn.fetchrow(SQL_GET_RELATIONSHIP_BY_ID, relationship_id, user_id)

    if row is None:
        logger.warning(
            "relationship_not_found",
            relationship_id=str(relationship_id),
            user_id=str(user_id),
        )
        return None

    return Relationship(
        id=row["id"],
        contact_id=row["contact_id"],
        family_contact_id=row["family_contact_id"],
        relationship=row["relationship"],
    )


async def update_relationship(
    conn: asyncpg.Connection,
    relationship_id: UUID,
    user_id: UUID,
    relationship: str,
) -> Relationship | None:
    """
    Update a relationship type.

    Note: This only updates one direction. For bidirectional updates,
    you need to find and update the inverse relationship separately.
    """
    row = await conn.fetchrow(
        SQL_UPDATE_RELATIONSHIP,
        relationship_id,
        user_id,
        None,  # $3 is unused but kept for consistency
        relationship,
    )

    if row is None:
        logger.warning(
            "relationship_not_found_for_update",
            relationship_id=str(relationship_id),
            user_id=str(user_id),
        )
        return None

    relationship_obj = Relationship(
        id=row["id"],
        contact_id=row["contact_id"],
        family_contact_id=row["family_contact_id"],
        relationship=row["relationship"],
    )

    logger.info(
        "relationship_updated",
        relationship_id=str(relationship_id),
        new_relationship=relationship,
    )

    return relationship_obj


async def delete_relationship(
    conn: asyncpg.Connection,
    relationship_id: UUID,
    user_id: UUID,
    bidirectional: bool = True,
) -> bool:
    """
    Delete a relationship.

    Args:
        conn: Database connection
        relationship_id: ID of the relationship to delete
        user_id: User ID
        bidirectional: If True, also deletes the inverse relationship

    Returns:
        True if deleted, False if not found
    """
    # Get the relationship details first if we need to delete bidirectionally
    if bidirectional:
        relationship_obj = await get_relationship_by_id(conn, relationship_id, user_id)
        if relationship_obj:
            # Find and delete the inverse relationship
            inverse_row = await conn.fetchrow(
                """
                SELECT id FROM relationship
                WHERE contact_id = $1 AND family_contact_id = $2
                """,
                relationship_obj.family_contact_id,
                relationship_obj.contact_id,
            )
            if inverse_row:
                await conn.fetchrow(SQL_DELETE_RELATIONSHIP, inverse_row["id"], user_id)
                logger.info(
                    "inverse_relationship_deleted",
                    relationship_id=str(inverse_row["id"]),
                )

    # Delete the primary relationship
    row = await conn.fetchrow(SQL_DELETE_RELATIONSHIP, relationship_id, user_id)

    if row is None:
        logger.warning(
            "relationship_not_found_for_delete",
            relationship_id=str(relationship_id),
            user_id=str(user_id),
        )
        return False

    logger.info(
        "relationship_deleted",
        relationship_id=str(relationship_id),
    )

    return True


async def list_contacts_for_selection(
    conn: asyncpg.Connection, user_id: UUID, exclude_contact_id: UUID
) -> list[Contact]:
    """
    List contacts available for relationship selection.

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


async def get_relationships_with_details(
    conn: asyncpg.Connection, contact_id: UUID, user_id: UUID
) -> list[RelationshipWithDetails]:
    """Get relationships with full contact details for a contact."""
    rows = await conn.fetch(SQL_RELATIONSHIPS_WITH_DETAILS, contact_id, user_id)

    relationships = [
        RelationshipWithDetails(
            id=row["id"],
            family_contact_id=row["family_contact_id"],
            relationship=row["relationship"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )
        for row in rows
    ]

    return relationships
