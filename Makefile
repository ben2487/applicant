.PHONY: setup test lint fmt run list test-ai help

# Default target
help:
	@echo "Available commands:"
	@echo "  setup          - Install dependencies and Playwright browsers"
	@echo "  test           - Run tests"
	@echo "  lint           - Run linting with ruff"
	@echo "  fmt            - Format code with ruff and black"
	@echo "  list           - List Chrome browser profiles"
	@echo "  run            - Run automation (auto-attaches to existing Chrome or launches new)"
	@echo "  test-ai        - Test OpenAI API key with GPT-5o-mini"
	@echo "  help           - Show this help message"

# Install dependencies and Playwright browsers
setup:
	poetry install
	poetry run playwright install --with-deps

# Run tests
test:
	poetry run pytest -q

# Run linting
lint:
	poetry run ruff check .

# Format code
fmt:
	poetry run ruff check --fix .
	poetry run black .

# List Chrome profiles
list:
	cd src && poetry run python -m webbot.cli list-browser-profiles

# Test OpenAI API key
test-ai:
	cd src && poetry run python -m webbot.cli test-openai-key

# Run example automation
run:
	cd src && poetry run python -m webbot.cli run --use-browser-profile "Default" --initial-job-url "https://www.workatastartup.com/jobs/74132"

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

