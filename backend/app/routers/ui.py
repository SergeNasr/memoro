"""UI routes - HTML-serving endpoints for HTMX frontend."""

from datetime import date
from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.app.constants import TemplateConstants
from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.models import (
    AnalyzeInteractionRequest,
    ConfirmInteractionRequest,
    ExtractedContact,
    ExtractedFamilyMember,
    ExtractedInteraction,
    SearchRequest,
    SearchType,
)
from backend.app.services import contacts as contact_service
from backend.app.services import interactions as interaction_service
from backend.app.services import search as search_service

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
            "constants": TemplateConstants,
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
            "contact_name": summary.contact.first_name,
            "constants": TemplateConstants,
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


@router.get("/ui/search", response_class=HTMLResponse)
async def search_ui(
    request: Request,
    q: str = "",
    search_type: SearchType = SearchType.FUZZY,
    limit: int = 20,
    # TODO: Add user authentication and get user_id from session
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Search UI endpoint - returns search results HTML fragment.
    Used by HTMX for dynamic search.
    """
    if not q.strip():
        return templates.TemplateResponse(
            "components/search_results.html",
            {
                "request": request,
                "results": [],
                "query": "",
                "search_type": search_type,
                "total_results": 0,
                "constants": TemplateConstants,
            },
        )

    # Create search request
    search_request = SearchRequest(
        query=q.strip(),
        search_type=search_type,
        limit=limit,
    )

    # Perform search
    results = await search_service.perform_search(conn, user_id, search_request)

    return templates.TemplateResponse(
        "components/search_results.html",
        {
            "request": request,
            "results": results,
            "query": q,
            "search_type": search_type,
            "total_results": len(results),
            "constants": TemplateConstants,
        },
    )


@router.post("/ui/interactions/analyze", response_class=HTMLResponse)
async def analyze_interaction_ui(
    request: Request,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Analyze raw interaction text and return review form HTML fragment.
    Used by HTMX from the new interaction modal.
    If contact_id is provided, contact info will be pre-filled from database.
    """
    form_data = await request.form()

    # Parse form data into request model
    analyze_request = AnalyzeInteractionRequest(
        text=form_data.get("text"),
        contact_id=UUID(form_data.get("contact_id")) if form_data.get("contact_id") else None,
    )

    analysis = await interaction_service.analyze_interaction_text(analyze_request.text)

    # Override with provided contact if available
    if analyze_request.contact_id:
        contact = await contact_service.get_contact_by_id(conn, analyze_request.contact_id, user_id)
        if contact:
            analysis.contact.first_name = contact.first_name
            analysis.contact.last_name = contact.last_name
            analysis.contact.birthday = contact.birthday
            analysis.contact.confidence = 1.0

    return templates.TemplateResponse(
        "components/review_form.html",
        {
            "request": request,
            "analysis": analysis,
            "contact_id": analyze_request.contact_id,
        },
    )


@router.post("/ui/interactions/confirm")
async def confirm_interaction_ui(
    request: Request,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_transaction_dependency),
):
    """
    Confirm and persist interaction from review form.
    Parses form data and redirects to contact profile on success.
    """
    form_data = await request.form()

    # Parse contact data
    contact = ExtractedContact(
        first_name=form_data.get("contact.first_name"),
        last_name=form_data.get("contact.last_name") or None,
        birthday=date.fromisoformat(form_data.get("contact.birthday"))
        if form_data.get("contact.birthday")
        else None,
        confidence=1.0,
    )

    # Parse interaction data
    interaction = ExtractedInteraction(
        interaction_date=date.fromisoformat(form_data.get("interaction.interaction_date")),
        notes=form_data.get("interaction.notes"),
        location=form_data.get("interaction.location") or None,
        confidence=1.0,
    )

    # Parse family members
    family_members = []
    idx = 0
    while True:
        first_name_key = f"family_members[{idx}].first_name"
        if first_name_key not in form_data:
            break

        first_name = form_data.get(first_name_key)
        if first_name:
            family_members.append(
                ExtractedFamilyMember(
                    first_name=first_name,
                    last_name=form_data.get(f"family_members[{idx}].last_name") or None,
                    relationship=form_data.get(f"family_members[{idx}].relationship", ""),
                    confidence=1.0,
                )
            )
        idx += 1

    # Create request and persist
    confirm_request = ConfirmInteractionRequest(
        contact=contact,
        interaction=interaction,
        family_members=family_members,
    )

    (
        contact_id,
        interaction_id,
        family_count,
    ) = await interaction_service.confirm_and_persist_interaction(conn, user_id, confirm_request)

    logger.info(
        "interaction_confirmed_via_ui",
        contact_id=str(contact_id),
        interaction_id=str(interaction_id),
        family_members_linked=family_count,
    )

    # Redirect to contact profile
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.get("/ui/interactions/{interaction_id}", response_class=HTMLResponse)
async def get_interaction_fragment(
    request: Request,
    interaction_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns a single interaction HTML fragment (read-only view).
    Used by HTMX to cancel edit mode.
    """
    interaction = await interaction_service.get_interaction_by_id(conn, interaction_id, user_id)

    if interaction is None:
        return HTMLResponse(content="<div>Interaction not found</div>", status_code=404)

    return templates.TemplateResponse(
        "components/interaction_list.html",
        {
            "request": request,
            "interactions": [interaction],
        },
    )


@router.get("/ui/interactions/{interaction_id}/edit", response_class=HTMLResponse)
async def get_interaction_edit_form(
    request: Request,
    interaction_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns inline edit form for an interaction.
    Used by HTMX for in-place editing.
    """
    interaction = await interaction_service.get_interaction_by_id(conn, interaction_id, user_id)

    if interaction is None:
        return HTMLResponse(content="<div>Interaction not found</div>", status_code=404)

    return templates.TemplateResponse(
        "components/interaction_edit.html",
        {
            "request": request,
            "interaction": interaction,
        },
    )


@router.patch("/ui/interactions/{interaction_id}", response_class=HTMLResponse)
async def update_interaction_ui(
    request: Request,
    interaction_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Update an interaction and return the updated HTML fragment.
    Used by HTMX for in-place updates.
    """
    form_data = await request.form()

    # Parse form data
    interaction_date = date.fromisoformat(form_data.get("interaction_date"))
    location = form_data.get("location") or None
    notes = form_data.get("notes")

    # Update interaction
    interaction = await interaction_service.update_interaction(
        conn,
        interaction_id,
        user_id,
        notes,
        location,
        interaction_date,
    )

    if interaction is None:
        return HTMLResponse(content="<div>Interaction not found</div>", status_code=404)

    logger.info(
        "interaction_updated_via_ui",
        interaction_id=str(interaction_id),
        user_id=str(user_id),
    )

    # Return updated interaction fragment
    return templates.TemplateResponse(
        "components/interaction_list.html",
        {
            "request": request,
            "interactions": [interaction],
        },
    )


@router.delete("/ui/interactions/{interaction_id}", response_class=HTMLResponse)
async def delete_interaction_ui(
    request: Request,
    interaction_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Delete an interaction and return updated interaction list.
    Used by HTMX to remove interaction from the list.
    """
    # Get interaction first to get contact_id
    interaction = await interaction_service.get_interaction_by_id(conn, interaction_id, user_id)

    if interaction is None:
        return HTMLResponse(content="<div>Interaction not found</div>", status_code=404)

    contact_id = interaction.contact_id

    # Delete the interaction
    deleted = await interaction_service.delete_interaction(conn, interaction_id, user_id)

    if not deleted:
        return HTMLResponse(content="<div>Failed to delete interaction</div>", status_code=500)

    logger.info(
        "interaction_deleted_via_ui",
        interaction_id=str(interaction_id),
        contact_id=str(contact_id),
        user_id=str(user_id),
    )

    # Get updated interaction list for this contact
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    if summary is None:
        return HTMLResponse(content="", status_code=200)

    # Return updated interaction list
    return templates.TemplateResponse(
        "components/interaction_list.html",
        {
            "request": request,
            "interactions": summary.recent_interactions,
        },
    )


# TODO: Add more UI endpoints:
# - GET /ui/contacts/{contact_id}/interactions - Returns more interactions fragment (pagination)
