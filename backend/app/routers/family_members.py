"""Family member endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db import get_db_dependency
from backend.app.models import Contact, FamilyMember, FamilyMemberCreate
from backend.app.services import family_members as family_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/family-members", tags=["family-members"])


@router.post("", response_model=FamilyMember, status_code=status.HTTP_201_CREATED)
async def create_family_member(
    family_member: FamilyMemberCreate,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> FamilyMember:
    """
    Create a new family member relationship.

    Creates a bidirectional relationship between two contacts.
    """
    result = await family_service.create_family_member_relationship(
        conn,
        user_id,
        family_member.contact_id,
        family_member.family_contact_id,
        family_member.relationship,
        bidirectional=True,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create relationship (may already exist or be invalid)",
        )

    return result


@router.get("/{family_member_id}", response_model=FamilyMember, status_code=status.HTTP_200_OK)
async def get_family_member(
    family_member_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> FamilyMember:
    """Get a family member relationship by ID."""
    family_member = await family_service.get_family_member_by_id(conn, family_member_id, user_id)

    if family_member is None:
        raise HTTPException(status_code=404, detail="Family member relationship not found")

    return family_member


@router.patch("/{family_member_id}", response_model=FamilyMember, status_code=status.HTTP_200_OK)
async def update_family_member(
    family_member_id: UUID,
    relationship: str,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> FamilyMember:
    """
    Update a family member relationship type.

    Note: Only updates one direction of the relationship.
    """
    family_member = await family_service.update_family_member_relationship(
        conn, family_member_id, user_id, relationship
    )

    if family_member is None:
        raise HTTPException(status_code=404, detail="Family member relationship not found")

    return family_member


@router.delete("/{family_member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_member(
    family_member_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> None:
    """
    Delete a family member relationship.

    Deletes both directions of the relationship.
    """
    deleted = await family_service.delete_family_member_relationship(
        conn, family_member_id, user_id, bidirectional=True
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Family member relationship not found")


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
    List contacts available for family member selection.

    Returns all user's contacts except the specified contact.
    """
    contacts = await family_service.list_contacts_for_selection(conn, user_id, contact_id)
    return contacts
