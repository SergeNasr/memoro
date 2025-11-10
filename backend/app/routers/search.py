"""Search endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, status

from backend.app.auth import get_current_user
from backend.app.db import get_db_dependency
from backend.app.models import SearchRequest, SearchResponse
from backend.app.services import search as search_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    search_request: SearchRequest,
    user_id: UUID = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> SearchResponse:
    """
    Unified search endpoint for contacts and interactions.

    Uses hybrid search which combines fuzzy, term, and semantic searches with weighted scoring.

    Returns combined results from contacts and interactions, sorted by relevance.
    """
    results = await search_service.perform_search(
        conn, user_id, search_request.query, search_request.limit
    )

    return SearchResponse(
        results=results,
        query=search_request.query,
        total_results=len(results),
    )
