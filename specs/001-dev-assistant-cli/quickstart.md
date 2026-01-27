# Quickstart: Developer Assistant CLI

## Prerequisites

- Python 3.11+
- GCP project with Vertex AI API enabled
- API credentials for desired integrations

## Installation

```bash
# Clone the repository
git clone https://github.com/singlarity-seekers/singlarity.git
cd singlarity

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Initial Setup

### 1. Configure Workspace

```bash
# Initialize configuration (creates ~/.devassist/)
devassist init

# This creates:
# - ~/.devassist/config.yaml (main configuration)
# - ~/.devassist/cache/ (context cache)
# - ~/.devassist/briefs/ (generated briefs)
```

### 2. Configure GCP (Required)

```bash
# Option A: Use gcloud CLI
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Option B: Service account (for deployment)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Verify Vertex AI access
devassist ai test
```

### 3. Add Context Sources

#### Gmail

```bash
# Start OAuth2 flow (opens browser)
devassist config add gmail

# Follow prompts to authorize access
# Tokens stored in ~/.devassist/gmail_token.json
```

#### Slack

```bash
# Option A: Bot token (simpler)
devassist config add slack --token xoxb-your-bot-token

# Option B: OAuth (full access)
devassist config add slack --oauth
```

#### JIRA

```bash
# Requires API token from https://id.atlassian.com/manage-profile/security/api-tokens
devassist config add jira \
  --url https://yourcompany.atlassian.net \
  --email your.email@company.com \
  --token YOUR_API_TOKEN
```

#### GitHub

```bash
# Requires PAT from https://github.com/settings/tokens
devassist config add github --token ghp_your_token
```

### 4. Verify Configuration

```bash
# List configured sources
devassist config list

# Test all connections
devassist config test

# Expected output:
# ✓ gmail: connected (user@gmail.com)
# ✓ slack: connected (workspace: MyCompany)
# ✓ jira: connected (project: PROJ)
# ✓ github: connected (user: username)
```

## Usage

### Morning Brief

```bash
# Generate morning brief (queries all sources)
devassist brief

# Brief with specific sources
devassist brief --sources gmail,jira

# Force refresh (ignore cache)
devassist brief --refresh

# JSON output (for scripting)
devassist brief --json
```

### Configuration Management

```bash
# Show current config
devassist config show

# Remove a source
devassist config remove slack

# Reset all config
devassist config reset --confirm
```

### Preferences

```bash
# Add priority keyword
devassist prefs add --keyword "urgent" --weight 1.0

# View preferences
devassist prefs list

# Reset preferences
devassist prefs reset
```

### EC2 Sandbox (Optional)

```bash
# Add sandbox instance
devassist sandbox add --instance-id i-0abc123 --name "dev-box"

# Check status
devassist sandbox status

# Start/stop
devassist sandbox start dev-box
devassist sandbox stop dev-box
```

## Example Session

```bash
$ devassist brief

⏳ Fetching context from 4 sources...
  ✓ gmail (12 items, 0.8s)
  ✓ slack (8 items, 0.5s)
  ✓ jira (5 items, 0.6s)
  ✓ github (3 items, 0.4s)

🧠 Generating summary with Gemini...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Morning Brief - January 27, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Highlights
  • PR #142 needs your review (GitHub, @teammate)
  • PROJ-456 blocked on API approval (JIRA, High Priority)
  • Team standup in 30 minutes (Gmail, calendar)

🔴 Urgent (3)
  1. Security patch review requested - PR #142
  2. Customer escalation in #support - needs response
  3. Deployment approval pending for v2.3.0

📋 Follow Up (5)
  1. Code review feedback on PR #138
  2. PROJ-123 ready for testing
  3. Weekly report due Friday
  ...

📝 Action Items
  • Review PR #142 (due: today)
  • Respond to #support thread (due: ASAP)
  • Update PROJ-456 status (due: EOD)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated in 2.3s | 28 items processed | Cache expires in 15m
```

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate Gmail
devassist config refresh gmail

# Check token validity
devassist config test gmail --verbose
```

### API Rate Limits

The CLI automatically handles rate limits with exponential backoff. If you see rate limit warnings:

```bash
# Use cached data
devassist brief --cached-only

# Check rate limit status
devassist config status
```

### AI Service Issues

```bash
# Test Vertex AI connection
devassist ai test

# Fall back to raw data (no AI summary)
devassist brief --no-ai
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=devassist

# Run specific test
pytest tests/unit/test_brief_service.py -v

# Type checking
mypy src/

# Linting
ruff check src/
```
