"""UI routes - HTML-serving endpoints for HTMX frontend."""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.app.db import get_db_dependency
from backend.app.services import contacts as contact_service

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["ui"])

# Set up Jinja2 templates
templates = Jinja2Templates(directory="backend/app/templates")


@router.get("/", response_class=HTMLResponse)
async def homepage(
    request: Request,
    page: int = 1,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Homepage - displays contact list with search and pagination.
    """
    page_size = 20
    contacts, total, total_pages = await contact_service.get_contact_list(
        conn, user_id, page, page_size
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "contacts": contacts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    )


@router.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def contact_profile(
    request: Request,
    contact_id: UUID,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Contact profile page - displays contact summary with interactions.
    """
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    if summary is None:
        # Return 404 page or redirect
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    return templates.TemplateResponse(
        "contact_profile.html",
        {
            "request": request,
            "summary": summary,
        },
    )


# Example HTMX endpoint - returns HTML fragment
@router.get("/ui/contacts/list", response_class=HTMLResponse)
async def get_contact_list_fragment(
    request: Request,
    page: int = 1,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns contact list HTML fragment for pagination.
    Used by HTMX for dynamic loading.
    """
    page_size = 20
    contacts, total, total_pages = await contact_service.get_contact_list(
        conn, user_id, page, page_size
    )

    return templates.TemplateResponse(
        "components/contact_list.html",
        {
            "request": request,
            "contacts": contacts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    )


# TODO: Add more UI endpoints:
# - POST /ui/interactions/analyze - Returns review form fragment
# - GET /ui/search - Returns search results fragment
# - GET /ui/contacts/{contact_id}/interactions - Returns more interactions fragment
# - PATCH /ui/interactions/{interaction_id} - Inline edit form
# - DELETE /ui/interactions/{interaction_id} - Delete and return updated list
