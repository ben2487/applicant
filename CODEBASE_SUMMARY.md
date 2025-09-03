# WebBot - Intelligent Job Application Assistant

## High-Level Overview

WebBot is a sophisticated Python browser automation system designed to intelligently analyze job postings and automatically find direct application URLs using agentic AI. The system combines Playwright browser automation with OpenAI's GPT models to create a fully automated job application pipeline.

## Core Functionality

### 🎯 **Primary Purpose**
- **Intelligent Job Discovery**: Automatically find official company application URLs from job posting aggregators
- **Structured Data Extraction**: Parse job postings to extract title, company, requirements, compensation, and work mode
- **Automated Form Filling**: Fill out job application forms with user data and resume uploads
- **Multi-Stage Navigation**: Navigate complex ATS (Applicant Tracking Systems) like Ashby, Greenhouse, and Lever

### 🏗️ **Architecture**
The system uses a **three-stage deterministic approach** for finding job application URLs:

1. **Stage 1**: Find official company website using LLM-powered search
2. **Stage 2**: Discover careers pages through comprehensive link analysis
3. **Stage 3**: Navigate to specific job postings and application forms

## Command Line Interface

### **Main Commands**

```bash
# Primary job application flow
python -m webbot.cli apply-flow <USER_PROFILE> [OPTIONS]

# Profile management
python -m webbot.cli list-browser-profiles    # List Chrome profiles
python -m webbot.cli list-user-profiles       # List user profiles
python -m webbot.cli create-user-profile      # Create new user profile

# Testing and utilities
python -m webbot.cli test-openai-key          # Test OpenAI API
python -m webbot.cli snapshot-url             # Take page snapshots
python -m webbot.cli extract-form-url         # Extract form schemas
```

### **Key Command Line Arguments**

#### `apply-flow` Command
```bash
python -m webbot.cli apply-flow <USER_PROFILE> \
  --initial-job-url "https://example.com/jobs/123" \
  --use-browser-profile "Work" \
  --apply-url-mode agentic5 \
  --vvvv \
  --headless \
  --hold-seconds 5 \
  --trace-html
```

**Required Arguments:**
- `USER_PROFILE`: User profile name (creates automatically if doesn't exist)

**Optional Arguments:**
- `--initial-job-url`: Starting job posting URL
- `--use-browser-profile`: Chrome browser profile to use
- `--apply-url-mode`: URL discovery method (`agentic5`, `agentic`, `legacy`, `compare`)
- `--vvvv`: Maximum verbosity (TRACE level logging)
- `--headless`: Run browser in headless mode
- `--hold-seconds`: Wait time before closing browser
- `--trace-html`: Generate HTML trace report

## Dependencies

### **Core Dependencies**
```toml
# Browser Automation
playwright = "^1.46"              # Browser automation framework
typer = "^0.12.0"                 # CLI framework

# AI and LLM
openai = "^1.40.0"                # OpenAI API client
ddgs = "^9.5.5"                   # DuckDuckGo search

# Data Processing
pydantic = "^2.6.0"               # Data validation
beautifulsoup4 = "^4.12.3"        # HTML parsing
tldextract = "^5.1.2"             # Domain extraction

# Logging and Tracing
eliot = "^1.16.0"                 # Structured logging
orjson = "^0.1.0"                 # Fast JSON processing

# Google Integration
google-api-python-client = "^2.141.0"
google-auth-httplib2 = "^0.2.0"
google-auth-oauthlib = "^1.2.1"

# Utilities
python-dotenv = "^1.0.1"          # Environment variables
requests = "^2.32.3"              # HTTP requests
```

### **Development Dependencies**
```toml
pytest = "^8.2.0"                 # Testing framework
pytest-playwright = "^0.5.0"      # Playwright testing
ruff = "^0.6.0"                   # Linting
black = "^24.8.0"                 # Code formatting
```

## Logging System

### **Eliot-Based Structured Logging**

The system uses **Eliot** for hierarchical, structured logging that generates both JSONL logs and HTML reports.

#### **Logging Levels**
- `TRACE` (5): Maximum verbosity, includes all LLM prompts/responses
- `DEBUG` (10): Detailed debugging information
- `INFO` (20): Standard operational messages

#### **Log Categories**
- `FIND_APPLY`: Job URL discovery operations
- `LLM`: All OpenAI API calls and responses
- `BROWSER`: Browser automation events
- `CONSOLE`: Captured console output
- `EXTRACT`: Data extraction operations
- `FORMS`: Form filling operations

#### **Key Logging Functions**
```python
# Initialize tracing
init_tracing(run_name="apply-flow", log_path=Path(".trace/log.jsonl"))

# Log events
event("FIND_APPLY", "INFO", "stage1_start", job_url=url)
action("llm_call", category="LLM")  # Context manager for operations
json_blob("LLM", "DEBUG", "prompt", {"content": prompt})
image("BROWSER", "DEBUG", "screenshot", png_data)
```

#### **HTML Report Generation**
- **Single File**: Self-contained HTML with embedded base64 images
- **Collapsible Tree**: Hierarchical view of operations
- **Embedded Artifacts**: Screenshots, JSON data, console output
- **Real-time Console**: Interleaved console output with timestamps

#### **Console Output Capture**
```python
enable_console_capture()  # Mirrors stdout/stderr to logs
```

All console output is automatically captured and interleaved into the HTML report with proper timestamps and formatting.

## System Components

### **Profile Management**
- **Browser Profiles**: Chrome profiles with cookies and sessions
- **User Profiles**: Local directories with secrets, resumes, and settings
- **Automatic Discovery**: Profiles are discovered and created automatically

### **Job Analysis Pipeline**
1. **URL Navigation**: Navigate to job posting
2. **Text Extraction**: Extract visible text from page
3. **Structured Parsing**: Use LLM to parse job details
4. **Apply URL Discovery**: Three-stage agentic approach
5. **Form Detection**: Find and analyze application forms
6. **Resume Selection**: Choose best resume for job
7. **Form Filling**: Automatically fill and submit forms

### **AI Integration**
- **OpenAI GPT-4o-mini**: Primary LLM for all operations
- **Function Calling**: Structured tool use for web search and analysis
- **Prompt Engineering**: Carefully crafted prompts for each task
- **Error Handling**: Robust fallback mechanisms

### **Browser Automation**
- **Playwright**: Cross-browser automation
- **Smart Launch**: Attach to existing Chrome or launch new instance
- **Profile Management**: Use existing Chrome profiles
- **Screenshot Capture**: Automatic screenshots at key points

## Configuration

### **Environment Variables**
```bash
OPENAI_API_KEY=sk-your-key-here    # Required for AI features
```

### **User Profile Structure**
```
user_profiles/
└── [UserName]/
    ├── settings.json              # User preferences
    ├── secrets.json               # API keys and credentials
    ├── resumes.json               # Resume metadata
    └── resume_pdf/                # Resume files
        └── [ResumeName]/
            ├── resume.pdf
            └── resume.txt
```

### **Domain Filtering**
```
data/do-not-apply.txt              # Domains to avoid
```

## Testing and Development

### **Test Suite**
- **Unit Tests**: Profile discovery, data extraction
- **Integration Tests**: End-to-end job application flow
- **Fixture Tests**: Real-world job posting examples

### **Code Quality**
- **Ruff**: Fast Python linter
- **Black**: Code formatter
- **Pytest**: Testing framework
- **Type Hints**: Full type annotation

## Success Metrics

The system has been successfully tested with:
- ✅ **End-to-End Automation**: Complete job application from URL to form submission
- ✅ **ATS Navigation**: Successfully navigates Ashby, Greenhouse, and other ATS systems
- ✅ **Form Detection**: Automatically finds and fills application forms
- ✅ **Resume Matching**: Intelligently selects best resume for each job
- ✅ **Error Recovery**: Robust handling of network issues and page changes

## File System Storage

### **User Profile Storage**

User profiles are stored in a hierarchical directory structure under the project root:

```
/Users/user/git/applicant/
└── user_profiles/
    ├── NewUser/
    │   ├── settings.json          # User preferences and configuration
    │   ├── secrets.json           # Encrypted credentials (Google Drive, etc.)
    │   ├── resumes.json           # Resume metadata and selection history
    │   └── resume_pdf/            # Resume files organized by type
    │       ├── Ben Mowery - Resume - AI source/
    │       │   ├── resume.pdf
    │       │   └── resume.txt
    │       ├── Ben Mowery - Resume - frontend/
    │       │   ├── resume.pdf
    │       │   └── resume.txt
    │       └── [Other resume types]/
    └── user_ben/
        └── [Similar structure]
```

#### **Profile File Formats**

**`settings.json`** - User preferences:
```json
{
  "human_name": "Ben Mowery",
  "google_drive_resume_path": "My Drive/J/Resume"
}
```

**`secrets.json`** - Encrypted credentials:
```json
{
  "google_drive_credentials": {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret", 
    "refresh_token": "your-refresh-token"
  },
  "google_drive_user": "user@example.com"
}
```

**`resumes.json`** - Resume metadata:
```json
{
  "resumes": [
    {
      "id": "ai_source",
      "name": "Ben Mowery - Resume - AI source",
      "path": "resume_pdf/Ben Mowery - Resume - AI source/resume.pdf",
      "text_path": "resume_pdf/Ben Mowery - Resume - AI source/resume.txt",
      "last_updated": "2024-01-15T10:30:00"
    }
  ]
}
```

#### **Profile Discovery and Management**
- **Automatic Creation**: Profiles are created automatically when first referenced
- **Path Resolution**: `get_user_profiles_root()` returns `project_root/user_profiles/`
- **Discovery**: `discover_user_profiles()` scans the directory for subdirectories
- **Validation**: Pydantic models ensure data integrity

### **Trace File Storage**

Trace files are stored in a dedicated `.trace/` directory with timestamped filenames:

```
/Users/user/git/applicant/
└── .trace/
    ├── apply-20241215-143022.jsonl    # Raw Eliot JSONL log
    ├── report-20241215-143022.html    # Generated HTML report
    ├── apply-20241215-150145.jsonl    # Previous run logs
    └── report-20241215-150145.html
```

#### **Trace File Generation**
- **JSONL Logs**: Raw structured logs in Eliot format
- **HTML Reports**: Self-contained HTML with embedded artifacts
- **Timestamping**: Format: `apply-YYYYMMDD-HHMMSS.jsonl`
- **Automatic Cleanup**: Files are not automatically deleted (manual cleanup required)

#### **Trace Configuration**
```python
# Default trace directory
trace_dir = repo_root() / ".trace"
log_path = trace_dir / f"apply-{timestamp}.jsonl"

# HTML report path (defaults if not specified)
html_path = trace_html or (repo_root() / ".trace" / f"report-{timestamp}.html")
```

### **Playwright Instance Management**

The system uses a sophisticated browser management strategy that balances performance with reliability:

#### **Browser Launch Strategy**

**1. Smart Attachment (Preferred)**
```python
async def try_attach_to_existing_chrome() -> tuple[BrowserContext, Page] | None:
    # Attempts to connect to existing Chrome instance
    # Uses remote debugging port
    # Returns None if attachment fails
```

**2. Profile-Based Launch (Fallback)**
```python
async def smart_launch_with_profile(profile: BrowserProfile) -> tuple[BrowserContext, Page]:
    # Launches new Chrome instance with specific profile
    # Uses persistent context for session management
    # Handles profile directory selection
```

#### **Browser Profile Integration**

**Chrome Profile Discovery**:
```python
# Profiles discovered from Chrome installation
/Users/user/Library/Application Support/Google/Chrome/
├── Default/                    # Default profile
├── Profile 1/                  # Work profile  
├── Profile 2/                  # Personal profile
└── [Other profiles]/
```

**Profile Selection**:
- **Automatic Detection**: Scans Chrome profile directories
- **Human-Readable Names**: Maps profile directories to display names
- **Email Association**: Extracts email from profile data
- **Session Persistence**: Maintains cookies and login state

#### **Browser Lifecycle Management**

**Launch Process**:
1. **Profile Resolution**: Find Chrome profile by name or directory
2. **Attachment Attempt**: Try to connect to existing Chrome instance
3. **Fallback Launch**: Launch new instance if attachment fails
4. **Context Creation**: Create browser context with profile
5. **Page Initialization**: Create new page for automation

**Cleanup Process**:
```python
# Automatic cleanup on exit
await playwright.stop()
await browser.close()
await context.close()
```

**Error Handling**:
- **Profile Conflicts**: Detects when profile is already in use
- **Permission Issues**: Handles Chrome directory access problems
- **Network Timeouts**: Manages page load timeouts gracefully
- **Resource Cleanup**: Ensures proper cleanup on failures

#### **Browser Configuration**

**Launch Arguments**:
```python
args = [
    f"--profile-directory={profile.dir_name}",  # Select specific profile
    "--remote-debugging-port=0",                # Enable remote debugging
    "--disable-web-security",                   # For testing (if needed)
    "--disable-features=VizDisplayCompositor"   # Performance optimization
]
```

**Context Settings**:
- **User Agent**: Maintains realistic browser fingerprint
- **Viewport**: Configurable screen resolution
- **Geolocation**: Optional location simulation
- **Permissions**: Camera, microphone, notifications

#### **Session Management**

**Persistent Context**:
- **Cookie Storage**: Maintains login sessions across runs
- **Local Storage**: Preserves form data and preferences
- **Cache Management**: Handles browser cache efficiently
- **Profile Isolation**: Each profile maintains separate data

**Multi-Tab Support**:
- **Context Sharing**: Multiple pages can share browser context
- **Tab Management**: Automatic tab creation and cleanup
- **Navigation State**: Tracks page history and state

## Future Extensions

The architecture supports easy extension for:
- **Additional ATS Systems**: New navigation patterns
- **Enhanced AI Agents**: More sophisticated job matching
- **Integration APIs**: Direct ATS API integration
- **Analytics Dashboard**: Application tracking and success metrics
