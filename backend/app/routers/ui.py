"""UI routes - HTML-serving endpoints for HTMX frontend."""

from datetime import date
from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.app.constants import TemplateConstants
from backend.app.db import get_db_dependency, get_db_transaction_dependency
from backend.app.models import SearchType
from backend.app.services import contacts as contact_service
from backend.app.services import interactions as interaction_service
from backend.app.services import relationships as relationship_service
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
    page_size = 50
    contacts, total, total_pages = await contact_service.get_contact_list(
        conn, user_id, page, page_size
    )

    return templates.TemplateResponse(
        request,
        "index.html",
        {
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
        return templates.TemplateResponse(request, "404.html", status_code=404)

    return templates.TemplateResponse(
        request,
        "contact_profile.html",
        {
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
    page_size = 50
    contacts, total, total_pages = await contact_service.get_contact_list(
        conn, user_id, page, page_size
    )

    return templates.TemplateResponse(
        request,
        "components/contact_list.html",
        {
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
    search_type: SearchType = SearchType.HYBRID,
    limit: int = 20,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Search UI endpoint - returns search results HTML fragment.
    Used by HTMX for dynamic search.
    """
    if not q.strip():
        return templates.TemplateResponse(
            request,
            "components/search_results.html",
            {
                "results": [],
                "query": "",
                "search_type": search_type,
                "total_results": 0,
                "constants": TemplateConstants,
            },
        )

    results = await search_service.perform_search(conn, user_id, q.strip(), search_type, limit)

    return templates.TemplateResponse(
        request,
        "components/search_results.html",
        {
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
    text: str = Form(..., min_length=1),
    contact_id: UUID | None = Form(None),
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Analyze raw interaction text and return review form HTML fragment.
    Used by HTMX from the new interaction modal.
    If contact_id is provided, contact info will be pre-filled from database.
    """
    analysis = await interaction_service.analyze_interaction_text(text)

    # Override with provided contact if available
    if contact_id:
        contact = await contact_service.get_contact_by_id(conn, contact_id, user_id)
        if contact:
            analysis.contact.first_name = contact.first_name
            analysis.contact.last_name = contact.last_name
            analysis.contact.birthday = contact.birthday
            analysis.contact.confidence = 1.0

    return templates.TemplateResponse(
        request,
        "components/review_form.html",
        {
            "analysis": analysis,
            "contact_id": contact_id,
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

    # Parse relationships
    relationships = []
    idx = 0
    while True:
        first_name_key = f"relationships[{idx}].first_name"
        if first_name_key not in form_data:
            break

        first_name = form_data.get(first_name_key)
        if first_name:
            relationships.append(
                {
                    "first_name": first_name,
                    "last_name": form_data.get(f"relationships[{idx}].last_name") or None,
                    "relationship": form_data.get(f"relationships[{idx}].relationship", ""),
                }
            )
        idx += 1

    (
        contact_id,
        interaction_id,
        relationship_count,
    ) = await interaction_service.confirm_and_persist_interaction(
        conn,
        user_id,
        first_name=form_data.get("contact.first_name"),
        last_name=form_data.get("contact.last_name") or None,
        birthday=form_data.get("contact.birthday") or None,
        interaction_date=form_data.get("interaction.interaction_date"),
        notes=form_data.get("interaction.notes"),
        location=form_data.get("interaction.location") or None,
        relationships=relationships if relationships else None,
    )

    logger.info(
        "interaction_confirmed_via_ui",
        contact_id=str(contact_id),
        interaction_id=str(interaction_id),
        relationships_linked=relationship_count,
    )

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
        request,
        "components/interaction_list.html",
        {
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
        request,
        "components/interaction_edit.html",
        {
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
        request,
        "components/interaction_list.html",
        {
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
        request,
        "components/interaction_list.html",
        {
            "interactions": summary.recent_interactions,
        },
    )


@router.get("/ui/contacts/{contact_id}/header", response_class=HTMLResponse)
async def get_contact_header(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns contact header HTML fragment (read-only view).
    Used by HTMX to cancel edit mode.
    """
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    if summary is None:
        return HTMLResponse(content="<div>Contact not found</div>", status_code=404)

    return templates.TemplateResponse(
        request,
        "components/contact_header.html",
        {
            "contact": summary.contact,
            "total_interactions": summary.total_interactions,
            "last_interaction_date": summary.last_interaction_date,
        },
    )


@router.get("/ui/contacts/{contact_id}/edit", response_class=HTMLResponse)
async def get_contact_edit_form(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns inline edit form for a contact.
    Used by HTMX for in-place editing.
    """
    contact = await contact_service.get_contact_by_id(conn, contact_id, user_id)

    if contact is None:
        return HTMLResponse(content="<div>Contact not found</div>", status_code=404)

    return templates.TemplateResponse(
        request,
        "components/contact_edit.html",
        {
            "contact": contact,
        },
    )


@router.patch("/ui/contacts/{contact_id}", response_class=HTMLResponse)
async def update_contact_ui(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Update a contact and return the updated HTML fragment.
    Used by HTMX for in-place updates.
    """
    form_data = await request.form()

    birthday_str = form_data.get("birthday")
    birthday = date.fromisoformat(birthday_str) if birthday_str else None

    # Use the form-specific update that treats empty strings as NULL for optional fields
    contact = await contact_service.update_contact_from_form(
        conn,
        contact_id,
        user_id,
        first_name=form_data.get("first_name", ""),
        last_name=form_data.get("last_name", ""),
        birthday=birthday,
        latest_news=form_data.get("latest_news", ""),
    )

    if contact is None:
        return HTMLResponse(content="<div>Contact not found</div>", status_code=404)

    logger.info(
        "contact_updated_via_ui",
        contact_id=str(contact_id),
        user_id=str(user_id),
    )

    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    return templates.TemplateResponse(
        request,
        "components/contact_header.html",
        {
            "contact": contact,
            "total_interactions": summary.total_interactions if summary else 0,
            "last_interaction_date": summary.last_interaction_date if summary else None,
        },
    )


@router.get("/ui/contacts/{contact_id}/delete", response_class=HTMLResponse)
async def get_delete_contact_modal(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Render delete confirmation modal for a contact.
    Shows contact name and number of interactions that will be deleted.
    """
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)

    if not summary:
        return HTMLResponse(content="<div>Contact not found</div>", status_code=404)

    return templates.TemplateResponse(
        request,
        "components/contact_delete_modal.html",
        {
            "contact": summary.contact,
            "total_interactions": summary.total_interactions,
        },
    )


@router.delete("/ui/contacts/{contact_id}", response_class=HTMLResponse)
async def delete_contact_ui(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Delete a contact and redirect to home page.
    """
    deleted = await contact_service.delete_contact(conn, contact_id, user_id)

    if not deleted:
        return HTMLResponse(content="<div>Failed to delete contact</div>", status_code=500)

    logger.info(
        "contact_deleted_via_ui",
        contact_id=str(contact_id),
        user_id=str(user_id),
    )

    return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/"})


@router.get("/ui/contacts/{contact_id}/relationships/new", response_class=HTMLResponse)
async def get_new_relationship_form(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns form to add a new relationship.
    """
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)
    if summary is None:
        return HTMLResponse(content="<div>Contact not found</div>", status_code=404)

    contacts = await relationship_service.list_contacts_for_selection(conn, user_id, contact_id)

    return templates.TemplateResponse(
        request,
        "components/relationship_new.html",
        {
            "contact": summary.contact,
            "available_contacts": contacts,
            "common_relationships": [
                "parent",
                "child",
                "spouse",
                "partner",
                "sibling",
                "grandparent",
                "grandchild",
                "aunt/uncle",
                "niece/nephew",
                "cousin",
                "friend",
            ],
        },
    )


@router.post("/ui/contacts/{contact_id}/relationships", response_class=HTMLResponse)
async def create_relationship_ui(
    request: Request,
    contact_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Create a new relationship and return updated relationship list.
    """
    form_data = await request.form()

    related_contact_id_str = form_data.get("related_contact_id")
    relationship_type = form_data.get("relationship")

    if not related_contact_id_str or not relationship_type:
        return HTMLResponse(
            content="<div>Contact and relationship are required</div>", status_code=400
        )

    try:
        related_contact_id = UUID(related_contact_id_str)
    except ValueError:
        return HTMLResponse(content="<div>Invalid contact ID</div>", status_code=400)

    relationship = await relationship_service.create_relationship(
        conn, user_id, contact_id, related_contact_id, relationship_type, bidirectional=True
    )

    if relationship is None:
        return HTMLResponse(
            content="<div>Could not create relationship (may already exist)</div>", status_code=400
        )

    logger.info(
        "relationship_created_via_ui",
        contact_id=str(contact_id),
        related_contact_id=str(related_contact_id),
        relationship=relationship_type,
    )

    # Return updated relationship list
    summary = await contact_service.get_contact_summary(conn, contact_id, user_id)
    if summary is None:
        return HTMLResponse(content="", status_code=200)

    return templates.TemplateResponse(
        request,
        "components/relationship_list.html",
        {
            "contact": summary.contact,
            "relationships": summary.relationships,
        },
    )


@router.get("/ui/relationships/{relationship_id}/edit", response_class=HTMLResponse)
async def get_relationship_edit_form(
    request: Request,
    relationship_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Returns inline edit form for a relationship.
    """
    relationship = await relationship_service.get_relationship_by_id(conn, relationship_id, user_id)

    if relationship is None:
        return HTMLResponse(content="<div>Relationship not found</div>", status_code=404)

    # Get contact details for display
    relationships = await relationship_service.get_relationships_with_details(
        conn, relationship.contact_id, user_id
    )

    # Find the specific relationship with details
    relationship_details = next((r for r in relationships if r.id == relationship_id), None)

    if relationship_details is None:
        return HTMLResponse(content="<div>Relationship not found</div>", status_code=404)

    return templates.TemplateResponse(
        request,
        "components/relationship_edit.html",
        {
            "relationship": relationship_details,
            "common_relationships": [
                "parent",
                "child",
                "spouse",
                "partner",
                "sibling",
                "grandparent",
                "grandchild",
                "aunt/uncle",
                "niece/nephew",
                "cousin",
                "friend",
            ],
        },
    )


@router.patch("/ui/relationships/{relationship_id}", response_class=HTMLResponse)
async def update_relationship_ui(
    request: Request,
    relationship_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Update a relationship and return the updated HTML fragment.
    """
    form_data = await request.form()
    relationship_type = form_data.get("relationship")

    if not relationship_type:
        return HTMLResponse(content="<div>Relationship is required</div>", status_code=400)

    relationship = await relationship_service.update_relationship(
        conn, relationship_id, user_id, relationship_type
    )

    if relationship is None:
        return HTMLResponse(content="<div>Relationship not found</div>", status_code=404)

    logger.info(
        "relationship_updated_via_ui",
        relationship_id=str(relationship_id),
        new_relationship=relationship_type,
    )

    # Get updated relationship details
    relationships = await relationship_service.get_relationships_with_details(
        conn, relationship.contact_id, user_id
    )

    relationship_details = next((r for r in relationships if r.id == relationship_id), None)

    if relationship_details is None:
        return HTMLResponse(content="<div>Relationship not found</div>", status_code=404)

    # Return updated relationship item
    return templates.TemplateResponse(
        request,
        "components/relationship_item.html",
        {
            "member": relationship_details,
        },
    )


@router.delete("/ui/relationships/{relationship_id}", response_class=HTMLResponse)
async def delete_relationship_ui(
    request: Request,
    relationship_id: UUID,
    user_id: UUID = UUID("00000000-0000-0000-0000-000000000000"),
    conn: asyncpg.Connection = Depends(get_db_dependency),
):
    """
    Delete a relationship and return updated relationship list.
    """
    # Get relationship first to get contact_id
    relationship = await relationship_service.get_relationship_by_id(conn, relationship_id, user_id)

    if relationship is None:
        return HTMLResponse(content="<div>Relationship not found</div>", status_code=404)

    contact_id = relationship.contact_id

    # Delete the relationship
    deleted = await relationship_service.delete_relationship(
        conn, relationship_id, user_id, bidirectional=True
    )

    if not deleted:
        return HTMLResponse(content="<div>Failed to delete relationship</div>", status_code=500)

    logger.info(
        "relationship_deleted_via_ui",
        relationship_id=str(relationship_id),
        contact_id=str(contact_id),
    )

    # Return empty content with success
    return HTMLResponse(content="", status_code=200)
