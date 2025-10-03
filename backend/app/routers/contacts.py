"""Contact endpoints."""

import math
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.db import get_db_connection, load_sql
from backend.app.models import Contact, ContactListResponse, ContactUpdate, Interaction

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

# Load SQL queries
SQL_LIST_CONTACTS = load_sql("contacts/list.sql")
SQL_COUNT_CONTACTS = load_sql("contacts/count.sql")
SQL_GET_CONTACT_BY_ID = load_sql("contacts/get_by_id.sql")
SQL_UPDATE_CONTACT = load_sql("contacts/update.sql")
SQL_DELETE_CONTACT = load_sql("contacts/delete.sql")
SQL_LIST_INTERACTIONS_BY_CONTACT = load_sql("interactions/list_by_contact.sql")


@router.get("", response_model=ContactListResponse, status_code=status.HTTP_200_OK)
async def list_contacts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of contacts per page"),
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> ContactListResponse:
    """
    List all contacts for the authenticated user with pagination.

    Returns contacts sorted alphabetically by last name, then first name.
    """
    offset = (page - 1) * page_size

    async with get_db_connection() as conn:
        # Get total count
        count_row = await conn.fetchrow(SQL_COUNT_CONTACTS, user_id)
        total = count_row["total"]

        # Get paginated contacts
        rows = await conn.fetch(SQL_LIST_CONTACTS, user_id, page_size, offset)

        contacts = [
            Contact(
                id=row["id"],
                user_id=row["user_id"],
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

        return ContactListResponse(
            contacts=contacts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/{contact_id}", response_model=Contact, status_code=status.HTTP_200_OK)
async def get_contact(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> Contact:
    """
    Get a single contact by ID.

    Returns the contact details if found and belongs to the authenticated user.
    Raises 404 if contact not found or doesn't belong to the user.
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(SQL_GET_CONTACT_BY_ID, contact_id, user_id)

        if row is None:
            logger.warning("contact_not_found", contact_id=str(contact_id), user_id=str(user_id))
            raise HTTPException(status_code=404, detail="Contact not found")

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


@router.patch("/{contact_id}", response_model=Contact, status_code=status.HTTP_200_OK)
async def update_contact(
    contact_id: UUID,
    contact_update: ContactUpdate,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> Contact:
    """
    Update a contact's details.

    All fields are optional. Only provided fields will be updated.
    Returns 404 if contact not found or doesn't belong to the user.
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            SQL_UPDATE_CONTACT,
            contact_id,
            user_id,
            contact_update.first_name,
            contact_update.last_name,
            contact_update.birthday,
            contact_update.latest_news,
        )

        if row is None:
            logger.warning("contact_not_found_for_update", contact_id=str(contact_id), user_id=str(user_id))
            raise HTTPException(status_code=404, detail="Contact not found")

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


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> None:
    """
    Delete a contact.

    Deletes the contact and all associated interactions and family relationships.
    Returns 404 if contact not found or doesn't belong to the user.
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(SQL_DELETE_CONTACT, contact_id, user_id)

        if row is None:
            logger.warning("contact_not_found_for_delete", contact_id=str(contact_id), user_id=str(user_id))
            raise HTTPException(status_code=404, detail="Contact not found")

        logger.info("contact_deleted", contact_id=str(contact_id), user_id=str(user_id))


@router.get("/{contact_id}/interactions", response_model=list[Interaction], status_code=status.HTTP_200_OK)
async def list_contact_interactions(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> list[Interaction]:
    """
    Get all interactions for a specific contact.

    Returns interactions sorted by date (most recent first).
    Returns 404 if contact not found or doesn't belong to the user.
    """
    async with get_db_connection() as conn:
        # First verify contact exists and belongs to user
        contact_row = await conn.fetchrow(SQL_GET_CONTACT_BY_ID, contact_id, user_id)

        if contact_row is None:
            logger.warning("contact_not_found_for_interactions", contact_id=str(contact_id), user_id=str(user_id))
            raise HTTPException(status_code=404, detail="Contact not found")

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
