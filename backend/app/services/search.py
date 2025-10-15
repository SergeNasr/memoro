"""Search business logic - shared between API and UI."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import (
    SearchResult,
    SearchResultContact,
    SearchResultInteraction,
    SearchType,
)

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_FUZZY_CONTACTS = load_sql("search/fuzzy_contacts.sql")
SQL_FUZZY_INTERACTIONS = load_sql("search/fuzzy_interactions.sql")
SQL_TERM_CONTACTS = load_sql("search/term_contacts.sql")
SQL_TERM_INTERACTIONS = load_sql("search/term_interactions.sql")
SQL_SEMANTIC_INTERACTIONS = load_sql("search/semantic_interactions.sql")


async def perform_search(
    conn: asyncpg.Connection,
    user_id: UUID,
    query: str,
    search_type: SearchType,
    limit: int,
) -> list[SearchResult]:
    """
    Perform unified search across contacts and interactions.

    Supports three search types:
    - semantic: Vector similarity search on interaction embeddings
    - fuzzy: Trigram similarity matching on text fields
    - term: Basic ILIKE pattern matching

    Returns combined results sorted by relevance score.
    """
    results = []

    if search_type == SearchType.SEMANTIC:
        # Semantic search not yet implemented
        # Would require embedding service integration
        pass

    elif search_type == SearchType.FUZZY:
        # Fuzzy search on contacts
        contact_rows = await conn.fetch(SQL_FUZZY_CONTACTS, user_id, query, limit)

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
        interaction_rows = await conn.fetch(SQL_FUZZY_INTERACTIONS, user_id, query, limit)

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

    elif search_type == SearchType.TERM:
        # Term search on contacts
        contact_rows = await conn.fetch(SQL_TERM_CONTACTS, user_id, query, limit)

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
        interaction_rows = await conn.fetch(SQL_TERM_INTERACTIONS, user_id, query, limit)

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
    results = results[:limit]

    logger.info(
        "search_completed",
        user_id=str(user_id),
        query=query,
        search_type=search_type,
        total_results=len(results),
    )

    return results
