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
