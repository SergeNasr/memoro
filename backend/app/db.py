"""Database connection and SQL query management using asyncpg."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import structlog

from backend.app.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
_pool: asyncpg.Pool | None = None

_POOL_RETRY_ATTEMPTS = 5
_POOL_RETRY_BASE_DELAY = 2  # seconds


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Validate a connection before it's handed out from the pool."""
    await conn.execute("SELECT 1")


async def create_pool() -> asyncpg.Pool:
    """Create a new connection pool with retries for startup resilience."""
    for attempt in range(1, _POOL_RETRY_ATTEMPTS + 1):
        try:
            pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                init=_init_connection,
            )
            logger.info("database_pool_created", min_size=2, max_size=10)
            return pool
        except (
            asyncpg.ConnectionDoesNotExistError,
            asyncpg.InterfaceError,
            OSError,
        ) as exc:
            if attempt == _POOL_RETRY_ATTEMPTS:
                logger.error("database_pool_creation_failed", attempts=attempt, error=str(exc))
                raise
            delay = _POOL_RETRY_BASE_DELAY * attempt
            logger.warning(
                "database_pool_creation_retry",
                attempt=attempt,
                delay=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)


async def get_pool() -> asyncpg.Pool:
    """
    Get or create the global connection pool.

    Returns:
        asyncpg.Pool instance
    """
    global _pool
    if _pool is None:
        _pool = await create_pool()
    return _pool


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        logger.info("database_pool_closed")
        _pool = None


async def _acquire_with_retry() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection, resetting the pool once on failure."""
    global _pool
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            yield conn
    except (
        asyncpg.ConnectionDoesNotExistError,
        asyncpg.InterfaceError,
        OSError,
    ):
        logger.warning("database_connection_failed, resetting pool")
        if _pool is not None:
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None
        pool = await get_pool()
        async with pool.acquire() as conn:
            yield conn


async def get_db_dependency() -> AsyncIterator[asyncpg.Connection]:
    """
    FastAPI dependency for database connections.

    Usage in endpoint:
        async def my_endpoint(conn: asyncpg.Connection = Depends(get_db_dependency)):
            result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    """
    async for conn in _acquire_with_retry():
        yield conn


async def get_db_transaction_dependency() -> AsyncIterator[asyncpg.Connection]:
    """
    FastAPI dependency for database transactions.

    Usage in endpoint:
        async def my_endpoint(conn: asyncpg.Connection = Depends(get_db_transaction_dependency)):
            await conn.execute("INSERT INTO users ...")
    """
    async for conn in _acquire_with_retry():
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
