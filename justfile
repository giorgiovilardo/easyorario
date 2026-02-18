# Easyorario task runner

set dotenv-load

# List available recipes
default:
    @just --list

# Start Litestar dev server with hot reload
dev:
    DEBUG=true uv run litestar --app easyorario.app:app run --reload --debug

# Run pytest (full suite)
test:
    uv run pytest

# Run pytest on a single file
test-file path:
    uv run pytest "{{path}}" -v

# Run ruff check + pyright
lint:
    uv run ruff check easyorario/ tests/
    uv run pyright easyorario/

# Sort imports + format
fmt:
    uv run ruff check --select I --fix easyorario/ tests/
    uv run ruff format easyorario/ tests/

# Run all quality checks: format, lint, typecheck
check: fmt lint

# Run Alembic upgrade head
db-migrate:
    uv run alembic upgrade head

# Create new Alembic revision
db-revision msg:
    uv run alembic revision --autogenerate -m "{{msg}}"

# Build Docker image
docker-build:
    docker build -t easyorario .

# Run Docker container
docker-run:
    docker run -p 8000:8000 -v easyorario-data:/app/data easyorario
