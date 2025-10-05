"""Contact business logic - shared between API and UI."""

import math
from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import (
    Contact,
    ContactSummary,
    FamilyMemberWithDetails,
    Interaction,
)

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_LIST_CONTACTS = load_sql("contacts/list.sql")
SQL_COUNT_CONTACTS = load_sql("contacts/count.sql")
SQL_GET_CONTACT_BY_ID = load_sql("contacts/get_by_id.sql")
SQL_UPDATE_CONTACT = load_sql("contacts/update.sql")
SQL_DELETE_CONTACT = load_sql("contacts/delete.sql")
SQL_LIST_INTERACTIONS_BY_CONTACT = load_sql("interactions/list_by_contact.sql")
SQL_COUNT_INTERACTIONS = load_sql("contacts/count_interactions.sql")
SQL_RECENT_INTERACTIONS = load_sql("contacts/recent_interactions.sql")
SQL_FAMILY_MEMBERS_WITH_DETAILS = load_sql("contacts/family_members_with_details.sql")
SQL_LAST_INTERACTION_DATE = load_sql("contacts/last_interaction_date.sql")


async def get_contact_list(
    conn: asyncpg.Connection, user_id: UUID, page: int, page_size: int
) -> tuple[list[Contact], int, int]:
    """
    Get paginated list of contacts for a user.

    Returns:
        Tuple of (contacts, total_count, total_pages)
    """
    offset = (page - 1) * page_size

    # Get total count
    count_row = await conn.fetchrow(SQL_COUNT_CONTACTS, user_id)
    total = count_row["total"]

    # Get paginated contacts
    rows = await conn.fetch(SQL_LIST_CONTACTS, user_id, page_size, offset)

    contacts = [
        Contact(
            id=row["id"],
            user_id=user_id,
            first_name=row["first_name"],
            last_name=row["last_name"],
            birthday=row["birthday"],
            latest_news=row["latest_news"],
        )
        for row in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    logger.info(
        "contacts_listed",
        user_id=str(user_id),
        page=page,
        page_size=page_size,
        total=total,
        returned=len(contacts),
    )

    return contacts, total, total_pages


async def get_contact_by_id(
    conn: asyncpg.Connection, contact_id: UUID, user_id: UUID
) -> Contact | None:
    """
    Get a single contact by ID.

    Returns None if contact not found or doesn't belong to user.
    """
    row = await conn.fetchrow(SQL_GET_CONTACT_BY_ID, contact_id, user_id)

    if row is None:
        logger.warning("contact_not_found", contact_id=str(contact_id), user_id=str(user_id))
        return None

    contact = Contact(
        id=row["id"],
        user_id=row["user_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        birthday=row["birthday"],
        latest_news=row["latest_news"],
    )

    logger.info("contact_retrieved", contact_id=str(contact_id), user_id=str(user_id))

    return contact


async def get_contact_summary(
    conn: asyncpg.Connection, contact_id: UUID, user_id: UUID
) -> ContactSummary | None:
    """
    Get comprehensive summary for a contact.

    Includes contact info, interaction count, recent interactions, family members, last interaction date.
    Returns None if contact not found or doesn't belong to user.
    """
    # 1. Get contact basic info
    contact_row = await conn.fetchrow(SQL_GET_CONTACT_BY_ID, contact_id, user_id)

    if contact_row is None:
        logger.warning(
            "contact_not_found_for_summary", contact_id=str(contact_id), user_id=str(user_id)
        )
        return None

    contact = Contact(
        id=contact_row["id"],
        user_id=contact_row["user_id"],
        first_name=contact_row["first_name"],
        last_name=contact_row["last_name"],
        birthday=contact_row["birthday"],
        latest_news=contact_row["latest_news"],
    )

    # 2. Get total interaction count
    count_row = await conn.fetchrow(SQL_COUNT_INTERACTIONS, contact_id, user_id)
    total_interactions = count_row["total"] if count_row else 0

    # 3. Get recent interactions
    recent_rows = await conn.fetch(SQL_RECENT_INTERACTIONS, contact_id, user_id)
    recent_interactions = [
        Interaction(
            id=row["id"],
            user_id=row["user_id"],
            contact_id=row["contact_id"],
            interaction_date=row["interaction_date"],
            notes=row["notes"],
            location=row["location"],
        )
        for row in recent_rows
    ]

    # 4. Get family members with details
    family_rows = await conn.fetch(SQL_FAMILY_MEMBERS_WITH_DETAILS, contact_id, user_id)
    family_members = [
        FamilyMemberWithDetails(
            id=row["id"],
            family_contact_id=row["family_contact_id"],
            relationship=row["relationship"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )
        for row in family_rows
    ]

    # 5. Get last interaction date
    last_date_row = await conn.fetchrow(SQL_LAST_INTERACTION_DATE, contact_id, user_id)
    last_interaction_date = last_date_row["last_interaction_date"] if last_date_row else None

    summary = ContactSummary(
        contact=contact,
        total_interactions=total_interactions,
        recent_interactions=recent_interactions,
        family_members=family_members,
        last_interaction_date=last_interaction_date,
    )

    logger.info(
        "contact_summary_retrieved",
        contact_id=str(contact_id),
        user_id=str(user_id),
        total_interactions=total_interactions,
        family_members_count=len(family_members),
    )

    return summary


async def update_contact(
    conn: asyncpg.Connection,
    contact_id: UUID,
    user_id: UUID,
    first_name: str | None,
    last_name: str | None,
    birthday: str | None,
    latest_news: str | None,
) -> Contact | None:
    """
    Update a contact's details.

    Returns None if contact not found or doesn't belong to user.
    """
    row = await conn.fetchrow(
        SQL_UPDATE_CONTACT,
        contact_id,
        user_id,
        first_name,
        last_name,
        birthday,
        latest_news,
    )

    if row is None:
        logger.warning(
            "contact_not_found_for_update", contact_id=str(contact_id), user_id=str(user_id)
        )
        return None

    contact = Contact(
        id=row["id"],
        user_id=row["user_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        birthday=row["birthday"],
        latest_news=row["latest_news"],
    )

    logger.info("contact_updated", contact_id=str(contact_id), user_id=str(user_id))

    return contact


async def delete_contact(conn: asyncpg.Connection, contact_id: UUID, user_id: UUID) -> bool:
    """
    Delete a contact.

    Returns True if deleted, False if not found or doesn't belong to user.
    """
    row = await conn.fetchrow(SQL_DELETE_CONTACT, contact_id, user_id)

    if row is None:
        logger.warning(
            "contact_not_found_for_delete", contact_id=str(contact_id), user_id=str(user_id)
        )
        return False

    logger.info("contact_deleted", contact_id=str(contact_id), user_id=str(user_id))

    return True


async def get_contact_interactions(
    conn: asyncpg.Connection, contact_id: UUID, user_id: UUID
) -> list[Interaction] | None:
    """
    Get all interactions for a specific contact.

    Returns None if contact doesn't exist, empty list if no interactions.
    """
    # First verify contact exists and belongs to user
    contact_row = await conn.fetchrow(SQL_GET_CONTACT_BY_ID, contact_id, user_id)

    if contact_row is None:
        logger.warning(
            "contact_not_found_for_interactions",
            contact_id=str(contact_id),
            user_id=str(user_id),
        )
        return None

    # Fetch interactions
    rows = await conn.fetch(SQL_LIST_INTERACTIONS_BY_CONTACT, contact_id, user_id)

    interactions = [
        Interaction(
            id=row["id"],
            user_id=user_id,
            contact_id=row["contact_id"],
            interaction_date=row["interaction_date"],
            notes=row["notes"],
            location=row["location"],
        )
        for row in rows
    ]

    logger.info(
        "interactions_listed_for_contact",
        contact_id=str(contact_id),
        user_id=str(user_id),
        count=len(interactions),
    )

    return interactions
