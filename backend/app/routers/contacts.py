"""Contact endpoints."""

import math
from uuid import UUID

import structlog
from fastapi import APIRouter, Query, status

from backend.app.db import get_db_connection, load_sql
from backend.app.models import Contact, ContactListResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

# Load SQL queries
SQL_LIST_CONTACTS = load_sql("contacts/list.sql")
SQL_COUNT_CONTACTS = load_sql("contacts/count.sql")


@router.get("", response_model=ContactListResponse, status_code=status.HTTP_200_OK)
async def list_contacts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of contacts per page"),
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
) -> ContactListResponse:
    """
    List all contacts for the authenticated user with pagination.

    Returns contacts sorted alphabetically by last name, then first name.
    """
    offset = (page - 1) * page_size

    async with get_db_connection() as conn:
        # Get total count
        count_row = await conn.fetchrow(SQL_COUNT_CONTACTS, user_id)
        total = count_row["total"]

        # Get paginated contacts
        rows = await conn.fetch(SQL_LIST_CONTACTS, user_id, page_size, offset)

        contacts = [
            Contact(
                id=row["id"],
                user_id=row["user_id"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                birthday=row["birthday"],
                latest_news=row["latest_news"],
            )
            for row in rows
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        logger.info(
            "contacts_listed",
            user_id=str(user_id),
            page=page,
            page_size=page_size,
            total=total,
            returned=len(contacts),
        )

        return ContactListResponse(
            contacts=contacts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
