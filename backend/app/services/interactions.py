"""Interaction business logic - shared between API and UI."""

from datetime import date
from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import (
    AnalyzeInteractionResponse,
    ExtractedRelationship,
    Interaction,
)
from backend.app.services.llm import (
    analyze_interaction as llm_analyze_interaction,
)
from backend.app.services.llm import (
    generate_embedding,
)

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_FIND_OR_CREATE_CONTACT = load_sql("contacts/find_or_create.sql")
SQL_UPDATE_LATEST_NEWS = load_sql("contacts/update_latest_news.sql")
SQL_CREATE_INTERACTION = load_sql("interactions/create.sql")
SQL_CREATE_RELATIONSHIP = load_sql("relationships/create.sql")
SQL_GET_INTERACTION_BY_ID = load_sql("interactions/get_by_id.sql")
SQL_UPDATE_INTERACTION = load_sql("interactions/update.sql")
SQL_DELETE_INTERACTION = load_sql("interactions/delete.sql")


async def analyze_interaction_text(text: str) -> AnalyzeInteractionResponse:
    """
    Analyze raw interaction text and extract structured information using LLM.

    Returns extracted contact, interaction, and relationship information with confidence scores.
    """
    result = await llm_analyze_interaction(text)
    return result


async def confirm_and_persist_interaction(
    conn: asyncpg.Connection,
    user_id: UUID,
    first_name: str,
    last_name: str | None,
    birthday: str | None,
    interaction_date: date | str,
    notes: str,
    location: str | None,
    relationships: list[dict[str, str]] | None = None,
) -> tuple[UUID, UUID, int]:
    """
    Confirm and persist interaction data to database.

    Creates/finds contact, creates interaction, links relationships, updates latest news.

    Returns:
        Tuple of (contact_id, interaction_id, relationships_linked)
    """
    # 1. Find or create main contact
    contact_row = await conn.fetchrow(
        SQL_FIND_OR_CREATE_CONTACT,
        user_id,
        first_name or "Unknown",
        last_name or "",
        birthday,
        notes,  # Use interaction notes as initial latest_news
    )
    contact_id = contact_row["id"]
    logger.info("contact_found_or_created", contact_id=str(contact_id))

    # 2. Generate embedding from notes
    embedding = await generate_embedding(notes)
    logger.info("embedding_generated_for_interaction", embedding_dimensions=len(embedding))

    # 3. Create interaction
    parsed_date = (
        date.fromisoformat(interaction_date)
        if isinstance(interaction_date, str)
        else interaction_date
    )
    # Convert embedding list to pgvector string format
    embedding_str = f"[{','.join(map(str, embedding))}]"
    interaction_row = await conn.fetchrow(
        SQL_CREATE_INTERACTION,
        user_id,
        contact_id,
        parsed_date,
        notes,
        location,
        embedding_str,
    )
    interaction_id = interaction_row["id"]
    logger.info("interaction_created", interaction_id=str(interaction_id))

    # 4. Update contact's latest_news with this interaction
    await conn.execute(
        SQL_UPDATE_LATEST_NEWS,
        contact_id,
        notes,
    )

    # 5. Link relationships
    relationships_list = []
    if relationships:
        for rel in relationships:
            if rel.get("first_name"):
                relationships_list.append(
                    ExtractedRelationship(
                        first_name=rel["first_name"],
                        last_name=rel.get("last_name"),
                        relationship=rel.get("relationship", ""),
                        confidence=1.0,
                    )
                )

    relationship_count = await link_relationships(
        conn, user_id, contact_id, first_name, relationships_list
    )

    logger.info(
        "interaction_confirmed",
        contact_id=str(contact_id),
        interaction_id=str(interaction_id),
        relationships_linked=relationship_count,
    )

    return contact_id, interaction_id, relationship_count


# Relationship inverse mapping - single source of truth
RELATIONSHIP_INVERSES = {
    "parent": "child",
    "child": "parent",
    "spouse": "spouse",
    "sibling": "sibling",
}


def get_inverse_relationship(relationship: str) -> str:
    """Get the inverse relationship for bidirectional links."""
    return RELATIONSHIP_INVERSES.get(relationship.lower(), "related_to")


async def link_relationships(
    conn: asyncpg.Connection,
    user_id: UUID,
    contact_id: UUID,
    contact_first_name: str | None,
    relationships: list[ExtractedRelationship],
) -> int:
    """
    Link relationships to a contact bidirectionally.

    Creates contact records for related people if they don't exist, then creates
    relationships in both directions to ensure consistent querying.

    Returns count of newly linked relationships.
    """
    relationship_count = 0
    for relationship in relationships:
        if not relationship.first_name:
            continue

        # Create or find related contact
        related_contact_row = await conn.fetchrow(
            SQL_FIND_OR_CREATE_CONTACT,
            user_id,
            relationship.first_name,
            relationship.last_name or "",
            None,  # No birthday yet
            f"Related to {contact_first_name}",
        )
        related_contact_id = related_contact_row["id"]

        # Create forward relationship (contact -> related_contact)
        forward_result = await conn.fetchrow(
            SQL_CREATE_RELATIONSHIP,
            contact_id,
            related_contact_id,
            relationship.relationship,
        )

        # Create reverse relationship (related_contact -> contact)
        inverse_relationship = get_inverse_relationship(relationship.relationship)
        reverse_result = await conn.fetchrow(
            SQL_CREATE_RELATIONSHIP,
            related_contact_id,
            contact_id,
            inverse_relationship,
        )

        # Count as linked if either relationship was created (not duplicate)
        if forward_result or reverse_result:
            relationship_count += 1
            logger.info(
                "relationship_linked_bidirectionally",
                contact_id=str(contact_id),
                related_contact_id=str(related_contact_id),
                forward_relationship=relationship.relationship,
                reverse_relationship=inverse_relationship,
                forward_created=bool(forward_result),
                reverse_created=bool(reverse_result),
            )

    return relationship_count


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
    interaction_date: date | str | None,
) -> Interaction | None:
    """
    Update an interaction's details.

    Returns None if interaction not found or doesn't belong to user.
    """
    # Generate new embedding if notes are being updated
    embedding_str = None
    if notes is not None:
        embedding = await generate_embedding(notes)
        logger.info(
            "embedding_regenerated_for_update",
            interaction_id=str(interaction_id),
            embedding_dimensions=len(embedding),
        )
        # Convert embedding list to pgvector string format
        embedding_str = f"[{','.join(map(str, embedding))}]"

    parsed_date = (
        date.fromisoformat(interaction_date)
        if isinstance(interaction_date, str)
        else interaction_date
    )
    row = await conn.fetchrow(
        SQL_UPDATE_INTERACTION,
        interaction_id,
        user_id,
        notes,
        location,
        parsed_date,
        embedding_str,
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
