# Memoro - Personal CRM

# Default recipe to display help information
default:
    @just --list

# Install dependencies using uv
install:
    uv sync --all-extras

# Run development server with hot reload
dev:
    uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Run all tests
test:
    uv run pytest backend/tests -v

# Run tests with coverage
test-cov:
    uv run pytest backend/tests -v --cov=backend.app --cov-report=term-missing

# Run specific test file
test-file file:
    uv run pytest backend/tests/{{file}} -v

# Format code with ruff
format:
    uv run ruff format .

# Lint code with ruff (show all warnings)
lint:
    uv run ruff check . --output-format=full

# Lint and fix auto-fixable issues
lint-fix:
    uv run ruff check . --fix

# Run both format and lint
check: format lint

# Install pre-commit hooks
hooks-install:
    uv run pre-commit install

# Run pre-commit on all files
hooks-run:
    uv run pre-commit run --all-files

# Start full stack (API + database) with hot reload
docker-up:
    docker-compose up -d
    @echo "Services starting..."
    @echo "API: http://localhost:8000"
    @echo "Docs: http://localhost:8000/docs"
    @echo "Database: localhost:5432"

# Stop all Docker services
docker-down:
    docker-compose down

# View logs from all services
docker-logs:
    docker-compose logs -f

# View API logs only
docker-logs-api:
    docker-compose logs -f api

# Rebuild and restart services
docker-restart:
    docker-compose down
    sleep 2
    docker-compose up -d --build

# Setup local database only (requires docker-compose)
db-setup:
    docker-compose up -d postgres
    sleep 2
    @echo "Database is ready at localhost:5432"

# Stop local database
db-stop:
    docker-compose down postgres

# Run database migrations
db-migrate:
    uv run alembic upgrade head

# Rollback last migration
db-rollback:
    uv run alembic downgrade -1

# Setup development environment with test user
dev-setup:
    docker-compose up -d postgres
    sleep 3
    uv run alembic upgrade head
    @echo "Creating test user..."
    docker-compose exec postgres psql -U memoro -d memoro -c "INSERT INTO \"user\" (id, email, first_name, last_name) VALUES ('00000000-0000-0000-0000-000000000000', 'test@example.com', 'Test', 'User') ON CONFLICT (id) DO NOTHING;"
    @echo "✅ Development environment ready!"
    @echo "Run 'just dev' to start the API server"

# Create new migration
db-revision message:
    uv run alembic revision -m "{{message}}"

# Open database shell
db-shell:
    docker-compose exec postgres psql -U memoro -d memoro

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Run the application in production mode
run:
    uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Export OpenAPI spec to file
openapi:
    @echo "Exporting OpenAPI specification..."
    uv run python -c "from backend.app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
    @echo "OpenAPI spec exported to openapi.json"

# Show project info
info:
    @echo "Memoro - Personal CRM"
    @echo "Python version: $(python --version)"
    @echo "uv version: $(uv --version)"
    @echo ""
    @echo "Run 'just install' to install dependencies"
    @echo "Run 'just dev' to start development server"
    @echo "Run 'just test' to run tests"

# Backfill embeddings for interactions (max 20, requires confirmation)
backfill-embeddings:
    @echo "⚠️  This will generate embeddings using OpenAI API (costs money)"
    @echo "   Run the script directly for interactive mode:"
    @echo "   uv run python scripts/backfill_embeddings.py"
    @echo ""
    @read -p "Press Enter to continue or Ctrl-C to cancel..." && uv run python scripts/backfill_embeddings.py

# Import contacts from TSV file (preview mode by default - no changes, no OpenAI calls)
import tsv_file:
    uv run python scripts/import_tsv.py {{tsv_file}}

# Actually import contacts from TSV file (creates contacts, interactions with embeddings)
import-execute tsv_file:
    @echo "⚠️  This will import contacts and generate embeddings using OpenAI API"
    @echo "   Run 'just import {{tsv_file}}' to preview first"
    @echo ""
    uv run python scripts/import_tsv.py --execute {{tsv_file}}

# Rollback import by deleting contacts from TSV file (preview mode by default)
import-rollback tsv_file:
    uv run python scripts/rollback_import.py {{tsv_file}}

# Actually rollback import (DESTRUCTIVE - deletes contacts)
import-rollback-execute tsv_file:
    @echo "⚠️  This will DELETE all contacts from the TSV file!"
    @echo "   This includes all interactions and relationships!"
    @echo "   Run 'just import-rollback {{tsv_file}}' to preview first"
    @echo ""
    uv run python scripts/rollback_import.py --execute {{tsv_file}}
