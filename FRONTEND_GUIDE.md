# Frontend Implementation Guide

## What's Done ✅

### Structure
- `backend/app/static/css/style.css` - Complete retro styling
- `backend/app/static/js/shortcuts.js` - Keyboard shortcuts working
- `backend/app/templates/base.html` - Base layout with HTMX
- `backend/app/templates/index.html` - Homepage example
- `backend/app/templates/components/contact_list.html` - Component example
- `backend/app/routers/ui.py` - UI router with 3 example endpoints
- `backend/app/main.py` - Router registered, static files mounted

### Working Endpoints
1. `GET /` - Homepage (contact list)
2. `GET /contacts/{id}` - Contact profile (needs template)
3. `GET /ui/contacts/list` - Contact list fragment for pagination

## What's Needed 📋

### 1. Templates to Create

#### `templates/contact_profile.html`
```html
{% extends "base.html" %}
{% block content %}
<!-- Show summary.contact info -->
<!-- Show summary.recent_interactions -->
<!-- Show summary.family_members -->
<!-- "Load more" button for older interactions -->
{% endblock %}
```

#### `templates/components/` (more components)
- `search_results.html` - Search results fragment
- `review_form.html` - LLM extraction review/edit form
- `interaction_card.html` - Single interaction display
- `404.html` - Not found page

### 2. UI Endpoints to Add in `routers/ui.py`

```python
@router.get("/ui/search", response_class=HTMLResponse)
async def search_ui(request: Request, q: str, ...):
    """Returns search results HTML fragment"""
    # Use search_service.perform_search()
    # Return templates.TemplateResponse("components/search_results.html", ...)

@router.post("/ui/interactions/analyze", response_class=HTMLResponse)
async def analyze_interaction_ui(request: Request, text: str = Form(...), ...):
    """Analyze interaction and return review form"""
    # Use interaction_service.analyze_interaction_text()
    # Return templates.TemplateResponse("components/review_form.html", ...)

@router.post("/ui/interactions/confirm", response_class=HTMLResponse)
async def confirm_interaction_ui(request: Request, ...):
    """Confirm interaction and close modal"""
    # Use interaction_service.confirm_and_persist_interaction()
    # Return success response that triggers modal close + refresh

@router.get("/ui/contacts/{contact_id}/interactions", response_class=HTMLResponse)
async def load_more_interactions(request: Request, contact_id: UUID, ...):
    """Load more interactions for a contact"""
    # Use contact_service.get_contact_interactions()
    # Return templates.TemplateResponse("components/interaction_list.html", ...)

@router.patch("/ui/interactions/{interaction_id}", response_class=HTMLResponse)
async def update_interaction_ui(request: Request, interaction_id: UUID, ...):
    """Update interaction inline"""
    # Use interaction_service.update_interaction()
    # Return updated interaction card

@router.delete("/ui/interactions/{interaction_id}", response_class=HTMLResponse)
async def delete_interaction_ui(interaction_id: UUID, ...):
    """Delete interaction"""
    # Use interaction_service.delete_interaction()
    # Return empty response (HTMX will swap with nothing)
```

### 3. HTMX Patterns to Use

**Search (realtime)**
```html
<input
    hx-get="/ui/search"
    hx-trigger="keyup changed delay:300ms"
    hx-target="#results"
>
```

**Form submission**
```html
<form
    hx-post="/ui/interactions/analyze"
    hx-target="#review-form"
    hx-indicator=".loader"
>
```

**Delete with confirmation**
```html
<button
    hx-delete="/ui/interactions/{id}"
    hx-confirm="Delete this interaction?"
    hx-target="closest .interaction-item"
    hx-swap="outerHTML"
>
```

**Load more**
```html
<button
    hx-get="/ui/contacts/{id}/interactions"
    hx-target="#interactions-list"
    hx-swap="beforeend"
>Load more</button>
```

## Key Patterns

### 1. Service Reuse
```python
# Always use services - ZERO duplication
from backend.app.services import contacts as contact_service

contacts, total, pages = await contact_service.get_contact_list(...)
```

### 2. Template Response
```python
return templates.TemplateResponse(
    "template.html",
    {"request": request, "data": data}
)
```

### 3. Form Data
```python
from fastapi import Form

@router.post("/endpoint")
async def endpoint(text: str = Form(...)):
    # Handle form data
```

## Testing

```bash
# Start database
docker-compose up -d

# Run migrations
just db-migrate

# Start dev server
just dev

# Visit http://localhost:8000
# Should see homepage with empty state
```

## Styling Tips

All classes are in `static/css/style.css`:
- `.contact-item` - Contact in list
- `.interaction-item` - Interaction card
- `.btn`, `.btn-primary` - Buttons
- `.modal-overlay`, `.modal` - Modal
- `.form-group` - Form field
- `.loader` - ASCII spinner (shown during htmx-request)
- `.empty-state` - Empty states

## Next Steps

1. Create `templates/contact_profile.html`
2. Add remaining endpoints in `routers/ui.py`
3. Create component templates as needed
4. Test each feature
5. Commit and push
6. Create PR

The foundation is solid - just fill in the templates and endpoints following the patterns shown!
