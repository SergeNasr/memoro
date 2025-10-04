"""Search endpoints."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db import get_db_dependency, load_sql
from backend.app.models import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultContact,
    SearchResultInteraction,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# Load SQL queries
SQL_FUZZY_CONTACTS = load_sql("search/fuzzy_contacts.sql")
SQL_FUZZY_INTERACTIONS = load_sql("search/fuzzy_interactions.sql")
SQL_TERM_CONTACTS = load_sql("search/term_contacts.sql")
SQL_TERM_INTERACTIONS = load_sql("search/term_interactions.sql")
SQL_SEMANTIC_INTERACTIONS = load_sql("search/semantic_interactions.sql")


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    search_request: SearchRequest,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
    conn: asyncpg.Connection = Depends(get_db_dependency),
) -> SearchResponse:
    """
    Unified search endpoint for contacts and interactions.

    Supports three search types:
    - semantic: Vector similarity search on interaction embeddings
    - fuzzy: Trigram similarity matching on text fields
    - term: Basic ILIKE pattern matching

    Returns combined results from contacts and interactions, sorted by relevance.
    """
    results = []

    if search_request.search_type == "semantic":
        # Semantic search only works on interactions with embeddings
        # For now, we'll need an embedding service to generate query embedding
        # TODO: Integrate with embedding service
        raise HTTPException(
            status_code=501,
            detail="Semantic search not yet implemented - requires embedding service integration",
        )

    elif search_request.search_type == "fuzzy":
        # Fuzzy search on contacts
        contact_rows = await conn.fetch(
            SQL_FUZZY_CONTACTS, user_id, search_request.query, search_request.limit
        )

        for row in contact_rows:
            results.append(
                SearchResult(
                    result_type="contact",
                    contact=SearchResultContact(
                        id=row["id"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        birthday=row["birthday"],
                        latest_news=row["latest_news"],
                    ),
                    score=float(row["score"]),
                )
            )

        # Fuzzy search on interactions
        interaction_rows = await conn.fetch(
            SQL_FUZZY_INTERACTIONS, user_id, search_request.query, search_request.limit
        )

        for row in interaction_rows:
            results.append(
                SearchResult(
                    result_type="interaction",
                    interaction=SearchResultInteraction(
                        id=row["id"],
                        contact_id=row["contact_id"],
                        interaction_date=row["interaction_date"],
                        notes=row["notes"],
                        location=row["location"],
                        contact_first_name=row["contact_first_name"],
                        contact_last_name=row["contact_last_name"],
                    ),
                    score=float(row["score"]),
                )
            )

    elif search_request.search_type == "term":
        # Term search on contacts
        contact_rows = await conn.fetch(
            SQL_TERM_CONTACTS, user_id, search_request.query, search_request.limit
        )

        for row in contact_rows:
            results.append(
                SearchResult(
                    result_type="contact",
                    contact=SearchResultContact(
                        id=row["id"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        birthday=row["birthday"],
                        latest_news=row["latest_news"],
                    ),
                    score=float(row["score"]),
                )
            )

        # Term search on interactions
        interaction_rows = await conn.fetch(
            SQL_TERM_INTERACTIONS, user_id, search_request.query, search_request.limit
        )

        for row in interaction_rows:
            results.append(
                SearchResult(
                    result_type="interaction",
                    interaction=SearchResultInteraction(
                        id=row["id"],
                        contact_id=row["contact_id"],
                        interaction_date=row["interaction_date"],
                        notes=row["notes"],
                        location=row["location"],
                        contact_first_name=row["contact_first_name"],
                        contact_last_name=row["contact_last_name"],
                    ),
                    score=float(row["score"]),
                )
            )

    # Sort all results by score (descending) and limit to requested amount
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[: search_request.limit]

    logger.info(
        "search_completed",
        user_id=str(user_id),
        query=search_request.query,
        search_type=search_request.search_type,
        total_results=len(results),
    )

    return SearchResponse(
        results=results,
        query=search_request.query,
        search_type=search_request.search_type,
        total_results=len(results),
    )
