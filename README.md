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
│   │   ├── db.py                # Database connection pool & helpers
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
- 💾 **POST /api/interactions/confirm** - Persist analyzed interactions to database with automatic contact creation and family linking
- ❤️ Health check endpoint
- 🏗️ Database schema with PostgreSQL + pgvector support
- 🔄 Transaction-based database operations with auto-commit/rollback
- 📁 Clean architecture with SQL files and prompt templates
- 🧪 Comprehensive unit tests with reusable mocks
- 📝 Structured logging with colored console output
- 🔄 Alembic migrations for schema management

### 🚧 Coming Soon
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

---

### POST /api/interactions/confirm

Confirms and persists the analyzed interaction data to the database.

**Request:**
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
  ]
}
```

**Response:**
```json
{
  "contact_id": "123e4567-e89b-12d3-a456-426614174000",
  "interaction_id": "987f6543-e21a-45b7-b123-426614174001",
  "family_members_linked": 1
}
```

**Features:**
- Creates or finds existing contacts (case-insensitive name matching)
- Creates interaction records with notes, location, and date
- Automatically creates contacts for family members and links relationships
- Updates contact's `latest_news` field
- All operations in a single transaction (auto-commit/rollback)

## Testing

Run the test suite:
```bash
just test
```

Tests include:
- ✅ Successful interaction analysis with LLM
- ✅ Interaction confirmation and database persistence
- ✅ Family member linking
- ✅ Request validation (empty/missing text)
- ✅ API error handling
- ✅ Health check endpoint

All tests use mocked external dependencies (OpenRouter API, database transactions).

## Architecture Decisions

See [claude.md](./claude.md) for detailed architecture and technical decisions.
