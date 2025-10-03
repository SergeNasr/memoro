"""Database connection and SQL query management using asyncpg."""

from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import structlog

from backend.app.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Get or create the global connection pool.

    Returns:
        asyncpg.Pool instance
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("database_pool_created", min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        logger.info("database_pool_closed")
        _pool = None


async def get_db_dependency() -> AsyncIterator[asyncpg.Connection]:
    """
    FastAPI dependency for database connections.

    Usage in endpoint:
        async def my_endpoint(conn: asyncpg.Connection = Depends(get_db_dependency)):
            result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_db_transaction_dependency() -> AsyncIterator[asyncpg.Connection]:
    """
    FastAPI dependency for database transactions.

    Usage in endpoint:
        async def my_endpoint(conn: asyncpg.Connection = Depends(get_db_transaction_dependency)):
            await conn.execute("INSERT INTO users ...")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn


def load_sql(filename: str) -> str:
    """
    Load SQL query from file.

    Args:
        filename: Path relative to backend/app/sql/ directory

    Returns:
        SQL query string

    Raises:
        FileNotFoundError: If SQL file doesn't exist
    """
    sql_dir = Path(__file__).parent / "sql"
    sql_path = sql_dir / filename

    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    return sql_path.read_text()
