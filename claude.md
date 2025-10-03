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

## Technology Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Python 3.11+** - Latest stable Python
- **asyncpg** - Direct async PostgreSQL driver (NO ORM)
- **Pydantic** - Data validation and settings management only
- **Raw SQL** - All queries in `.sql` files for full visibility and control

### Database
- **PostgreSQL** - Primary relational database
- **pgvector** - Extension for storing and querying embeddings
- Single database solution for both relational data and vector search

### Frontend
- **HTMX** - Dynamic interactions without heavy JavaScript
- **Jinja2** - Server-side templating
- **Tailwind CSS** - Utility-first styling

### AI/Embeddings
- **OpenRouter API** - For generating text embeddings
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
│   │   ├── db.py                   # asyncpg connection pool & helpers
│   │   ├── logger.py               # structlog configuration
│   │   ├── models.py               # Pydantic schemas (validation only)
│   │   ├── auth.py                 # Google OAuth implementation
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── contacts.py         # Contact CRUD endpoints
│   │   │   └── interactions.py     # Interaction endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py              # OpenRouter API client for LLM
│   │   │   ├── embeddings.py       # Embedding generation
│   │   │   └── search.py           # Semantic search logic
│   │   ├── sql/                    # Raw SQL queries (by domain)
│   │   │   ├── contacts/
│   │   │   │   ├── find_or_create.sql
│   │   │   │   ├── update_latest_news.sql
│   │   │   │   ├── get_by_id.sql
│   │   │   │   ├── update.sql
│   │   │   │   ├── list.sql
│   │   │   │   └── search.sql      # Vector similarity search
│   │   │   ├── interactions/
│   │   │   │   ├── create.sql
│   │   │   │   ├── get_latest.sql
│   │   │   │   └── list_by_contact.sql
│   │   │   └── family_members/
│   │   │       └── create.sql
│   │   ├── prompts/                # LLM prompt templates
│   │   │   └── extract_interaction.txt
│   │   ├── templates/              # Jinja2 templates
│   │   │   ├── base.html
│   │   │   ├── contacts/
│   │   │   │   ├── list.html
│   │   │   │   ├── detail.html
│   │   │   │   └── form.html
│   │   │   └── interactions/
│   │   │       ├── list.html
│   │   │       └── form.html
│   │   └── static/
│   │       ├── css/
│   │       └── js/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py             # pytest fixtures (in-memory DB)
│   │   ├── test_contacts.py
│   │   ├── test_interactions.py
│   │   └── test_search.py
│   └── Dockerfile
├── alembic/                        # Alembic migration files
│   ├── versions/
│   │   └── d892e083fe19_initial_schema.py
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

### Why OpenRouter Instead of Local Models?
- No local GPU/compute requirements
- Access to best-in-class embedding models
- Scalable without infrastructure changes
- Cost-effective for personal CRM use case
- Simplified deployment

### Why HTMX?
- Minimal JavaScript required
- Server-side rendering benefits (SEO, simplicity)
- Progressive enhancement approach
- Faster development without complex frontend builds
- Great for CRUD applications

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
We use clean context managers to eliminate boilerplate:
- `get_db_transaction()` - For transactional operations with auto-commit/rollback
- `get_db_connection()` - For simple read queries
- No repetitive `pool.acquire()` and `conn.transaction()` code
- Pattern reusable across all endpoints

### Prompt Management Pattern
LLM prompts stored as external files (like SQL):
- `backend/app/prompts/*.txt` - Prompt template files
- `load_prompt()` helper function loads prompts
- Consistent with SQL file pattern
- Easy to version control and edit without touching code
- Scalable for multiple prompts

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
- pgvector extension enabled for semantic search
- Indexes on frequently queried fields (user_id, contact_id, dates, names)
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
- Rate limiting for OpenRouter API

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
OPENROUTER_API_KEY=sk-...
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
- openai  # OpenRouter client compatible

### Testing
- pytest
- pytest-asyncio
- pytest-postgresql

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

### Testing
- Test file names: `test_*.py`
- One test class per feature
- Use fixtures for common setup
- Mock external APIs (OpenRouter)
- Aim for >80% coverage on core logic
