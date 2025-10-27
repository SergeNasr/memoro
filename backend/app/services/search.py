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
from backend.app.services.llm import generate_embedding

logger = structlog.get_logger(__name__)

# Load SQL queries
SQL_FUZZY_CONTACTS = load_sql("search/fuzzy_contacts.sql")
SQL_FUZZY_INTERACTIONS = load_sql("search/fuzzy_interactions.sql")
SQL_TERM_CONTACTS = load_sql("search/term_contacts.sql")
SQL_TERM_INTERACTIONS = load_sql("search/term_interactions.sql")
SQL_SEMANTIC_INTERACTIONS = load_sql("search/semantic_interactions.sql")

# Hybrid search weight configuration
HYBRID_SEARCH_WEIGHTS = {
    "semantic": 0.5,
    "fuzzy": 0.3,
    "term": 0.2,
}


def _add_or_update_score(
    interaction_scores: dict[UUID, dict],
    row: dict,
    score_key: str,
) -> None:
    """Add or update score for an interaction in hybrid search."""
    interaction_id = row["id"]
    if interaction_id not in interaction_scores:
        interaction_scores[interaction_id] = {
            "row": row,
            "fuzzy": 0.0,
            "term": 0.0,
            "semantic": 0.0,
        }
    interaction_scores[interaction_id][score_key] = float(row["score"])


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

    elif search_type == SearchType.HYBRID:
        # Delegate to hybrid search function
        return await perform_hybrid_search(conn, user_id, query, limit)

    else:
        # Unknown search type
        logger.error("unknown_search_type", search_type=search_type)
        raise ValueError(f"Unknown search type: {search_type}")

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


async def perform_hybrid_search(
    conn: asyncpg.Connection,
    user_id: UUID,
    query: str,
    limit: int,
) -> list[SearchResult]:
    """
    Perform hybrid search combining fuzzy, term, and semantic searches on interactions.

    Runs all three search types and merges results with weighted scoring:
    - Semantic: 50%
    - Fuzzy: 30%
    - Term: 20%

    Returns combined results sorted by weighted relevance score.
    """
    # Generate embedding for semantic search
    query_embedding = await generate_embedding(query)
    embedding_str = f"[{','.join(map(str, query_embedding))}]"

    # Run all three searches sequentially (asyncpg doesn't support concurrent ops on same conn)
    fuzzy_rows = await conn.fetch(SQL_FUZZY_INTERACTIONS, user_id, query, limit)
    term_rows = await conn.fetch(SQL_TERM_INTERACTIONS, user_id, query, limit)
    semantic_rows = await conn.fetch(SQL_SEMANTIC_INTERACTIONS, user_id, embedding_str, limit)

    logger.debug(
        "search_results_fetched",
        fuzzy_count=len(fuzzy_rows),
        term_count=len(term_rows),
        semantic_count=len(semantic_rows),
    )

    # Early return if no results
    if not fuzzy_rows and not term_rows and not semantic_rows:
        logger.info("hybrid_search_no_results", query=query)
        return []

    # Collect scores by interaction ID
    interaction_scores: dict[UUID, dict] = {}

    # Process all search results
    for search_type, rows in [
        ("fuzzy", fuzzy_rows),
        ("term", term_rows),
        ("semantic", semantic_rows),
    ]:
        for row in rows:
            _add_or_update_score(interaction_scores, row, search_type)

    # Calculate weighted scores and create results
    results = []
    for data in interaction_scores.values():
        weighted_score = sum(data[key] * weight for key, weight in HYBRID_SEARCH_WEIGHTS.items())

        row = data["row"]
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
                score=weighted_score,
            )
        )

    # Sort by weighted score and apply limit
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:limit]

    logger.info(
        "hybrid_search_completed",
        user_id=str(user_id),
        query=query,
        total_results=len(results),
        unique_interactions=len(interaction_scores),
    )

    return results
