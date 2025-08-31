.PHONY: help install test run lint fmt clean install-browsers

# Default target
help:
	@echo "Available commands:"
	@echo "  install          - Install dependencies"
	@echo "  install-browsers - Install Playwright browsers"
	@echo "  test            - Run tests"
	@echo "  run             - Run example automation flow"
	@echo "  lint            - Run linting with ruff"
	@echo "  fmt             - Format code with black"
	@echo "  clean           - Clean up generated files"
	@echo "  help            - Show this help message"

# Install dependencies
install:
	poetry install

# Install Playwright browsers
install-browsers:
	poetry run playwright install --with-deps

# Run tests
test:
	PYTHONPATH=src poetry run pytest tests/ -v

# Run example automation flow
run:
	PYTHONPATH=src poetry run python -m automation.example_flow

# Run linting
lint:
	poetry run ruff check .

# Format code
fmt:
	poetry run black .
	poetry run ruff check --fix .

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

# Development setup
dev-setup: install install-browsers
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything is working."
