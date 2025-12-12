# Memoro - Architecture & Technical Decisions

## Project Overview
Memoro is a personal CRM for tracking daily interactions with people in your life. It records names, birthdays, locations, latest news, family members, and supports semantic search for finding context.

## Core Requirements
- Record daily interactions with contacts
- Store contact details: names, birthdays, locations, news/updates, family members
- Semantic search based on context
- Look up latest recorded context for someone
- Web-based application
- Google OAuth login
- Cloud-agnostic deployment (starting with Digital Ocean)

## Implemented Features

### ✅ Currently Available

**Web UI (HTMX):**
- 🏠 **GET /** - Homepage with contact list and search
- 👤 **GET /contacts/{id}** - Contact profile with interactions
- 🔍 **GET /ui/search** - Dynamic search (fuzzy/semantic/term)
- 📄 **GET /ui/contacts/list** - Paginated contact list fragment
- 🗑️ **GET /ui/contacts/{id}/delete** - Render delete confirmation modal for a contact
- 🗑️ **DELETE /ui/contacts/{id}** - Delete contact and redirect to home page
- 🤖 **POST /ui/interactions/analyze** - Analyze interaction text and return review form
- 💾 **POST /ui/interactions/confirm** - Persist interaction and redirect to contact profile
- 📖 **GET /ui/interactions/{id}** - Get single interaction fragment (read-only view)
- ✏️ **GET /ui/interactions/{id}/edit** - Get inline edit form for interaction
- ✏️ **PATCH /ui/interactions/{id}** - Update interaction and return updated fragment
- 🗑️ **DELETE /ui/interactions/{id}** - Delete interaction and return updated list
- 👨‍👩‍👧 **GET /ui/relationships/{id}** - Get relationship item view (for canceling edit)
- 🚫 **GET /ui/contacts/{id}/relationships/cancel** - Cancel new relationship form

**Search Endpoints:**
- 🔍 **POST /api/search** - Unified search (semantic, fuzzy, term) across contacts and interactions

**Interaction Endpoints:**
- 🤖 **POST /api/interactions/analyze** - LLM-powered extraction using OpenAI structured output
- 💾 **POST /api/interactions/confirm** - Persist analyzed interactions with automatic contact/family creation
- 📖 **GET /api/interactions/{id}** - Retrieve a single interaction by ID
- ✏️ **PATCH /api/interactions/{id}** - Update an existing interaction
- 🗑️ **DELETE /api/interactions/{id}** - Delete an interaction

**Contact Endpoints:**
- 📋 **GET /api/contacts** - List all contacts with pagination
- 📖 **GET /api/contacts/{id}** - Get a single contact by ID
- 📊 **GET /api/contacts/{id}/summary** - Contact summary with recent interactions
- ✏️ **PATCH /api/contacts/{id}** - Update contact details
- 🗑️ **DELETE /api/contacts/{id}** - Delete a contact
- 📜 **GET /api/contacts/{id}/interactions** - List all interactions for a contact

**Infrastructure:**
- ❤️ Health check endpoint
- 🏗️ Database schema with PostgreSQL + pgvector + pg_trgm
- 💉 FastAPI dependency injection for database connections
- 🔄 Transaction-based database operations with auto-commit/rollback
- 📁 Clean architecture with SQL files and prompt templates
- 🛡️ Global exception handlers for clean error handling
- 🧪 Comprehensive unit tests with dependency injection mocks
- 📝 Structured logging with colored console output
- 🔄 Alembic migrations for schema management
- 🚀 CI/CD with GitHub Actions
- 🎨 Retro-styled responsive UI with HTMX and consistent delete confirmations
- ⌨️ Keyboard shortcuts (cmd/ctrl+k for search, cmd/ctrl+. for new interaction)
- 🧹 Clean HTMX implementation with minimal inline JavaScript

### 🚧 Coming Soon
- 🔐 Google OAuth authentication (currently uses placeholder user_id)
- 📊 AI-generated contact insights
- 🎯 Semantic search using embeddings

## Technology Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Python 3.11+** - Latest stable Python
- **asyncpg** - Direct async PostgreSQL driver (NO ORM)
- **Pydantic** - Data validation and settings management only
- **Raw SQL** - All queries in `.sql` files for full visibility and control

### Database
- **PostgreSQL** - Primary relational database
- **pgvector** - Extension for storing and querying embeddings (semantic search)
- **pg_trgm** - Extension for trigram-based fuzzy text search
- Single database solution for relational data, vector search, and fuzzy search

### Frontend
- **HTMX** - Dynamic interactions without heavy JavaScript
- **Jinja2** - Server-side templating
- **Custom CSS** - Retro-styled design with dark/brown color scheme
- **tinykeys** - Lightweight keyboard shortcuts library (loaded via CDN)

### AI/Embeddings
- **OpenAI API** - For LLM analysis (structured output via `response_format`) and text embeddings
- GPT-4o with structured output using Pydantic models
- No local models needed
- Embeddings stored in pgvector for semantic search

### Authentication
- **Google OAuth 2.0** - Single sign-on
- **authlib** - OAuth implementation
- Session-based authentication with secure cookies

### Logging
- **structlog** - Structured logging
- Colored console output in development
- Verbose debug mode for development
- Structured JSON logs in production
- Environment-based configuration

### Testing
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-postgresql** - In-memory PostgreSQL for fast, isolated tests
- **pytest-socket** - Block network access during tests for isolation
- **httpx** - HTTP client for FastAPI testing
- No external dependencies required for tests

### Database Migrations
- **Alembic** - Database migration management
- **SQLAlchemy** - Used only for Alembic migrations (not in app code)
- Migration files use raw SQL via Alembic operations
- Application code remains ORM-free with raw SQL queries

### Development Tools
- **uv** - Fast Python package installer and dependency manager
- **just** - Command runner for common tasks
- **ruff** - Fast Python linter and formatter

### Deployment
- **Docker** - Containerization
- **docker-compose** - Local PostgreSQL with pgvector for development
- Cloud-agnostic approach - works on Digital Ocean, AWS, GCP, Azure
- Environment-based configuration for portability

## Project Structure

```
memoro/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── constants.py            # Template and app constants
│   │   ├── db.py                   # asyncpg connection pool & helpers
│   │   ├── exceptions.py           # Custom exceptions & handlers
│   │   ├── logger.py               # structlog configuration
│   │   ├── models.py               # Pydantic schemas (validation only)
│   │   ├── auth.py                 # Google OAuth implementation
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── ui.py               # UI endpoints (HTMX HTML responses)
│   │   │   ├── contacts.py         # Contact CRUD API endpoints
│   │   │   ├── interactions.py     # Interaction API endpoints
│   │   │   └── search.py           # Search API endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py              # OpenAI API (structured output)
│   │   │   ├── embeddings.py       # Embedding generation
│   │   │   ├── search.py           # Search logic (semantic/fuzzy/term)
│   │   │   ├── contacts.py         # Contact business logic
│   │   │   └── interactions.py     # Interaction business logic
│   │   ├── sql/                    # Raw SQL queries (by domain)
│   │   │   ├── contacts/
│   │   │   │   ├── find_or_create.sql
│   │   │   │   ├── update_latest_news.sql
│   │   │   │   ├── get_by_id.sql
│   │   │   │   ├── update.sql
│   │   │   │   ├── delete.sql
│   │   │   │   ├── list.sql
│   │   │   │   └── search.sql      # Vector similarity search
│   │   │   ├── interactions/
│   │   │   │   ├── create.sql
│   │   │   │   ├── get_by_id.sql
│   │   │   │   ├── update.sql
│   │   │   │   ├── delete.sql
│   │   │   │   └── list_by_contact.sql
│   │   │   ├── search/
│   │   │   │   ├── fuzzy_contacts.sql
│   │   │   │   ├── fuzzy_interactions.sql
│   │   │   │   ├── term_contacts.sql
│   │   │   │   └── term_interactions.sql
│   │   │   └── family_members/
│   │   │       └── create.sql
│   │   ├── prompts/                # LLM prompt templates
│   │   │   └── extract_interaction.txt
│   │   ├── templates/              # Jinja2 templates
│   │   │   ├── base.html           # Base template with header/footer
│   │   │   ├── index.html          # Homepage with contact list
│   │   │   ├── contact_profile.html # Contact detail page
│   │   │   └── components/         # HTMX fragments
│   │   │       ├── contact_list.html          # Contact list fragment
│   │   │       ├── contact_delete_modal.html  # Delete confirmation modal
│   │   │       ├── contact_edit.html          # Contact inline edit form
│   │   │       ├── contact_header.html        # Contact header fragment
│   │   │       ├── search_results.html        # Search results fragment
│   │   │       ├── modal.html                 # Generic modal wrapper
│   │   │       ├── interaction_edit.html      # Interaction inline edit form
│   │   │       ├── interaction_list.html      # Interaction list fragment
│   │   │       ├── relationship_edit.html     # Relationship inline edit form
│   │   │       ├── relationship_item.html     # Relationship item view
│   │   │       ├── relationship_list.html     # Relationship list fragment
│   │   │       ├── relationship_new.html      # New relationship form
│   │   │       ├── login_message.html         # Login prompt message
│   │   │       └── review_form.html           # LLM analysis review form
│   │   └── static/
│   │       ├── css/
│   │       │   └── style.css       # Retro dark/brown styling
│   │       └── js/
│   │           ├── main.js
│   │           ├── modal.js
│   │           ├── toast.js
│   │           └── htmx-handlers.js
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py             # pytest fixtures (in-memory DB)
│   │   ├── test_contacts.py
│   │   ├── test_interactions.py
│   │   ├── test_search.py
│   │   ├── test_ui.py              # UI endpoint tests
│   │   ├── test_network_blocking.py # Network isolation tests
│   │   └── test_relationship_mapping.py # Family relationship tests
│   └── Dockerfile
├── alembic/                        # Alembic migration files
│   ├── versions/
│   │   ├── d892e083fe19_initial_schema.py
│   │   └── 72052229f181_enable_pg_trgm_extension.py
│   ├── env.py                      # Alembic environment config
│   └── script.py.mako              # Migration template
├── alembic.ini                     # Alembic configuration
├── pyproject.toml                  # uv dependencies
├── justfile                        # Command runner
├── docker-compose.yml              # PostgreSQL with pgvector
├── .env.example                    # Environment template
├── .gitignore
├── claude.md                       # This file
└── README.md
```

## Key Design Decisions

### Why No ORM?
- **Transparency**: Direct visibility into all SQL queries
- **Performance**: No ORM overhead or N+1 query issues
- **Simplicity**: Easier to debug and optimize
- **Learning**: Better understanding of actual database operations
- **Control**: Fine-grained control over complex queries and pgvector operations

### Why asyncpg?
- Native async support for FastAPI
- High performance
- Direct PostgreSQL protocol implementation
- No abstraction layers

### Why SQL Files?
- Separation of concerns
- Easy to review and test queries independently
- Version control friendly
- No query builders or string concatenation
- Reusable across different parts of the application

### Why OpenAI API Instead of Local Models?
- No local GPU/compute requirements
- Access to best-in-class models (GPT-4o for analysis)
- Structured output using `response_format` for reliable extraction
- Scalable without infrastructure changes
- Cost-effective for personal CRM use case
- Simplified deployment

### Why OpenAI Structured Output?
- Type-safe response parsing using Pydantic models
- Eliminates manual JSON parsing and validation
- More reliable than prompt engineering alone
- Automatic retry on invalid responses
- Consistent schema enforcement
- Better error handling and debugging

### Why HTMX?
- Minimal JavaScript required
- Server-side rendering benefits (SEO, simplicity)
- Progressive enhancement approach
- Faster development without complex frontend builds
- Great for CRUD applications
- Declarative attributes (`hx-confirm`, `hx-swap`, etc.) replace inline JavaScript
- Built-in support for cancel patterns via GET endpoints

### Why structlog?
- Structured logging for better searchability
- Colored output improves dev experience
- Production-ready with JSON output
- Easy to integrate with log aggregation services
- Contextual logging support

### Why uv?
- 10-100x faster than pip
- Built-in dependency resolution
- Replaces pip, pip-tools, and virtualenv
- Modern Python packaging
- Growing ecosystem support

### Why just?
- Simpler than make
- Better error messages
- Cross-platform
- Easy to document commands
- Great for project-specific workflows

### Why Alembic with SQLAlchemy (for migrations only)?
- Battle-tested migration management
- Version-controlled schema changes
- Automatic rollback support
- SQLAlchemy used ONLY for migrations - application code stays ORM-free
- Migrations use raw SQL operations for transparency
- Best of both worlds: robust tooling + raw SQL control

### Why pytest-postgresql?
- In-memory database for fast tests
- No Docker required for CI/CD
- Automatic setup and teardown
- Isolated test environments
- Faster feedback loop during development

### Hybrid Database Approach
- **Development**: Docker PostgreSQL with pgvector (persisted data, easy reset)
- **Testing**: In-memory PostgreSQL via pytest-postgresql (fast, isolated)
- **Migrations**: Alembic against Docker PostgreSQL
- Application queries: Raw SQL files (no ORM dependency at runtime)

### Database Connection Pattern
We use FastAPI dependency injection for database connections:
- `get_db_dependency()` - FastAPI dependency for read operations
- `get_db_transaction_dependency()` - FastAPI dependency for transactional operations with auto-commit/rollback
- Injected via `Depends()` in endpoint parameters
- Automatic connection cleanup by FastAPI
- Easy to mock in tests by overriding `app.dependency_overrides`
- No manual connection management in endpoints

### Search Architecture
Memoro implements a unified search system with three modes:
- **Semantic Search** - Vector similarity using pgvector (planned, not yet implemented)
- **Fuzzy Search** - Trigram-based matching using pg_trgm extension for typo-tolerant search
- **Term Search** - Exact substring matching with ILIKE for precise queries
- Search spans both contacts and interactions with relevance scoring
- Implemented via `SearchType` enum for type-safe search mode selection

### UI/HTMX Pattern
- **Routers separation**: `ui.py` for HTML responses, separate API routers for JSON
- **Fragment components**: Reusable HTML fragments in `templates/components/` for dynamic updates
- **Constants management**: `constants.py` centralizes UI configuration (truncation lengths, pagination)
- **Progressive enhancement**: Full pages for initial loads, HTMX for dynamic interactions
- **Static assets**: Custom CSS with retro styling (including `.btn-danger` for delete buttons), minimal JavaScript for modals/toasts
- **Inline editing**: HTMX swapping for seamless edit/view transitions without page reloads
- **Cancel endpoints**: GET endpoints return empty content or item views to cancel form editing
- **Form-based UI**: UI endpoints accept form data directly, avoiding JSON parsing overhead
- **Consistent UX**: `hx-confirm` attribute on all delete buttons for confirmation prompts
- **Keyboard shortcuts**: Using tinykeys library for cross-platform shortcuts (cmd/ctrl+k for search, cmd/ctrl+. for new interaction)

### Prompt Management Pattern
LLM prompts stored as external files (like SQL):
- `backend/app/prompts/*.txt` - Prompt template files
- `load_prompt()` helper function loads prompts
- Consistent with SQL file pattern
- Easy to version control and edit without touching code
- Scalable for multiple prompts

### Exception Handling Pattern
Global exception handlers eliminate repetitive try/except blocks:
- `exceptions.py` - Custom exception classes and handlers
- Handlers registered in `main.py` at application startup
- Endpoints remain clean without error handling code
- Centralized logging and consistent error responses
- Proper HTTP status codes (503 for external services, 500 for internal errors)

### Service Layer Pattern
Service functions accept primitive parameters instead of Pydantic models:
- **Cleaner interfaces**: Functions accept individual parameters (strings, dates, dicts) directly
- **Separation of concerns**: Pydantic models used only at API boundaries for validation
- **Flexibility**: Service layer reusable across different input sources (JSON API, form data, CLI)
- **Simplicity**: No model instantiation overhead in service layer
- **Example**: `confirm_and_persist_interaction()` accepts `first_name`, `last_name`, etc. as separate parameters

## Database Schema Overview

### Core Tables (Singular Names)
- **user** - Google OAuth user data (email, first_name, last_name)
- **contact** - People in your network (first_name, last_name, birthday, latest_news)
- **interaction** - Daily interaction logs (notes, location, interaction_date, embedding)
- **family_member** - Contact relationships (self-referential links between contacts)

### Key Features
- UUID primary keys for distributed-friendly IDs
- TIMESTAMP WITH TIME ZONE for created_at, updated_at on all tables
- User isolation (all queries scoped to user_id)
- **pgvector** extension for semantic vector search
- **pg_trgm** extension for fuzzy text matching and similarity scoring
- Indexes on frequently queried fields (user_id, contact_id, dates, names)
- Trigram indexes on text fields for fast fuzzy search
- Cascading deletes for referential integrity

## Development Workflow

### Initial Setup
1. `uv sync` - Install all dependencies
2. `cp .env.example .env` - Create environment configuration
3. `docker-compose up -d` - Start PostgreSQL with pgvector
4. `just db-migrate` - Run Alembic migrations

### Local Development
1. `just dev` - Start FastAPI with hot reload
2. Edit code, changes reload automatically
3. View logs with color and structure
4. Database persists across restarts

### Database Operations
1. `just db-migrate` - Apply pending migrations
2. `just db-rollback` - Rollback last migration
3. `just db-revision "description"` - Create new migration
4. `just db-shell` - Open PostgreSQL shell
5. `docker-compose down` - Stop database (data persists)
6. `docker-compose down -v` - Stop and delete database

### Testing
1. `just test` - Run all tests with in-memory PostgreSQL
2. Tests run in isolation (no Docker required)
3. Fast feedback loop (< 5 seconds)
4. No interference with development database

## Testing

**Test Coverage:**

*Interaction Endpoints (API):*
- ✅ POST /api/interactions/analyze - Success, validation, API errors
- ✅ POST /api/interactions/confirm - Success, family linking, validation
- ✅ GET /api/interactions/{id} - Success, not found, invalid UUID
- ✅ PATCH /api/interactions/{id} - Update interaction
- ✅ DELETE /api/interactions/{id} - Delete interaction

*Contact Endpoints (API):*
- ✅ GET /api/contacts - Success, empty, pagination, validation
- ✅ GET /api/contacts/{id} - Success, not found, invalid UUID
- ✅ PATCH /api/contacts/{id} - Success, partial update, not found, empty body
- ✅ DELETE /api/contacts/{id} - Success, not found, invalid UUID
- ✅ GET /api/contacts/{id}/interactions - Success, empty, not found

*UI Endpoints:*
- ✅ GET / - Homepage rendering
- ✅ GET /contacts/{id} - Contact profile page
- ✅ GET /ui/contacts/{id}/delete - Delete confirmation modal
- ✅ DELETE /ui/contacts/{id} - Delete contact via UI
- ✅ POST /ui/interactions/analyze - Form-based analysis
- ✅ POST /ui/interactions/confirm - Form submission
- ✅ GET /ui/interactions/{id}/edit - Edit form rendering
- ✅ PATCH /ui/interactions/{id} - Inline editing
- ✅ DELETE /ui/interactions/{id} - Delete and refresh list

*Note:* New cancel endpoints (GET /ui/relationships/{id}, GET /ui/contacts/{id}/relationships/cancel) added in recent cleanup but not yet covered by tests.

*Infrastructure:*
- ✅ Health check endpoint
- ✅ Network isolation tests (pytest-socket)
- ✅ Relationship mapping tests

**Testing Approach:**
- FastAPI dependency injection with automatic overrides
- Mocked database connections and transactions
- Mocked OpenAI API calls
- In-memory PostgreSQL via pytest-postgresql
- **Network isolation**: pytest-socket blocks all TCP connections during tests
- No external dependencies required
- Aim for >80% coverage on core logic

### Code Quality
1. `just format` - Auto-format with ruff
2. `just lint` - Check code style
3. `just lint-fix` - Auto-fix linting issues
4. Run before committing

## Future Considerations

### Scaling
- Add connection pooling configuration
- Consider read replicas for search queries
- Cache frequently accessed contacts
- Rate limiting for OpenAI API

### Features
- Email notifications for birthdays
- Export data (JSON, CSV)
- Mobile-responsive design
- Dark mode
- Bulk import from contacts

### Deployment
- GitHub Actions for CI/CD
- Health check endpoints
- Database backup strategy
- Environment-specific configs
- Monitoring and alerting

## Environment Variables

```
DATABASE_URL=postgresql://user:pass@localhost:5432/memoro
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SECRET_KEY=...  # for session signing
LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR
ENVIRONMENT=development  # or production
```

## Dependencies (Key Packages)

### Core
- fastapi
- uvicorn[standard]
- asyncpg
- pydantic-settings
- jinja2

### Database Migrations
- alembic
- sqlalchemy
- psycopg2-binary

### Auth & HTTP
- authlib
- httpx
- python-multipart

### Logging
- structlog
- colorama

### AI/Embeddings
- openai  # OpenAI API client

### Testing
- pytest
- pytest-asyncio
- pytest-postgresql
- pytest-socket

### Dev Tools
- ruff

## Conventions

### Code Style
- Use ruff defaults
- Type hints everywhere
- Async/await for all I/O operations
- Pydantic models for validation

### SQL Files
- One query per file
- Named parameters (`:param_name`)
- Comments for complex queries
- Organized by domain (contacts/, interactions/)

### Logging
- Use structured logging with context
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Include user_id and request_id in logs
- No sensitive data in logs

### Testing Conventions
- Test file names: `test_*.py`
- One test class per feature
- Use fixtures for common setup
- Mock external APIs (OpenAI)
