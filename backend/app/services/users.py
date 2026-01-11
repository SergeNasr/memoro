"""User service for user lookup and creation."""

from uuid import UUID

import asyncpg
import structlog

from backend.app.db import load_sql

logger = structlog.get_logger(__name__)

SQL_GET_OR_CREATE_BY_FIREBASE_UID = load_sql("users/get_or_create_by_firebase_uid.sql")


async def get_or_create_user_by_firebase_uid(
    conn: asyncpg.Connection, firebase_uid: str, email: str
) -> UUID:
    """
    Get or create a user by Firebase UID.

    If user with firebase_uid exists, returns their internal UUID.
    If not, creates a new user and returns the new UUID.

    Args:
        conn: Database connection
        firebase_uid: Firebase user ID string
        email: User's email from Firebase token

    Returns:
        Internal UUID for the user
    """
    # Execute the multi-statement SQL (INSERT ... ON CONFLICT, then SELECT)
    row = await conn.fetchrow(SQL_GET_OR_CREATE_BY_FIREBASE_UID, firebase_uid, email)

    if not row:
        logger.error("user_creation_failed", firebase_uid=firebase_uid, email=email)
        raise ValueError("Failed to get or create user")

    user_id = row["id"]
    logger.debug("user_resolved", firebase_uid=firebase_uid, user_id=str(user_id))
    return user_id
