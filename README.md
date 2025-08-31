# Applicant - Python Browser Automation Starter

A Python browser automation starter project using Playwright, designed to help you quickly get started with web automation tasks.

## Features

- **Browser Helper**: Easy-to-use browser automation wrapper with context management
- **Example Flows**: Ready-to-run examples for form filling and navigation
- **Testing**: Comprehensive test suite with pytest
- **CI/CD**: GitHub Actions workflow for automated testing
- **Code Quality**: Ruff for linting, Black for formatting

## Requirements

- Python 3.8+
- Poetry (for dependency management)
- Playwright browsers

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/ben2487/applicant.git
cd applicant
```

### 2. Install Dependencies

```bash
# Install Poetry if you don't have it
brew install poetry

# Install project dependencies
make install

# Install Playwright browsers
make install-browsers
```

### 3. Run Examples

```bash
# Run the example form automation
make run

# Or run specific flows
poetry run python -m automation.example_flow
```

## Available Commands

```bash
make help           # Show available commands
make install        # Install dependencies
make test          # Run tests
make run           # Run example automation
make lint          # Run linting
make fmt           # Format code
make clean         # Clean generated files
make install-browsers  # Install Playwright browsers
```

## Project Structure

```
applicant/
├── src/
│   └── automation/
│       ├── __init__.py
│       ├── browser.py          # Browser helper class
│       └── example_flow.py     # Example automation flows
├── tests/
│   ├── __init__.py
│   └── test_example.py         # Test suite
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── pyproject.toml              # Poetry configuration
├── ruff.toml                   # Ruff configuration
├── Makefile                    # Build automation
└── README.md                   # This file
```

## Usage Examples

### Basic Browser Automation

```python
from automation.browser import create_browser

# Simple automation
with create_browser(headless=False) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    browser.take_screenshot(page, "screenshot.png")
```

### Form Automation

```python
from automation.example_flow import example_form_fill_flow

# Run the example form automation
example_form_fill_flow(
    url="https://httpbin.org/forms/post",
    screenshot_path="form_result.png",
    headless=False
)
```

### Custom Automation

```python
from automation.browser import BrowserHelper

with BrowserHelper(headless=True) as browser:
    context = browser.create_context(tracing=True)
    page = browser.new_page()
    
    # Your automation logic here
    page.goto("https://example.com")
    page.click("button")
    
    # Take screenshot
    browser.take_screenshot(page, "result.png")
    
    # Save trace for debugging
    browser.stop_tracing("trace.zip")
```

## Testing

Run the test suite:

```bash
make test
```

Run specific test categories:

```bash
# Unit tests only
poetry run pytest tests/ -m "not integration"

# Integration tests only
poetry run pytest tests/ -m "integration"
```

## Development

### Code Quality

```bash
# Check code quality
make lint

# Auto-format code
make fmt
```

### Adding New Tests

1. Create test functions in `tests/test_example.py`
2. Use the `@pytest.mark.integration` decorator for tests requiring network access
3. Run `make test` to verify

### Adding New Automation Flows

1. Create new functions in `src/automation/example_flow.py`
2. Import and expose them in `src/automation/__init__.py`
3. Add tests in `tests/test_example.py`

## Troubleshooting

### Common Issues

#### Playwright Browsers Not Installed

```bash
make install-browsers
```

#### Permission Errors on macOS

If you encounter permission issues with Playwright:

```bash
# Grant accessibility permissions to Terminal/VS Code
# System Preferences > Security & Privacy > Privacy > Accessibility
```

#### Network Issues in Tests

Integration tests require internet access. If they fail:

```bash
# Skip integration tests
poetry run pytest tests/ -m "not integration"
```

#### Poetry Environment Issues

```bash
# Remove and recreate virtual environment
poetry env remove python
poetry install
```

### Debug Mode

Run with visible browser for debugging:

```python
# In your code
with create_browser(headless=False, slow_mo=1000) as browser:
    # Your automation code
```

### Tracing and Debugging

Enable tracing to debug automation issues:

```python
with create_browser() as browser:
    context = browser.create_context(tracing=True)
    # ... your automation code ...
    browser.stop_tracing("debug_trace.zip")
```

View traces with Playwright Trace Viewer:

```bash
poetry run playwright show-trace debug_trace.zip
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `make test`
6. Format your code: `make fmt`
7. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about your problem
