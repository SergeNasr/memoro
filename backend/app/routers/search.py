"""Search endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth import get_authenticated_user
from backend.app.db import get_db_dependency
from backend.app.models import SearchRequest, SearchResponse
from backend.app.services import search as search_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    search_request: SearchRequest,
    user_id: UUID = Depends(get_authenticated_user),
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> SearchResponse:
    """
    Unified search endpoint for contacts and interactions.

    Supports four search types:
    - semantic: Vector similarity search on interaction embeddings
    - fuzzy: Trigram similarity matching on text fields
    - term: Basic ILIKE pattern matching
    - hybrid: Combines fuzzy, term, and semantic with weighted scoring

    Returns combined results from contacts and interactions, sorted by relevance.
    """
    if search_request.search_type == "hybrid":
        results = await search_service.perform_hybrid_search(
            conn, user_id, search_request.query, search_request.limit
        )
    elif search_request.search_type == "semantic":
        raise HTTPException(
            status_code=501,
            detail="Semantic search not yet implemented - requires embedding service integration",
        )
    else:
        results = await search_service.perform_search(
            conn, user_id, search_request.query, search_request.search_type, search_request.limit
        )

    return SearchResponse(
        results=results,
        query=search_request.query,
        search_type=search_request.search_type,
        total_results=len(results),
    )
