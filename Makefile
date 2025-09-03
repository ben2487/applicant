.PHONY: setup test lint fmt run list list-browser list-user test-ai help db-up db-wait db-reset clean-traces dev backend-test

# Default target
help:
	@echo "Available commands:"
	@echo "  setup          - Install dependencies and Playwright browsers"
	@echo "  test           - Run tests"
	@echo "  lint           - Run linting with ruff"
	@echo "  fmt            - Format code with ruff and black"
	@echo "  list-browser   - List Chrome browser profiles"
	@echo "  list-user      - List user profiles"
	@echo "  run            - Run automation with structured extraction & agentic AI"
	@echo "  test-ai        - Test OpenAI API key with GPT-4o-mini"
	@echo "  db-up          - Start PostgreSQL database (brew)"
	@echo "  db-wait        - Wait for database to be ready"
	@echo "  db-reset       - Reset database (drop/create + schema)"
	@echo "  clean-traces   - Clean trace files"
	@echo "  dev            - Start development server (backend + frontend)"
	@echo "  backend-test   - Run backend tests"
	@echo "  help           - Show this help message"

# Install dependencies and Playwright browsers
setup:
	poetry install
	poetry run playwright install --with-deps

# Run tests
test:
	poetry run pytest -q

# Run backend tests
backend-test:
	poetry run pytest tests/test_backend.py -v

# Run linting
lint:
	poetry run ruff check .

# Format code
fmt:
	poetry run ruff check --fix .
	poetry run black .

# List Chrome browser profiles
list-browser:
	cd src && poetry run python -m webbot.cli list-browser-profiles

# List user profiles
list-user:
	cd src && poetry run python -m webbot.cli list-user-profiles

# Test OpenAI API key
test-ai:
	cd src && poetry run python -m webbot.cli test-openai-key

# Run example automation with structured extraction and agentic AI
run:
	cd src && poetry run python -m webbot.cli run "DefaultUser" --use-browser-profile "Default" --initial-job-url "https://www.workatastartup.com/jobs/74132" --ai-mode openai

# Run with heuristic extraction only (no OpenAI required)
run-heuristic:
	cd src && poetry run python -m webbot.cli run "DefaultUser" --use-browser-profile "Default" --initial-job-url "https://www.workatastartup.com/jobs/74132" --ai-mode llm_off

# Database management
db-up:
	@echo "Starting PostgreSQL database..."
	brew services start postgresql@16
	@echo "PostgreSQL started. Run 'make db-wait' to wait for it to be ready."

db-wait:
	@echo "Waiting for PostgreSQL to be ready..."
	@if command -v pg_isready >/dev/null 2>&1; then \
		until pg_isready -h localhost -p 5432; do sleep 1; done; \
	elif [ -f "/opt/homebrew/opt/postgresql@16/bin/pg_isready" ]; then \
		until /opt/homebrew/opt/postgresql@16/bin/pg_isready -h localhost -p 5432; do sleep 1; done; \
	else \
		echo "Error: pg_isready not found. Please ensure PostgreSQL is properly installed."; \
		exit 1; \
	fi
	@echo "PostgreSQL is ready!"

db-reset:
	@echo "Resetting database..."
	@if command -v dropdb >/dev/null 2>&1; then \
		dropdb --if-exists webbot; \
		createdb webbot; \
		psql -d webbot -f src/backend/database/schema.sql; \
	elif [ -f "/opt/homebrew/opt/postgresql@16/bin/dropdb" ]; then \
		/opt/homebrew/opt/postgresql@16/bin/dropdb --if-exists webbot; \
		/opt/homebrew/opt/postgresql@16/bin/createdb webbot; \
		/opt/homebrew/opt/postgresql@16/bin/psql -d webbot -f src/backend/database/schema.sql; \
	else \
		echo "Error: PostgreSQL binaries not found. Please ensure PostgreSQL is properly installed."; \
		exit 1; \
	fi
	@echo "Database reset complete!"

# Clean up generated files
clean:
	find . -type f -name "*.png" -delete
	find . -type f -name "*.zip" -delete
	find . -type f -name "*.har" -delete
	find . -type d -name "videos" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true

# Clean trace files
clean-traces:
	@echo "Cleaning trace files..."
	rm -rf .trace/*
	@echo "Trace files cleaned!"

# Development server
dev:
	@echo "Starting development server..."
	@echo "Backend will be available at http://localhost:8000"
	@echo "Frontend will be available at http://localhost:3000"
	@echo ""
	@echo "Starting backend..."
	cd src/backend && poetry run python -m flask --app app:create_app run --host=0.0.0.0 --port=8000 --debug &
	@echo "Backend started!"
	@echo ""
	@echo "To open in browser, run: open http://localhost:8000"

