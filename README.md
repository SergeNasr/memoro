[![CI](https://github.com/SergeNasr/memoro/actions/workflows/ci.yml/badge.svg)](https://github.com/SergeNasr/memoro/actions/workflows/ci.yml)

<p align="center">
  <img src="assets/banner.png" alt="Memoro Banner" width="50%">
</p>

# Memoro

A personal CRM for tracking daily interactions with people in your life. Record contact details, interactions, and use semantic search to find context about your relationships.

## Tech Stack

FastAPI • PostgreSQL • HTMX • OpenAI API

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- [just](https://github.com/casey/just)

## Quick Start

```bash
# Install dependencies
just install

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start database
docker-compose up -d

# Run migrations
just db-migrate

# Start server
just dev
```

Visit http://localhost:8000

## Keyboard Shortcuts

- `cmd+k` (or `ctrl+k`) - Focus search bar
- `cmd+.` (or `ctrl+.`) - New interaction

## Commands

```bash
just dev              # Start dev server
just test             # Run tests
just format           # Format code
just lint             # Lint code

just db-migrate       # Apply migrations
just db-rollback      # Rollback migration
just db-shell         # PostgreSQL shell
```

## Documentation

- API docs: http://localhost:8000/docs
- Architecture: [claude.md](./claude.md)
