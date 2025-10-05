"""Contact endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.db import get_db_dependency
from backend.app.models import (
    Contact,
    ContactListResponse,
    ContactSummary,
    ContactUpdate,
    Interaction,
)
from backend.app.services import contacts as contact_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse, status_code=status.HTTP_200_OK)
async def list_contacts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of contacts per page"),
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> ContactListResponse:
    """
    List all contacts for the authenticated user with pagination.

    Returns contacts sorted alphabetically by last name, then first name.
    """
    contacts, total, total_pages = await contact_service.get_contact_list(
        conn, user_id, page, page_size
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
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Contact:
    """
    Get a single contact by ID.

    Returns the contact details if found and belongs to the authenticated user.
    Raises 404 if contact not found or doesn't belong to the user.
    """
    contact = await contact_service.get_contact_by_id(conn, contact_id, user_id)

    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return contact


@router.get("/{contact_id}/summary", response_model=ContactSummary, status_code=status.HTTP_200_OK)
async def get_contact_summary(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> ContactSummary:
    """
    Get comprehensive summary for a contact.

    Includes:
    - Contact basic information
    - Total number of interactions
    - Recent interactions (last 5)
    - Family members with details
    - Date of last interaction

    Returns 404 if contact not found or doesn't belong to the user.
    """
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    if summary is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return summary


@router.patch("/{contact_id}", response_model=Contact, status_code=status.HTTP_200_OK)
async def update_contact(
    contact_id: UUID,
    contact_update: ContactUpdate,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Contact:
    """
    Update a contact's details.

    All fields are optional. Only provided fields will be updated.
    Returns 404 if contact not found or doesn't belong to the user.
    """
    contact = await contact_service.update_contact(
        conn,
        contact_id,
        user_id,
        contact_update.first_name,
        contact_update.last_name,
        contact_update.birthday,
        contact_update.latest_news,
    )

    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> None:
    """
    Delete a contact.

    Deletes the contact and all associated interactions and family relationships.
    Returns 404 if contact not found or doesn't belong to the user.
    """
    deleted = await contact_service.delete_contact(conn, contact_id, user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.get(
    "/{contact_id}/interactions", response_model=list[Interaction], status_code=status.HTTP_200_OK
)
async def list_contact_interactions(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> list[Interaction]:
    """
    Get all interactions for a specific contact.

    Returns interactions sorted by date (most recent first).
    Returns 404 if contact not found or doesn't belong to the user.
    """
    interactions = await contact_service.get_contact_interactions(conn, contact_id, user_id)

    if interactions is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return interactions
