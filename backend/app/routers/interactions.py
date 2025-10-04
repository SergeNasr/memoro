"""Interaction endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db import get_db_dependency, get_db_transaction_dependency, load_sql
from backend.app.models import (
    AnalyzeInteractionRequest,
    AnalyzeInteractionResponse,
    ConfirmInteractionRequest,
    ConfirmInteractionResponse,
    Interaction,
    InteractionUpdate,
)
from backend.app.services.llm import analyze_interaction

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/interactions", tags=["interactions"])

# Load SQL queries
SQL_FIND_OR_CREATE_CONTACT = load_sql("contacts/find_or_create.sql")
SQL_UPDATE_LATEST_NEWS = load_sql("contacts/update_latest_news.sql")
SQL_CREATE_INTERACTION = load_sql("interactions/create.sql")
SQL_CREATE_FAMILY_MEMBER = load_sql("family_members/create.sql")
SQL_LIST_INTERACTIONS_BY_CONTACT = load_sql("interactions/list_by_contact.sql")
SQL_GET_INTERACTION_BY_ID = load_sql("interactions/get_by_id.sql")
SQL_UPDATE_INTERACTION = load_sql("interactions/update.sql")
SQL_DELETE_INTERACTION = load_sql("interactions/delete.sql")


@router.post("/analyze", response_model=AnalyzeInteractionResponse, status_code=status.HTTP_200_OK)
async def analyze_interaction_endpoint(
    request: AnalyzeInteractionRequest,
) -> AnalyzeInteractionResponse:
    """
    Analyze raw interaction text and extract structured information.

    This endpoint uses LLM to extract:
    - Contact information (name, birthday)
    - Interaction details (notes, location, date)
    - Family members mentioned

    Each extracted field includes a confidence score.
    """
    result = await analyze_interaction(request.text)
    return result


@router.post(
    "/confirm", response_model=ConfirmInteractionResponse, status_code=status.HTTP_201_CREATED
)
async def confirm_interaction_endpoint(
    request: ConfirmInteractionRequest,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_transaction_dependency),
) -> ConfirmInteractionResponse:
    """
    Confirm and persist analyzed interaction data to database.

    This endpoint:
    - Creates or finds existing contact
    - Creates interaction record with notes, location, date
    - Links family members (creates contacts for them too)
    - Updates contact's latest_news field

    Returns IDs of created/found entities.
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
    family_count = 0
    for family_member in request.family_members:
        if not family_member.first_name:
            continue

        # Create or find family member contact
        family_contact_row = await conn.fetchrow(
            SQL_FIND_OR_CREATE_CONTACT,
            user_id,
            family_member.first_name,
            family_member.last_name or "",
            None,  # No birthday for family members yet
            f"Family member of {request.contact.first_name}",
        )
        family_contact_id = family_contact_row["id"]

        # Create family relationship
        result = await conn.fetchrow(
            SQL_CREATE_FAMILY_MEMBER,
            contact_id,
            family_contact_id,
            family_member.relationship,
        )

        if result:  # Only count if relationship was created (not duplicate)
            family_count += 1
            logger.info(
                "family_member_linked",
                contact_id=str(contact_id),
                family_contact_id=str(family_contact_id),
                relationship=family_member.relationship,
            )

    logger.info(
        "interaction_confirmed",
        contact_id=str(contact_id),
        interaction_id=str(interaction_id),
        family_members_linked=family_count,
    )

    return ConfirmInteractionResponse(
        contact_id=contact_id,
        interaction_id=interaction_id,
        family_members_linked=family_count,
    )


@router.get("/{interaction_id}", response_model=Interaction, status_code=status.HTTP_200_OK)
async def get_interaction(
    interaction_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Interaction:
    """
    Get a single interaction by ID.

    Returns the interaction details if found and belongs to the authenticated user.
    Raises 404 if interaction not found or doesn't belong to the user.
    """
    row = await conn.fetchrow(SQL_GET_INTERACTION_BY_ID, interaction_id, user_id)

    if row is None:
        logger.warning(
            "interaction_not_found", interaction_id=str(interaction_id), user_id=str(user_id)
        )
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction = Interaction(
        id=row["id"],
        user_id=row["user_id"],
        contact_id=row["contact_id"],
        interaction_date=row["interaction_date"],
        notes=row["notes"],
        location=row["location"],
    )

    logger.info("interaction_retrieved", interaction_id=str(interaction_id), user_id=str(user_id))

    return interaction


@router.patch("/{interaction_id}", response_model=Interaction, status_code=status.HTTP_200_OK)
async def update_interaction(
    interaction_id: UUID,
    interaction_update: InteractionUpdate,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> Interaction:
    """
    Update an interaction's details.

    All fields are optional. Only provided fields will be updated.
    Returns 404 if interaction not found or doesn't belong to the user.
    """
    row = await conn.fetchrow(
        SQL_UPDATE_INTERACTION,
        interaction_id,
        user_id,
        interaction_update.notes,
        interaction_update.location,
        interaction_update.interaction_date,
    )

    if row is None:
        logger.warning(
            "interaction_not_found_for_update",
            interaction_id=str(interaction_id),
            user_id=str(user_id),
        )
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction = Interaction(
        id=row["id"],
        user_id=row["user_id"],
        contact_id=row["contact_id"],
        interaction_date=row["interaction_date"],
        notes=row["notes"],
        location=row["location"],
    )

    logger.info("interaction_updated", interaction_id=str(interaction_id), user_id=str(user_id))

    return interaction


@router.delete("/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interaction(
    interaction_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> None:
    """
    Delete an interaction.

    Returns 404 if interaction not found or doesn't belong to the user.
    """
    row = await conn.fetchrow(SQL_DELETE_INTERACTION, interaction_id, user_id)

    if row is None:
        logger.warning(
            "interaction_not_found_for_delete",
            interaction_id=str(interaction_id),
            user_id=str(user_id),
        )
        raise HTTPException(status_code=404, detail="Interaction not found")

    logger.info("interaction_deleted", interaction_id=str(interaction_id), user_id=str(user_id))
