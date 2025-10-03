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

## Quick Start

1. **Install dependencies**
   ```bash
   just install
   # or: uv sync --all-extras
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
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

## Implemented Features

### ✅ Currently Available
- 🤖 **POST /api/interactions/analyze** - LLM-powered extraction of contact info and interaction details from natural text
- ❤️ Health check endpoint
- 🏗️ Database schema with PostgreSQL + pgvector support
- 🧪 Comprehensive unit tests with reusable mocks
- 📝 Structured logging with colored console output
- 🔄 Alembic migrations for schema management

### 🚧 Coming Soon
- 📝 Confirm and persist analyzed interactions
- 🔍 Semantic search using embeddings
- 👥 CRUD operations for contacts and interactions
- 📊 Contact summaries
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

### POST /api/interactions/analyze

Analyzes raw interaction text using LLM to extract structured information.

**Request:**
```json
{
  "text": "Had coffee with Sarah Johnson at Starbucks today. She mentioned her birthday is March 15th and her daughter Emma just started college."
}
```

**Response:**
```json
{
  "contact": {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "birthday": "1985-03-15",
    "confidence": 0.95
  },
  "interaction": {
    "notes": "Had coffee together, discussed daughter starting college",
    "location": "Starbucks",
    "interaction_date": "2025-10-02",
    "confidence": 0.9
  },
  "family_members": [
    {
      "first_name": "Emma",
      "last_name": "Johnson",
      "relationship": "child",
      "confidence": 0.85
    }
  ],
  "raw_text": "Had coffee with Sarah Johnson at..."
}
```

**Features:**
- Extracts contact name, birthday, location
- Identifies family members and relationships
- Returns confidence scores for all extracted data
- Preserves original text for reference

## Testing

Run the test suite:
```bash
just test
```

Tests include:
- ✅ Successful interaction analysis
- ✅ Request validation (empty/missing text)
- ✅ API error handling
- ✅ Health check endpoint

All tests use mocked OpenRouter API calls (no external dependencies).

## Architecture Decisions

See [claude.md](./claude.md) for detailed architecture and technical decisions.
