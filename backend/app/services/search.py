"""Search business logic - shared between API and UI."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql
from backend.app.models import (
    SearchResult,
    SearchResultContact,
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


async def _fetch_search_results_by_contact_id(
    conn: asyncpg.Connection,
    sql: str,
    *args,
) -> dict[UUID, asyncpg.Record]:
    """
    Execute a search query and return results as a dictionary mapping contact_id -> row.

    All search queries return contact_id, so this helper consolidates the pattern.

    Raises ValueError if duplicate contact_ids are found in the results.
    """
    rows = await conn.fetch(sql, *args)

    # Check for duplicate contact_ids
    contact_ids = [row["contact_id"] for row in rows]
    seen = set()
    duplicates = []
    for contact_id in contact_ids:
        if contact_id in seen:
            duplicates.append(str(contact_id))
        seen.add(contact_id)

    if duplicates:
        logger.error(
            "duplicate_contact_ids_found",
            duplicate_count=len(duplicates),
            total_rows=len(rows),
            duplicates=duplicates[:10],  # Log first 10 duplicates
        )
        raise ValueError(
            f"Found {len(duplicates)} duplicate contact_id(s) in search results. "
            f"Each contact_id should appear only once. First duplicate(s): {', '.join(duplicates[:5])}"
        )

    return {row["contact_id"]: row for row in rows}


async def perform_search(
    conn: asyncpg.Connection,
    user_id: UUID,
    query: str,
    limit: int,
) -> list[SearchResult]:
    """
    Perform unified search across contacts and interactions.

    Combines fuzzy, term, and semantic searches with weighted scoring:
    - Fuzzy: 30% (applied to contacts and interactions)
    - Term: 20% (applied to contacts and interactions)
    - Semantic: 50% (applied to interactions only)

    Returns combined results sorted by weighted relevance score, deduplicated by contact_id.
    """
    query_embedding = await generate_embedding(query)
    embedding_str = f"[{','.join(map(str, query_embedding))}]"

    # Execute all searches
    contact_fuzzy = await _fetch_search_results_by_contact_id(
        conn, SQL_FUZZY_CONTACTS, user_id, query, limit
    )
    interaction_fuzzy = await _fetch_search_results_by_contact_id(
        conn, SQL_FUZZY_INTERACTIONS, user_id, query, limit
    )
    contact_term = await _fetch_search_results_by_contact_id(
        conn, SQL_TERM_CONTACTS, user_id, query, limit
    )
    interaction_term = await _fetch_search_results_by_contact_id(
        conn, SQL_TERM_INTERACTIONS, user_id, query, limit
    )
    interaction_semantic = await _fetch_search_results_by_contact_id(
        conn, SQL_SEMANTIC_INTERACTIONS, user_id, embedding_str, limit
    )

    # Collect all unique contact IDs
    all_contact_ids = set()
    all_contact_ids.update(contact_fuzzy.keys())
    all_contact_ids.update(interaction_fuzzy.keys())
    all_contact_ids.update(contact_term.keys())
    all_contact_ids.update(interaction_term.keys())
    all_contact_ids.update(interaction_semantic.keys())

    # Combine results
    results = []
    for contact_id in all_contact_ids:
        # Get contact row, preferring contact queries over interaction queries
        contact_row = (
            contact_fuzzy.get(contact_id)
            or contact_term.get(contact_id)
            or interaction_fuzzy.get(contact_id)
            or interaction_term.get(contact_id)
            or interaction_semantic.get(contact_id)
        )

        # Compute weighted combined score
        combined_score = 0.0
        if contact_id in contact_fuzzy:
            combined_score += contact_fuzzy[contact_id]["score"] * HYBRID_SEARCH_WEIGHTS["fuzzy"]
        if contact_id in interaction_fuzzy:
            combined_score += (
                interaction_fuzzy[contact_id]["score"] * HYBRID_SEARCH_WEIGHTS["fuzzy"]
            )
        if contact_id in contact_term:
            combined_score += contact_term[contact_id]["score"] * HYBRID_SEARCH_WEIGHTS["term"]
        if contact_id in interaction_term:
            combined_score += interaction_term[contact_id]["score"] * HYBRID_SEARCH_WEIGHTS["term"]
        if contact_id in interaction_semantic:
            combined_score += (
                interaction_semantic[contact_id]["score"] * HYBRID_SEARCH_WEIGHTS["semantic"]
            )

        # Create SearchResult
        results.append(
            SearchResult(
                contact=SearchResultContact(
                    id=contact_id,
                    first_name=contact_row["first_name"],
                    last_name=contact_row["last_name"],
                    birthday=contact_row["birthday"],
                    latest_news=contact_row["latest_news"],
                ),
                score=combined_score,
            )
        )

    # Sort by weighted score and apply limit
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:limit]

    logger.info(
        "search_completed",
        user_id=str(user_id),
        query=query,
        total_results=len(results),
    )

    return results
