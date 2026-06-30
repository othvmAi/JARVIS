# JARVIS — AI Operating Assistant

**Capability-first, adapter-based AI assistant powered by n8n.** Replaceable providers, permanent capabilities.

JARVIS is a personal AI operating assistant built on a **capability-first architecture**. Each capability (Mail, Calendar, Storage, etc.) is a first-class citizen with a replaceable provider adapter. Currently, Google is the primary provider, but the architecture is designed for any provider.

---

## Vision

Build a personal AI assistant where:

- **Capabilities are permanent** — Mail, Calendar, Storage, Search, Memory, LLM, etc.
- **Providers are replaceable** — Swap Gmail for Outlook, Google Calendar for CalDAV, without changing core logic
- **Everything is a workflow** — n8n orchestrates every step: classify, route, execute, respond, remember
- **Simple and modular** — No enterprise patterns, no unnecessary abstraction

---

## Architecture

```
User Message
    │
    ▼
Entry Workflow ─── Normalize → Input Processor → Auth → Rate Limit
    │
    ▼
Intent Classifier (LLM Adapter) ─── Classify intent + extract params
    │
    ▼
Capability Router ─── Route to capability by intent prefix
    │
    ▼
Capability Agent ─── Build request → HTTP → Format response
    │
    ▼
Response Sender ─── Format → Deliver (Telegram / Webhook)
    │
    ▼
Memory Store ─── Save session → Extract facts → Save facts
```

---

## Core Features

- **Single Entry Point** — Telegram and Webhook unified into one normalized request
- **Intent Classification** — LLM-based (any provider) — 27 intents across 10 capabilities
- **Capability Router** — Config-driven routing by intent prefix
- **Replaceable LLM** — Groq (default), Ollama, OpenAI, Anthropic
- **Replaceable Memory** — SQLite (default), n8n-static (fallback), PostgreSQL
- **Response Channels** — Telegram, Webhook (website)
- **Global Error Handling** — Structured logging with trace IDs
- **Auth & Rate Limiting** — Owner-only mode, per-user rate limiting
- **Session & Fact Memory** — Saves conversations, extracts facts via LLM

---

## Current Capabilities

| Capability | Intents | Current Provider |
|---|---|---|
| **Mail** | search, read, send, delete | Google Gmail |
| **Calendar** | list, create, delete | Google Calendar |
| **Storage** | list, search, upload, download, delete | Google Drive |
| **Contacts** | list, search, create | Google Contacts |
| **Docs** | create, read, edit | Google Docs |
| **Slides** | create | Google Slides |
| **Sheets** | read, write, create | Google Sheets |
| **Tasks** | list, create, update, delete | Google Tasks |
| **Knowledge** | query | WolframAlpha / Wikipedia / SerpAPI |
| **Chat** | general conversation | LLM Adapter |

### Future Providers (architecture supports, not yet implemented)

**Mail:** Outlook, IMAP, SMTP  
**Calendar:** CalDAV, Outlook Calendar  
**Storage:** Dropbox, OneDrive, S3, Local FS  
**LLM:** OpenRouter, Gemini, local models  
**Memory:** Chroma, Qdrant, Redis  
**Channels:** Discord, Slack, Matrix

---

## Workflow Overview

All workflows are n8n JSON files in `workflow/`:

```
workflow/
├── core/                          # Core orchestration
│   ├── entry.json                 # Single entry point
│   ├── intent-classifier.json     # LLM intent classification
│   ├── capability-router.json     # Intent → capability routing
│   ├── llm-adapter.json           # Unified LLM interface
│   ├── memory-adapter.json        # Unified memory interface
│   ├── memory-store.json          # Session + fact persistence
│   ├── response-sender.json       # Response formatting + delivery
│   ├── config-validator.json      # Env var validation
│   ├── error-handler.json         # Global error handling
│   └── google-auth.json           # OAuth2 token refresh
└── capabilities/                  # Capability agents
    ├── mail/gmail-agent.json
    ├── calendar/calendar-agent.json
    ├── storage/drive-agent.json
    ├── contacts/contacts-agent.json
    ├── docs/docs-agent.json
    ├── slides/slides-agent.json
    ├── sheets/sheets-agent.json
    ├── tasks/tasks-agent.json
    ├── knowledge/knowledge-agent.json
    └── chat/general-chat.json
```

---

## Project Structure

```
├── workflow/
│   ├── core/           # 11 core orchestration workflows
│   └── capabilities/   # 10 capability agent workflows
├── ARCHITECTURE.md     # Full architecture documentation
├── WORKFLOWS.md        # Complete workflow reference
├── TESTING.md          # Testing guide & smoke test sequence
├── CONTRIBUTING.md     # Development guidelines
├── .env.example        # Environment variable reference
├── README.md           # This file
└── LICENSE             # MIT License
```

---

## Installation

### Prerequisites

- [n8n](https://n8n.io) — Self-hosted or cloud (v1.0+ recommended)
- Python 3.10+ (optional, for local Ollama LLM)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/othvmAi/JARVIS.git
   cd JARVIS
   ```

2. **Start the SQLite Memory Server** (required for persistent memory)
   ```bash
   pip install flask
   python scripts/sqlite-memory-server.py
   ```
   The server runs on `http://localhost:8710`. See [SQLite Memory Server](#sqlite-memory-server) for details.

3. **Import workflows into n8n**
   - Open n8n → Workflows → Import
   - Import each JSON file from `workflow/core/` and `workflow/capabilities/`
   - Workflows are imported with their correct names (e.g., `JARVIS — Entry`)

4. **Configure credentials in n8n**
   - **Telegram**: Create a bot via [@BotFather](https://t.me/BotFather), add Telegram credentials in n8n
   - **Google**: Set up OAuth2 credentials. See [Google OAuth Setup](#google-oauth-setup) below.
   - **LLM**: Configure your preferred LLM provider (Groq, Ollama, OpenAI, Anthropic)

5. **Set environment variables**
   - Copy variables from `.env.example` into n8n → Settings → Environment Variables
   - All required variables are marked; optional ones have defaults shown
   - See [Configuration](#configuration) below for details

6. **Activate the Entry workflow**
   - Activate only `JARVIS — Entry` in n8n (sub-workflows are called via `executeWorkflow` and don't need activation)
   - Set up Telegram webhook to point to your n8n instance (see [Finding Your Webhook URL](#finding-your-webhook-url))

---

## Configuration

All configuration is via n8n environment variables.

### Required

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Secret for Telegram webhook validation |
| `OWNER_USER_ID` | Your Telegram user ID (numeric) |
| `LLM_API_KEY` | API key for LLM provider |
| `LLM_API_BASE` | LLM API base URL |
| `LLM_MODEL` | LLM model name |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Google OAuth refresh token |

### Optional

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | groq, ollama, openai, anthropic |
| `OLLAMA_API_BASE` | `http://localhost:11434` | Ollama base URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | OpenAI base URL |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3-haiku-20240307` | Anthropic model |
| `MEMORY_PROVIDER` | `sqlite` | sqlite, n8n-static, postgres |
| `SQLITE_MEMORY_URL` | `http://localhost:8710` | SQLite memory server URL |
| `SQLITE_MEMORY_PATH` | — | SQLite memory DB path |
| `WOLFRAM_ALPHA_APPID` | — | WolframAlpha App ID |
| `SERPAPI_API_KEY` | — | SerpAPI key |
| `AUTH_MODE` | `protected` | open, protected |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per user |
| `TELEGRAM_MAX_MESSAGE_LENGTH` | `4000` | Max message length |
| `LOG_LEVEL` | `info` | debug, info, warn, error |

---

## How JARVIS Works

1. **User sends a message** via Telegram or a website webhook
2. **Entry workflow** normalizes the request, authenticates the user, and applies rate limiting
3. **Intent Classifier** uses the LLM Adapter to classify the intent (e.g., `gmail_search`) and extract parameters
4. **Capability Router** routes to the correct capability agent based on intent prefix
5. **Capability Agent** builds a provider-specific API request, executes it, and formats the response
6. **Response Sender** delivers the response back through the original channel
7. **Memory Store** saves the session and extracts facts for future reference

Every request gets a unique `traceId` (format: `sess_<epoch>_<6char-random>`) for end-to-end debugging.

---

## Roadmap

- [ ] Additional mail providers (Outlook, IMAP)
- [ ] Additional calendar providers (CalDAV, Outlook)
- [ ] Additional storage providers (OneDrive, Dropbox)
- [ ] Additional memory providers (PostgreSQL with pgvector)
- [ ] Additional response channels (Discord, Slack)
- [x] OAuth token refresh for Google APIs
- [x] Persistent memory (SQLite)
- [ ] Web UI dashboard for configuration
- [ ] Workflow testing framework
- [ ] Docker Compose for one-click deployment

---

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/othvmAi/JARVIS).

---

## License

MIT — free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Google OAuth Setup

JARVIS uses OAuth2 refresh tokens for Google API access. Static access tokens and API keys are no longer used for user data APIs.

### Step 1: Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing
3. Enable required APIs: Gmail, Calendar, Drive, People, Docs, Slides, Sheets, Tasks
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose **Desktop application** as application type
6. Copy the **Client ID** and **Client Secret**

### Step 2: Get a Refresh Token

```bash
# Set your credentials
CLIENT_ID="your-client-id"
CLIENT_SECRET="your-client-secret"

# Generate the auth URL (open in browser)
echo "https://accounts.google.com/o/oauth2/auth?client_id=$CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/gmail.modify%20https://www.googleapis.com/auth/calendar%20https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/documents%20https://www.googleapis.com/auth/presentations%20https://www.googleapis.com/auth/spreadsheets%20https://www.googleapis.com/auth/tasks"

# Exchange the authorization code for tokens
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET&code=AUTHORIZATION_CODE&redirect_uri=urn:ietf:wg:oauth:2.0:oob&grant_type=authorization_code"
```

Save the `refresh_token` from the response.

### Step 3: Set Environment Variables

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token
```

The `JARVIS — Google Auth` workflow automatically refreshes the access token using these credentials.

---

## Finding Your Webhook URL

JARVIS exposes two webhook endpoints (hardcoded — update in `entry.json` if needed):

| Endpoint | Path | Purpose |
|---|---|---|
| Telegram | `/webhook/jarvis-telegram` | Telegram bot updates (set via BotFather `setWebhook`) |
| Website | `/webhook/jarvis-webhook-site` | Direct HTTP API access |

**URL format:**
```
http(s)://YOUR_N8N_HOST:5678/webhook/jarvis-webhook-site
```

- For **local testing**, use [ngrok](https://ngrok.com) to expose your n8n instance:
  ```bash
  ngrok http 5678
  # → Use the https URL as your n8n base URL
  ```
- For **production**, use your public n8n domain (reverse-proxied with HTTPS).
- The webhook path is hardcoded in the Webhook node in `entry.json`. To change it, edit the `path` parameter in the node configuration and re-import.

**Setup verification:**
```bash
curl -X POST https://YOUR_N8N_URL/webhook/jarvis-webhook-site \
  -H "Content-Type: application/json" \
  -d '{"text": "ping", "session_id": "setup-test"}'
```
Expected response: `{"responseText": "I'm JARVIS, your AI assistant. How can I help?", "success": true}`

---

## SQLite Memory Server

The SQLite memory server provides persistent storage for sessions and facts.

### Quick Start

```bash
pip install flask
python scripts/sqlite-memory-server.py
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/sessions` | Save a session |
| `GET` | `/sessions/<id>` | Get a session |
| `POST` | `/facts` | Save facts |
| `GET` | `/facts` | Get facts (filter by `user_id`, `category`) |

### Configuration

| Env Variable | Default | Description |
|---|---|---|
| `SQLITE_MEMORY_PATH` | `scripts/jarvis_memory.db` | Database file path |
| `SQLITE_MEMORY_PORT` | `8710` | Server port |

### Production Deployment

```bash
# Using nohup
nohup python scripts/sqlite-memory-server.py > memory-server.log 2>&1 &

# Using Docker (if you prefer)
# Or use a systemd service for auto-restart
```

---

## Credits

- [n8n](https://n8n.io) — Workflow automation platform
- [Ollama](https://ollama.com) — Local LLM serving
- [Groq](https://groq.com) — Fast LLM inference
