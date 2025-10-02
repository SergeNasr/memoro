# Memoro

A personal CRM for tracking daily interactions with people in your life. Record contact details, interactions, and use semantic search to find context about your relationships.

## Tech Stack

- **Backend**: FastAPI + asyncpg (no ORM, raw SQL)
- **Database**: PostgreSQL + pgvector for semantic search
- **Frontend**: HTMX + Jinja2 + Tailwind CSS
- **Auth**: Google OAuth 2.0
- **AI**: OpenRouter API for embeddings
- **Testing**: pytest + pytest-postgresql (in-memory)

## Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [just](https://github.com/casey/just) - Command runner

## Setup

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Start PostgreSQL**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   just db-migrate
   ```

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
│   │   ├── sql/                 # Raw SQL queries
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
OPENROUTER_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SECRET_KEY=...
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

## Key Features

- 📝 Track daily interactions with contacts
- 🔍 Semantic search using embeddings
- 👥 Manage contact relationships and family members
- 🎂 Store birthdays, locations, and updates
- 🔐 Google OAuth authentication
- 🚀 Fast, async Python backend
- ✨ No ORM - direct SQL for transparency
- 🔄 Alembic migrations for schema management
- 🐳 Docker PostgreSQL for dev, in-memory for tests

## Database Schema

Tables use singular names:
- **user** - OAuth users (email, first_name, last_name)
- **contact** - People you track (first_name, last_name, birthday, latest_news)
- **interaction** - Interaction logs (notes, location, interaction_date, embedding)
- **family_member** - Contact relationships (self-referential)

All tables have timezone-aware `created_at` and `updated_at` timestamps.

## Architecture Decisions

See [CLAUDE.md](./CLAUDE.md) for detailed architecture and technical decisions.
