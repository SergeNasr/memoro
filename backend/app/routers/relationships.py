"""Relationship endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db import get_db_dependency
from backend.app.models import Contact, Relationship, RelationshipCreate
from backend.app.services import relationships as relationship_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("", response_model=Relationship, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    relationship: RelationshipCreate,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Relationship:
    """
    Create a new relationship.

    Creates a bidirectional relationship between two contacts.
    """
    result = await relationship_service.create_relationship(
        conn,
        user_id,
        relationship.contact_id,
        relationship.family_contact_id,
        relationship.relationship,
        bidirectional=True,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create relationship (may already exist or be invalid)",
        )

    return result


@router.get("/{relationship_id}", response_model=Relationship, status_code=status.HTTP_200_OK)
async def get_relationship(
    relationship_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Relationship:
    """Get a relationship by ID."""
    relationship = await relationship_service.get_relationship_by_id(conn, relationship_id, user_id)

    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return relationship


@router.patch("/{relationship_id}", response_model=Relationship, status_code=status.HTTP_200_OK)
async def update_relationship(
    relationship_id: UUID,
    relationship_type: str,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Relationship:
    """
    Update a relationship type.

    Note: Only updates one direction of the relationship.
    """
    relationship = await relationship_service.update_relationship(
        conn, relationship_id, user_id, relationship_type
    )

    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return relationship


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    relationship_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> None:
    """
    Delete a relationship.

    Deletes both directions of the relationship.
    """
    deleted = await relationship_service.delete_relationship(
        conn, relationship_id, user_id, bidirectional=True
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")


@router.get(
    "/contacts/{contact_id}/available",
    response_model=list[Contact],
    status_code=status.HTTP_200_OK,
)
async def list_available_contacts(
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> list[Contact]:
    """
    List contacts available for relationship selection.

    Returns all user's contacts except the specified contact.
    """
    contacts = await relationship_service.list_contacts_for_selection(conn, user_id, contact_id)
    return contacts
