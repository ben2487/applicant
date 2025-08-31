# WebBot - Browser Automation Starter

A Python browser automation starter project using Playwright, designed to help you quickly get started with web automation tasks including Chrome profile management and job application workflows.

## Features

- **Chrome Profile Management**: Discover and list Chrome profiles with human-readable names and email identifiers
- **Persistent Browser Sessions**: Launch Chrome with existing profiles to reuse cookies and sessions
- **Job Page Analysis**: Extract visible text from job pages and analyze content
- **Smart Apply URL Discovery**: Use OpenAI-assisted search to find company careers/apply pages
- **Domain Filtering**: Maintain a do-not-apply domain list for job aggregation sites
- **CLI Interface**: Easy-to-use Typer-based command line interface
- **Testing**: Comprehensive test suite with pytest

## Requirements

- Python 3.10+
- Poetry (for dependency management)
- Chrome browser installed
- Playwright browsers
- OpenAI API key (optional, for enhanced search)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd applicant
```

### 2. Install Dependencies

```bash
# Install Poetry if you don't have it
brew install poetry

# Install project dependencies and Playwright browsers
make setup
```

### 3. List Chrome Profiles

```bash
# List all available Chrome profiles
make list

# Or run directly
poetry run python -m webbot.cli list-browser-profiles
```

### 4. Run Automation

```bash
# Open Chrome with Default profile and visit a job page
make run

# Or customize the profile and URL
poetry run python -m webbot.cli run \
  --use-browser-profile "Profile 1" \
  --initial-job-url "https://example.com/jobs/123"
```

## Available Commands

```bash
make help           # Show available commands
make setup          # Install dependencies and Playwright browsers
make test           # Run tests
make list           # List Chrome browser profiles
make run            # Run example automation
make lint           # Run linting with ruff
make fmt            # Format code with ruff and black
make clean          # Clean up generated files
```

## Project Structure

```
applicant/
├── data/
│   └── do-not-apply.txt      # Domains to exclude from job applications
├── src/
│   └── webbot/
│       ├── __init__.py        # Package initialization
│       ├── cli.py             # Command line interface
│       ├── profiles.py        # Chrome profile discovery
│       ├── browser.py         # Browser launch and management
│       ├── extract.py         # Text extraction utilities
│       ├── apply_finder.py    # Apply URL discovery logic
│       ├── ai_search.py       # OpenAI-assisted search
│       └── config.py          # Configuration and environment
├── tests/
│   ├── test_profiles.py       # Profile discovery tests
│   └── test_cli_smoke.py     # CLI smoke tests
├── .env.example               # Environment variables template
├── pyproject.toml             # Poetry configuration
├── Makefile                   # Build automation
└── README.md                  # This file
```

## Usage Examples

### List Chrome Profiles

```bash
poetry run python -m webbot.cli list-browser-profiles
```

Output:
```
- name: Person 1
  dir_name: Default  (default)
  path: /Users/user/Library/Application Support/Google/Chrome/Default
  email: user@example.com

- name: Work Profile
  dir_name: Profile 1
  path: /Users/user/Library/Application Support/Google/Chrome/Profile 1
  email: work@company.com
```

### Open Browser with Profile

```bash
# Use default profile
poetry run python -m webbot.cli run

# Use specific profile
poetry run python -m webbot.cli run --use-browser-profile "Profile 1"

# Visit a job page and analyze
poetry run python -m webbot.cli run \
  --use-browser-profile "Default" \
  --initial-job-url "https://www.workatastartup.com/jobs/74132"
```

### Domain Filtering

Add domains to exclude from job applications in `data/do-not-apply.txt`:

```
# One domain per line; subdomains will match implicitly.
workatastartup.com
angel.co
```

When a job page from these domains is visited, the tool will:
1. Extract the page text
2. Search for the company's own careers/apply page
3. Present the best "applyable" URL

## Configuration

### OpenAI Integration

To enable OpenAI-assisted search for company careers pages:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

3. The tool will automatically use AI to generate better search queries when finding apply URLs.

### Chrome Profile Selection

The tool automatically discovers Chrome profiles from standard locations:
- **macOS**: `~/Library/Application Support/Google/Chrome`
- **Windows**: `%LOCALAPPDATA%\Google\Chrome\User Data`
- **Linux**: `~/.config/google-chrome` or `~/.config/chromium`

## Testing

Run the test suite:

```bash
make test
```

Run specific test categories:

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/test_profiles.py
```

## Development

### Code Quality

```bash
# Check code quality
make lint

# Auto-format code
make fmt
```

### Adding New Features

1. **New CLI Commands**: Add to `src/webbot/cli.py`
2. **Profile Enhancements**: Extend `src/webbot/profiles.py`
3. **Browser Features**: Add to `src/webbot/browser.py`
4. **Search Logic**: Enhance `src/webbot/apply_finder.py`

## Troubleshooting

### Common Issues

#### Chrome Profile Not Found

```bash
# Make sure Chrome has been launched at least once
# Check if profiles exist
make list
```

#### Browser Launch Fails

If Chrome is already running with the selected profile:
1. Close all Chrome windows
2. Try again with `make run`

#### OpenAI API Errors

```bash
# Check your API key
cat .env

# Verify the key is valid
poetry run python -c "from webbot.ai_search import get_openai_client; get_openai_client()"
```

#### Permission Issues

On macOS, grant accessibility permissions to Terminal/VS Code:
- System Preferences > Security & Privacy > Privacy > Accessibility

### Debug Mode

For debugging, you can run individual components:

```python
# Test profile discovery
from webbot.profiles import discover_profiles
profiles = discover_profiles()
print(profiles)

# Test browser launch
from webbot.browser import launch_with_profile
# ... browser automation code
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
4. Include your operating system, Chrome version, and any error messages
