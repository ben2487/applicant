# WebBot - Intelligent Job Application Assistant

A Python browser automation tool using Playwright and OpenAI, designed to intelligently analyze job postings and find direct application URLs using agentic AI. Now with a modern React frontend and Flask backend for enhanced monitoring and control.

## Features

- **Chrome Profile Management**: Discover and list Chrome browser profiles with human-readable names and email identifiers
- **User Profile System**: Manage user-specific data including secrets, job tracking, and resume cache
- **Smart Browser Launch**: Automatically attach to existing Chrome instances or launch new ones with profiles
- **Structured Job Analysis**: Extract job details including title, company, requirements, work mode, locations, and compensation
- **Agentic AI Apply Discovery**: Use OpenAI function-calling to intelligently find official company apply URLs
- **Dual Extraction Modes**: LLM-enhanced extraction (default) or fast heuristic-only mode
- **Domain Filtering**: Maintain a do-not-apply domain list for job aggregation sites
- **Comparison Output**: Compare agentic AI vs. legacy heuristic approaches
- **CLI Interface**: Easy-to-use Typer-based command line interface
- **Web Interface**: Modern React frontend with real-time monitoring
- **Backend API**: Flask REST API with PostgreSQL database
- **Testing**: Comprehensive test suite with pytest

## Features

- **Chrome Profile Management**: Discover and list Chrome browser profiles with human-readable names and email identifiers
- **User Profile System**: Manage user-specific data including secrets, job tracking, and resume cache
- **Smart Browser Launch**: Automatically attach to existing Chrome instances or launch new ones with profiles
- **Structured Job Analysis**: Extract job details including title, company, requirements, work mode, locations, and compensation
- **Agentic AI Apply Discovery**: Use OpenAI function-calling to intelligently find official company apply URLs
- **Dual Extraction Modes**: LLM-enhanced extraction (default) or fast heuristic-only mode
- **Domain Filtering**: Maintain a do-not-apply domain list for job aggregation sites
- **Comparison Output**: Compare agentic AI vs. legacy heuristic approaches
- **CLI Interface**: Easy-to-use Typer-based command line interface
- **Testing**: Comprehensive test suite with pytest

## Requirements

- Python 3.10+
- Poetry (for dependency management)
- Chrome browser installed
- Playwright browsers
- OpenAI API key (for AI-enhanced features)

## Quick Start

### Web Interface (Recommended)

The easiest way to use WebBot is through the modern web interface:

1. **Start the Backend**:
```bash
# Install dependencies
poetry install

# Start PostgreSQL
make db-up
make db-wait
make db-reset

# Start Flask backend
DATABASE_URL="postgresql://localhost/webbot" poetry run python -c "from src.backend.app import create_app; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=False)" &
```

2. **Start the Frontend**:
```bash
cd frontend
npm install
npm run dev
```

3. **Access the Application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

The web interface provides:
- **Applications Table**: View all automation runs with sorting and filtering
- **New Application**: Start new runs with URL input and live monitoring
- **Real-time Logs**: Live console output during automation
- **Embedded Browser**: Browser view during automation (planned)

### Command Line Interface

For advanced users or automation scripts:

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

### 3. Configure OpenAI (Optional)

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 4. List Available Profiles

```bash
# List Chrome browser profiles
make list-browser

# List user profiles (will be empty initially)
make list-user

# Or run directly
poetry run python -m webbot.cli list-browser-profiles
poetry run python -m webbot.cli list-user-profiles
```

### 5. Test OpenAI Integration

```bash
# Test your OpenAI API key
make test-ai

# Or run directly
poetry run python -m webbot.cli test-openai-key
```

### 6. Run Intelligent Job Analysis

```bash
# Run with AI-enhanced extraction (default)
make run

# Run with heuristic extraction only (no OpenAI required)
make run-heuristic

# Or customize the profiles and URL
poetry run python -m webbot.cli run "MyUserProfile" \
  --use-browser-profile "Work" \
  --initial-job-url "https://example.com/jobs/123" \
  --ai-mode openai
```

## Available Commands

```bash
make help           # Show available commands
make setup          # Install dependencies and Playwright browsers
make test           # Run tests
make list-browser   # List Chrome browser profiles
make list-user      # List user profiles
make test-ai        # Test OpenAI API key
make run            # Run with AI-enhanced extraction
make run-heuristic  # Run with heuristic extraction only
make lint           # Run linting with ruff
make fmt            # Format code with ruff and black
make clean          # Clean up generated files
```

## Project Structure

```
applicant/
├── data/
│   └── do-not-apply.txt      # Domains to exclude from job applications
├── user_profiles/            # User-specific data (created automatically)
│   └── [UserName]/
│       └── secrets.json      # User secrets (Google Drive, etc.)
├── src/
│   ├── webbot/               # Original CLI automation package
│   │   ├── __init__.py        # Package initialization
│   │   ├── cli.py             # Command line interface
│   │   ├── browser_profiles.py # Chrome browser profile discovery
│   │   ├── user_profiles.py   # User profile management
│   │   ├── browser.py         # Browser launch and management
│   │   ├── extract.py         # Text extraction utilities
│   │   ├── struct_extract.py  # Structured job data extraction
│   │   ├── apply_finder.py    # Legacy apply URL discovery
│   │   ├── ai_search.py       # OpenAI client and search utilities
│   │   ├── agents/
│   │   │   ├── __init__.py    # Agents package
│   │   │   └── find_apply_page.py  # Agentic apply URL discovery
│   │   └── config.py          # Configuration and environment
│   └── backend/              # Flask backend API
│       ├── __init__.py        # Backend package
│       ├── app.py             # Flask application factory
│       ├── database/          # Database layer
│       │   ├── connection.py  # PostgreSQL connection management
│       │   ├── repository.py  # Data access layer
│       │   └── schema.sql     # Database schema
│       ├── models/            # Pydantic data models
│       │   └── entities.py    # Database entity models
│       ├── api/               # REST API endpoints
│       │   ├── runs.py        # Run management API
│       │   └── users.py       # User management API
│       └── websocket/         # WebSocket handlers (planned)
│           └── handlers.py    # Real-time communication
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   ├── RunTable.tsx   # Applications table
│   │   │   └── NewApplication.tsx # New run form
│   │   ├── lib/              # Utilities and API client
│   │   │   ├── api.ts        # Backend API client
│   │   │   └── utils.ts      # Utility functions
│   │   ├── types/            # TypeScript type definitions
│   │   │   └── api.ts        # API response types
│   │   ├── App.tsx           # Main application component
│   │   └── main.tsx          # Application entry point
│   ├── package.json          # Node.js dependencies
│   └── vite.config.ts        # Vite configuration
├── tests/
│   ├── test_profiles.py       # Profile discovery tests
│   ├── test_cli_smoke.py     # CLI smoke tests
│   └── test_backend.py       # Backend API tests
├── .env.example               # Environment variables template
├── pyproject.toml             # Poetry configuration
├── Makefile                   # Build automation
└── README.md                  # This file
```

## Profile System

WebBot uses two distinct profile systems:

### Browser Profiles
Chrome browser profiles that contain cookies, sessions, and browser settings:
- Discovered automatically from Chrome installation
- Used for browser automation and session management
- Optional: `--use-browser-profile "ProfileName"`

### User Profiles
Local directories containing user-specific data:
- Created automatically when first used
- Contains secrets, job tracking, resume cache
- **Required**: `USER_PROFILE` argument

## Usage Examples

### List Available Profiles

```bash
# List Chrome browser profiles
poetry run python -m webbot.cli list-browser-profiles
```

Output:
```
- name: Default
  dir_name: Default  (default)
  path: /Users/user/Library/Application Support/Google/Chrome/Default
  email: user@example.com

- name: Work
  dir_name: Profile 1
  path: /Users/user/Library/Application Support/Google/Chrome/Profile 1
  email: work@company.com
```

```bash
# List user profiles
poetry run python -m webbot.cli list-user-profiles
```

Output:
```
- name: JohnDoe
  path: user_profiles/JohnDoe
  has_google_drive: True

- name: WorkAccount
  path: user_profiles/WorkAccount
  has_google_drive: False
```

### Analyze a Job Posting with AI

```bash
poetry run python -m webbot.cli run "JohnDoe" \
  --use-browser-profile "Work" \
  --initial-job-url "https://www.workatastartup.com/jobs/74132" \
  --ai-mode openai
```

This will:
1. Create user profile "JohnDoe" if it doesn't exist
2. Launch Chrome with the "Work" browser profile (or attach to existing instance)
3. Navigate to the job URL
4. Extract and display structured job data:
   - Job title and company name
   - Work mode (remote/hybrid/in-office)
   - Locations and requirements
   - Compensation currencies and non-US indicators
5. Use agentic AI to find the official company apply URL
6. Compare with legacy heuristic approach
7. Display colored LLM prompts and responses

### Run with Heuristic Extraction Only

```bash
poetry run python -m webbot.cli run "TestUser" \
  --initial-job-url "https://example.com/jobs/123" \
  --ai-mode llm_off
```

This runs without requiring OpenAI API key, using only fast heuristic extraction.

## Configuration

### OpenAI API Key

Create a `.env` file in the project root:

```bash
# Copy the example
cp .env.example .env

# Edit .env and add your key
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### User Profile Secrets

User profiles automatically create a `secrets.json` file for storing credentials:

```json
{
  "google_drive_credentials": {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "refresh_token": "your-refresh-token"
  }
}
```

### Do-Not-Apply Domains

Edit `data/do-not-apply.txt` to add domains where you don't want to apply directly:

```
# One domain per line; subdomains will match implicitly
workatastartup.com
angel.co
indeed.com
```

## Testing

```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_profiles.py

# Run with verbose output
poetry run pytest -v
```

## Troubleshooting

### Chrome Profile Issues

- **No profiles found**: Make sure Chrome has been launched at least once
- **Profile in use**: Close other Chrome instances or use a different profile
- **Permission errors**: Check Chrome profile directory permissions

### User Profile Issues

- **Profile not found**: User profiles are created automatically when first used
- **Permission errors**: Check write permissions in the project directory
- **Corrupted secrets**: Delete the `secrets.json` file to reset

### OpenAI Issues

- **Missing API key**: Set `OPENAI_API_KEY` in your `.env` file
- **Invalid API key**: Verify your key is correct and has billing enabled
- **Rate limits**: The tool uses GPT-4o-mini which has generous rate limits

### Browser Launch Issues

- **Chrome not found**: Install Chrome browser
- **Playwright browsers**: Run `make setup` to install Playwright browsers
- **Port conflicts**: The tool automatically handles port conflicts by attaching to existing instances

## Development

### Code Quality

```bash
# Format code
make fmt

# Run linting
make lint

# Run tests
make test
```

### Adding New Agents

The `agents/` directory is designed for future LLM-guided agents:

1. Create a new file in `src/webbot/agents/`
2. Implement your agent logic
3. Import and use in `cli.py`

### Extending User Profiles

User profiles are designed to be extensible:

1. Add new fields to `UserSecrets` in `user_profiles.py`
2. Create new data files in the user profile directory
3. Implement profile-specific functionality

### Extending Structured Extraction

Modify `struct_extract.py` to add new fields to the `JobPostingExtract` model and corresponding extraction logic.
