"""Interaction business logic - shared between API and UI."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import (
    AnalyzeInteractionResponse,
    ConfirmInteractionRequest,
    ExtractedFamilyMember,
    Interaction,
)
from backend.app.services.llm import analyze_interaction as llm_analyze_interaction

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_FIND_OR_CREATE_CONTACT = load_sql("contacts/find_or_create.sql")
SQL_UPDATE_LATEST_NEWS = load_sql("contacts/update_latest_news.sql")
SQL_CREATE_INTERACTION = load_sql("interactions/create.sql")
SQL_CREATE_FAMILY_MEMBER = load_sql("family_members/create.sql")
SQL_GET_INTERACTION_BY_ID = load_sql("interactions/get_by_id.sql")
SQL_UPDATE_INTERACTION = load_sql("interactions/update.sql")
SQL_DELETE_INTERACTION = load_sql("interactions/delete.sql")


async def analyze_interaction_text(text: str) -> AnalyzeInteractionResponse:
    """
    Analyze raw interaction text and extract structured information using LLM.

    Returns extracted contact, interaction, and family member information with confidence scores.
    """
    result = await llm_analyze_interaction(text)
    return result


async def confirm_and_persist_interaction(
    conn: asyncpg.Connection, user_id: UUID, request: ConfirmInteractionRequest
) -> tuple[UUID, UUID, int]:
    """
    Confirm and persist analyzed interaction data to database.

    Creates/finds contact, creates interaction, links family members, updates latest news.

    Returns:
        Tuple of (contact_id, interaction_id, family_members_linked)
    """
    # 1. Find or create main contact
    contact_row = await conn.fetchrow(
        SQL_FIND_OR_CREATE_CONTACT,
        user_id,
        request.contact.first_name or "Unknown",
        request.contact.last_name or "",
        request.contact.birthday,
        request.interaction.notes,  # Use interaction notes as initial latest_news
    )
    contact_id = contact_row["id"]
    logger.info("contact_found_or_created", contact_id=str(contact_id))

    # 2. Create interaction
    interaction_row = await conn.fetchrow(
        SQL_CREATE_INTERACTION,
        user_id,
        contact_id,
        request.interaction.interaction_date,
        request.interaction.notes,
        request.interaction.location,
        None,  # embedding - will be added later
    )
    interaction_id = interaction_row["id"]
    logger.info("interaction_created", interaction_id=str(interaction_id))

    # 3. Update contact's latest_news with this interaction
    await conn.execute(
        SQL_UPDATE_LATEST_NEWS,
        contact_id,
        request.interaction.notes,
    )

    # 4. Link family members
    family_count = await link_family_members(
        conn, user_id, contact_id, request.contact.first_name, request.family_members
    )

    logger.info(
        "interaction_confirmed",
        contact_id=str(contact_id),
        interaction_id=str(interaction_id),
        family_members_linked=family_count,
    )

    return contact_id, interaction_id, family_count


# Relationship inverse mapping - single source of truth
RELATIONSHIP_INVERSES = {
    "parent": "child",
    "child": "parent",
    "spouse": "spouse",
    "sibling": "sibling",
}


def get_inverse_relationship(relationship: str) -> str:
    """Get the inverse relationship for bidirectional family links."""
    return RELATIONSHIP_INVERSES.get(relationship.lower(), "related_to")


async def link_family_members(
    conn: asyncpg.Connection,
    user_id: UUID,
    contact_id: UUID,
    contact_first_name: str | None,
    family_members: list[ExtractedFamilyMember],
) -> int:
    """
    Link family members to a contact bidirectionally.

    Creates contact records for family members if they don't exist, then creates
    relationships in both directions to ensure consistent querying.

    Returns count of newly linked family members.
    """
    family_count = 0
    for family_member in family_members:
        if not family_member.first_name:
            continue

        # Create or find family member contact
        family_contact_row = await conn.fetchrow(
            SQL_FIND_OR_CREATE_CONTACT,
            user_id,
            family_member.first_name,
            family_member.last_name or "",
            None,  # No birthday for family members yet
            f"Family member of {contact_first_name}",
        )
        family_contact_id = family_contact_row["id"]

        # Create forward relationship (contact -> family_member)
        forward_result = await conn.fetchrow(
            SQL_CREATE_FAMILY_MEMBER,
            contact_id,
            family_contact_id,
            family_member.relationship,
        )

        # Create reverse relationship (family_member -> contact)
        inverse_relationship = get_inverse_relationship(family_member.relationship)
        reverse_result = await conn.fetchrow(
            SQL_CREATE_FAMILY_MEMBER,
            family_contact_id,
            contact_id,
            inverse_relationship,
        )

        # Count as linked if either relationship was created (not duplicate)
        if forward_result or reverse_result:
            family_count += 1
            logger.info(
                "family_member_linked_bidirectionally",
                contact_id=str(contact_id),
                family_contact_id=str(family_contact_id),
                forward_relationship=family_member.relationship,
                reverse_relationship=inverse_relationship,
                forward_created=bool(forward_result),
                reverse_created=bool(reverse_result),
            )

    return family_count


async def get_interaction_by_id(
    conn: asyncpg.Connection, interaction_id: UUID, user_id: UUID
) -> Interaction | None:
    """
    Get a single interaction by ID.

    Returns None if interaction not found or doesn't belong to user.
    """
    row = await conn.fetchrow(SQL_GET_INTERACTION_BY_ID, interaction_id, user_id)

    if row is None:
        logger.warning(
            "interaction_not_found", interaction_id=str(interaction_id), user_id=str(user_id)
        )
        return None

    interaction = Interaction(
        id=row["id"],
        user_id=user_id,
        contact_id=row["contact_id"],
        interaction_date=row["interaction_date"],
        notes=row["notes"],
        location=row["location"],
    )

    logger.info("interaction_retrieved", interaction_id=str(interaction_id), user_id=str(user_id))

    return interaction


async def update_interaction(
    conn: asyncpg.Connection,
    interaction_id: UUID,
    user_id: UUID,
    notes: str | None,
    location: str | None,
    interaction_date: str | None,
) -> Interaction | None:
    """
    Update an interaction's details.

    Returns None if interaction not found or doesn't belong to user.
    """
    row = await conn.fetchrow(
        SQL_UPDATE_INTERACTION,
        interaction_id,
        user_id,
        notes,
        location,
        interaction_date,
    )

    if row is None:
        logger.warning(
            "interaction_not_found_for_update",
            interaction_id=str(interaction_id),
            user_id=str(user_id),
        )
        return None

    interaction = Interaction(
        id=row["id"],
        user_id=user_id,
        contact_id=row["contact_id"],
        interaction_date=row["interaction_date"],
        notes=row["notes"],
        location=row["location"],
    )

    logger.info("interaction_updated", interaction_id=str(interaction_id), user_id=str(user_id))

    return interaction


async def delete_interaction(conn: asyncpg.Connection, interaction_id: UUID, user_id: UUID) -> bool:
    """
    Delete an interaction.

    Returns True if deleted, False if not found or doesn't belong to user.
    """
    row = await conn.fetchrow(SQL_DELETE_INTERACTION, interaction_id, user_id)

    if row is None:
        logger.warning(
            "interaction_not_found_for_delete",
            interaction_id=str(interaction_id),
            user_id=str(user_id),
        )
        return False

    logger.info("interaction_deleted", interaction_id=str(interaction_id), user_id=str(user_id))

    return True
