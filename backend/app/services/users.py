"""User service for user lookup."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql

logger = structlog.get_logger(__name__)

SQL_GET_USER_BY_FIREBASE_UID = load_sql("users/get_by_firebase_uid.sql")


async def get_user_by_firebase_uid(conn: asyncpg.Connection, firebase_uid: str) -> UUID:
    """
    Get user by Firebase UID.

    Args:
        conn: Database connection
        firebase_uid: Firebase user ID string

    Returns:
        Internal UUID for the user

    Raises:
        ValueError: If no user found with this firebase_uid
    """
    row = await conn.fetchrow(SQL_GET_USER_BY_FIREBASE_UID, firebase_uid)

    if not row:
        logger.error("user_not_found", firebase_uid=firebase_uid)
        raise ValueError("User not found")

    user_id = row["id"]
    logger.debug("user_resolved", firebase_uid=firebase_uid, user_id=str(user_id))
    return user_id
