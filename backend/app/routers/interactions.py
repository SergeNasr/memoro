"""Interaction endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.models import (
    AnalyzeInteractionRequest,
    AnalyzeInteractionResponse,
    ConfirmInteractionRequest,
    ConfirmInteractionResponse,
    Interaction,
    InteractionUpdate,
)
from backend.app.services import interactions as interaction_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


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
    result = await interaction_service.analyze_interaction_text(request.text)
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
    (
        contact_id,
        interaction_id,
        family_count,
    ) = await interaction_service.confirm_and_persist_interaction(conn, user_id, request)

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
    interaction = await interaction_service.get_interaction_by_id(conn, interaction_id, user_id)

    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")

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
    interaction = await interaction_service.update_interaction(
        conn,
        interaction_id,
        user_id,
        interaction_update.notes,
        interaction_update.location,
        interaction_update.interaction_date,
    )

    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")

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
    deleted = await interaction_service.delete_interaction(conn, interaction_id, user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Interaction not found")
