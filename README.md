[![CI](https://github.com/SergeNasr/memoro/actions/workflows/ci.yml/badge.svg)](https://github.com/SergeNasr/memoro/actions/workflows/ci.yml)

<p align="center">
  <img src="assets/banner.png" alt="Memoro Banner" width="50%">
</p>

# Memoro

A personal CRM for tracking daily interactions with people in your life. Record contact details, interactions, and use semantic search to find context about your relationships.

## Tech Stack

- **Backend**: FastAPI + asyncpg (no ORM, raw SQL)
- **Database**: PostgreSQL + pgvector for semantic search
- **Frontend**: HTMX + Jinja2 + Tailwind CSS
- **Auth**: Google OAuth 2.0
- **AI**: OpenAI API for LLM analysis and embeddings
- **Testing**: pytest + pytest-postgresql (in-memory)

## Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [just](https://github.com/casey/just) - Command runner

## Quick Start

1. **Install dependencies**
   ```bash
   just install
   # or: uv sync --all-extras
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start PostgreSQL**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   just db-migrate
   ```

5. **Start the development server**
   ```bash
   just dev
   ```

6. **Access the API**
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Development Commands

### Run
```bash
just dev              # Start FastAPI with hot reload
```

### Testing
```bash
just test             # Run all tests (in-memory PostgreSQL)
```

### Code Quality
```bash
just format           # Auto-format with ruff
just lint             # Check code style
```

### Database
```bash
just db-migrate       # Apply pending migrations
just db-rollback      # Rollback last migration
just db-revision "description"  # Create new migration
just db-shell         # Open PostgreSQL shell
```

## Project Structure

```
memoro/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── db.py                # Database connection pool & helpers
│   │   ├── exceptions.py        # Custom exceptions & handlers
│   │   ├── sql/                 # Raw SQL queries (by domain)
│   │   ├── prompts/             # LLM prompt templates
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   └── templates/           # Jinja2 templates
│   └── tests/                   # pytest tests
├── alembic/                     # Database migrations
│   ├── versions/                # Migration files
│   └── env.py                   # Alembic config
├── alembic.ini                  # Alembic settings
├── docker-compose.yml           # PostgreSQL + pgvector
├── pyproject.toml               # uv dependencies
└── justfile                     # Command definitions
```

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/memoro
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SECRET_KEY=...
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

## Implemented Features

### ✅ Currently Available

**Interaction Endpoints:**
- 🤖 **POST /api/interactions/analyze** - LLM-powered extraction of contact info and interaction details from natural text
- 💾 **POST /api/interactions/confirm** - Persist analyzed interactions to database with automatic contact creation and family linking
- 📖 **GET /api/interactions/{id}** - Retrieve a single interaction by ID

**Contact Endpoints:**
- 📋 **GET /api/contacts** - List all contacts with pagination
- 📖 **GET /api/contacts/{id}** - Get a single contact by ID
- ✏️ **PATCH /api/contacts/{id}** - Update contact details
- 🗑️ **DELETE /api/contacts/{id}** - Delete a contact
- 📜 **GET /api/contacts/{id}/interactions** - List all interactions for a contact

**Infrastructure:**
- ❤️ Health check endpoint
- 🏗️ Database schema with PostgreSQL + pgvector support
- 💉 FastAPI dependency injection for database connections
- 🔄 Transaction-based database operations with auto-commit/rollback
- 📁 Clean architecture with SQL files and prompt templates
- 🛡️ Global exception handlers for clean error handling
- 🧪 Comprehensive unit tests with dependency injection mocks
- 📝 Structured logging with colored console output
- 🔄 Alembic migrations for schema management
- 🚀 CI/CD with GitHub Actions

### 🚧 Coming Soon
- 🔍 Semantic search using embeddings
- ✏️ PATCH /api/interactions/{id} - Update interactions
- 🗑️ DELETE /api/interactions/{id} - Delete interactions
- 📊 Contact summaries with AI-generated insights
- 🔐 Google OAuth authentication
- 🎨 HTMX frontend

## Database Schema

Tables use singular names:
- **user** - OAuth users (email, first_name, last_name)
- **contact** - People you track (first_name, last_name, birthday, latest_news)
- **interaction** - Interaction logs (notes, location, interaction_date, embedding)
- **family_member** - Contact relationships (self-referential)

All tables have timezone-aware `created_at` and `updated_at` timestamps.

## API Documentation

Full API documentation available at http://localhost:8000/docs when running the development server.

## Testing

Run the test suite:
```bash
just test
```

**Test Coverage (29 tests):**

*Interaction Endpoints:*
- ✅ POST /api/interactions/analyze - Success, validation, API errors
- ✅ POST /api/interactions/confirm - Success, family linking, validation
- ✅ GET /api/interactions/{id} - Success, not found, invalid UUID

*Contact Endpoints:*
- ✅ GET /api/contacts - Success, empty, pagination, validation
- ✅ GET /api/contacts/{id} - Success, not found, invalid UUID
- ✅ PATCH /api/contacts/{id} - Success, partial update, not found, empty body
- ✅ DELETE /api/contacts/{id} - Success, not found, invalid UUID
- ✅ GET /api/contacts/{id}/interactions - Success, empty, not found

*Infrastructure:*
- ✅ Health check endpoint

**Testing Approach:**
- FastAPI dependency injection with automatic overrides
- Mocked database connections and transactions
- Mocked OpenAI API calls
- In-memory PostgreSQL via pytest-postgresql
- No external dependencies required

## Architecture Decisions

See [claude.md](./claude.md) for detailed architecture and technical decisions.
