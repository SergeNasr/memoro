#!/usr/bin/env python3
"""
Backfill embeddings for interactions that are missing them.

Safety features:
- Fails if more than 20 interactions need embeddings (prevent massive bills)
- Shows count before processing
- Requires confirmation to proceed
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import structlog
from dotenv import load_dotenv

# Add backend to path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.llm import generate_embedding

logger = structlog.get_logger(__name__)

# Safety limit
MAX_INTERACTIONS = 20


async def get_interactions_without_embeddings(conn: asyncpg.Connection) -> list[dict]:
    """Get all interactions that are missing embeddings."""
    query = """
        SELECT id, notes
        FROM interaction
        WHERE embedding IS NULL
        ORDER BY created_at DESC
    """
    rows = await conn.fetch(query)
    return [{"id": row["id"], "notes": row["notes"]} for row in rows]


async def update_interaction_embedding(
    conn: asyncpg.Connection, interaction_id: str, embedding: list[float]
) -> None:
    """Update an interaction's embedding."""
    embedding_str = f"[{','.join(map(str, embedding))}]"
    query = """
        UPDATE interaction
        SET embedding = $1::vector
        WHERE id = $2
    """
    await conn.execute(query, embedding_str, interaction_id)


async def backfill_embeddings() -> None:
    """Main backfill function."""
    # Load environment variables
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.error("DATABASE_URL not set in environment")
        sys.exit(1)

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("OPENAI_API_KEY not set in environment")
        sys.exit(1)

    # Connect to database
    logger.info("connecting_to_database")
    conn = await asyncpg.connect(database_url)

    try:
        # Get interactions without embeddings
        interactions = await get_interactions_without_embeddings(conn)
        count = len(interactions)

        logger.info("interactions_found", count=count)

        if count == 0:
            print("✅ All interactions already have embeddings!")
            return

        if count > MAX_INTERACTIONS:
            logger.error(
                "too_many_interactions",
                count=count,
                max_allowed=MAX_INTERACTIONS,
            )
            print(f"\n❌ Found {count} interactions without embeddings.")
            print(f"   Maximum allowed: {MAX_INTERACTIONS}")
            print("\n   This safety limit prevents accidentally generating too many embeddings.")
            print("   If you really need to backfill more, update MAX_INTERACTIONS in the script.")
            sys.exit(1)

        # Show what we're about to do
        print(f"\n📊 Found {count} interaction(s) without embeddings")
        print(f"   This will use approximately {count} OpenAI API calls")
        print(f"   Estimated cost: ~$0.{count:02d} USD")
        print()

        # Ask for confirmation
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return

        # Process each interaction
        print(f"\n🚀 Processing {count} interaction(s)...")
        for i, interaction in enumerate(interactions, 1):
            interaction_id = interaction["id"]
            notes = interaction["notes"]

            logger.info(
                "generating_embedding",
                interaction_id=str(interaction_id),
                progress=f"{i}/{count}",
            )

            # Generate embedding
            embedding = await generate_embedding(notes)

            # Update in database
            await update_interaction_embedding(conn, interaction_id, embedding)

            print(f"   [{i}/{count}] ✓ {interaction_id}")

        print(f"\n✅ Successfully backfilled {count} embedding(s)!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(backfill_embeddings())
