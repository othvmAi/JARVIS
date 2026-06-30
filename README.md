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
Entry Workflow ─── Normalize → Auth → Rate Limit
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
- **Replaceable Memory** — n8n-static (default), SQLite, PostgreSQL
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
│   └── logger.json                # Structured logging
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
│   ├── core/           # 10 core orchestration workflows
│   └── capabilities/   # 10 capability agent workflows
├── ARCHITECTURE.md     # Full architecture documentation
├── WORKFLOWS.md        # Complete workflow reference
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

2. **Import workflows into n8n**
   - Open n8n → Workflows → Import
   - Import each JSON file from `workflow/core/` and `workflow/capabilities/`
   - Workflows are imported with their correct names (e.g., `JARVIS — Entry`)

3. **Configure credentials in n8n**
   - **Telegram**: Create a bot via [@BotFather](https://t.me/BotFather), add Telegram credentials in n8n
   - **Google**: Set up OAuth2 or API key credentials for Google APIs
   - **LLM**: Configure your preferred LLM provider (Groq, Ollama, OpenAI, Anthropic)

4. **Set environment variables**
   - Add all required variables in n8n → Settings → Environment Variables
   - See [Configuration](#configuration) below

5. **Activate the Entry workflow**
   - Activate `JARVIS — Entry` in n8n
   - Set up Telegram webhook to point to your n8n instance

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
| `GOOGLE_API_KEY` | Google API key |
| `GOOGLE_ACCESS_TOKEN` | Google OAuth access token |

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
| `MEMORY_PROVIDER` | `n8n-static` | n8n-static, sqlite, postgres |
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

Every request gets a `traceId` for end-to-end debugging.

---

## Roadmap

- [ ] Additional mail providers (Outlook, IMAP)
- [ ] Additional calendar providers (CalDAV, Outlook)
- [ ] Additional storage providers (OneDrive, Dropbox)
- [ ] Persistent memory (SQLite, PostgreSQL with pgvector)
- [ ] Additional response channels (Discord, Slack)
- [ ] OAuth token refresh for Google APIs
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

## Credits

- [n8n](https://n8n.io) — Workflow automation platform
- [Ollama](https://ollama.com) — Local LLM serving
- [Groq](https://groq.com) — Fast LLM inference
