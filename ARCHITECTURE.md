# JARVIS Architecture

## Overview

JARVIS is a **single-owner, personal AI operating assistant** built on a **capability-first, adapter-based architecture** using n8n as the orchestration layer.

**Core Philosophy:**
- One owner, one instance, no multi-tenancy
- n8n-first: every feature as workflows when possible
- Capability-first: design around capabilities, not providers
- Simple: no enterprise patterns, no unnecessary abstractions
- Replaceable: adapters can be swapped without changing core

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRY POINT                              │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐   │
│  │  Telegram   │    │  Webhook    │───▶│  Normalize       │   │
│  │  Trigger    │    │  (Website)  │    │  Request         │   │
│  └─────────────┘    └─────────────┘    └────────┬─────────┘   │
│                                                  │             │
│                                                  ▼             │
│                                         ┌──────────────────┐   │
│                                         │  Input Processor │   │
│                                         │  (STT, fallbacks)│   │
│                                         └────────┬─────────┘   │
│                                                  │             │
│                                                  ▼             │
│                                         ┌──────────────────┐   │
│                                         │  Auth Gate       │   │
│                                         │  (OWNER_USER_ID) │   │
│                                         └────────┬─────────┘   │
│                                                  │             │
│                                                  ▼             │
│                                         ┌──────────────────┐   │
│                                         │  Rate Limit      │   │
│                                         │  (per user/min)  │   │
│                                         └────────┬─────────┘   │
└──────────────────────────────────────────────────┼─────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INTENT CLASSIFIER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM Adapter (Groq/Ollama/OpenAI/Anthropic)              │  │
│  │  System Prompt → Classify intent + extract params        │  │
│  └────────────────────────────┬──────────────────────────────┘  │
│                               │                                 │
│                               ▼                                 │
│                    ┌──────────────────┐                         │
│                    │  Parse & Validate │                        │
│                    │  Intent Output    │                        │
│                    └────────┬─────────┘                         │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPABILITY ROUTER                             │
│  intent → capability → adapter (config-driven, not hardcoded)  │
│                                                                 │
│  gmail_*        → mail       → gmail-agent                     │
│  calendar_*     → calendar   → calendar-agent                  │
│  drive_*        → storage    → drive-agent                     │
│  contacts_*     → contacts   → contacts-agent                  │
│  docs_*         → docs       → docs-agent                      │
│  slides_*       → slides     → slides-agent                    │
│  tasks_*        → tasks      → tasks-agent                     │
│  sheets_*       → sheets     → sheets-agent                    │
│  knowledge_*    → knowledge  → knowledge-agent                 │
│  general_chat   → chat       → general-chat                    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPABILITY AGENTS                            │
│  Each agent handles one capability using its provider adapter  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Mail    │ │Calendar │ │Storage  │ │Contacts │ │Docs     │  │
│  │ (Gmail) │ │ (GCal)  │ │(GDrive) │ │(GCont)  │ │(GDoc)   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │Slides   │ │Sheets   │ │Tasks    │ │Knowledge│ │Chat     │  │
│  │(GSlide) │ │(GSheet) │ │(GTask)  │ │(Wolfram │ │(LLM)    │  │
│  │         │ │         │ │         │ │ Wiki,   │ │         │  │
│  │         │ │         │ │         │ │ SerpAPI)│ │         │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE SENDER                              │
│  Format → Channel Adapter (Telegram, Webhook)                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY STORE                               │
│  Session save + Fact extraction (LLM) → Memory Adapter         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ SQLite          │  │ n8n-static      │  │ PostgreSQL     │  │
│  │ (default)       │  │ (fallback)      │  │ + pgvector     │  │
│  └─────────────────┘  └─────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Workflows

### `core/entry.json`
Single entry point for all inputs.
- **Triggers**: Telegram, Webhook (website)
- **Normalization**: Unifies Telegram + Web payloads into common shape; passes `inputFileId` for voice/photo/document and `inputLocation` for location
- **Auth**: Validates `OWNER_USER_ID` + Telegram webhook secret
- **Rate Limit**: Per-user, per-minute (configurable)
- **Input Processor**: Routes non-text inputs through `JARVIS — Input Processor` for preprocessing
- **Flow**: Normalize → Input Processor → Auth → Rate Limit → Intent Classifier → Capability Router → Merge → Response Sender + Memory Store

### `core/input-processor.json`
Preprocesses non-text inputs before intent classification.
- **voice**: Downloads audio via Telegram Bot API, transcribes with Groq Whisper (requires `GROQ_API_KEY`)
- **photo**: Placeholder message (image analysis not yet supported)
- **document**: Placeholder with filename
- **location**: Converts coordinates to text: "My location is: lat, lon"
- **unknown**: Generic fallback message
- Falls back gracefully if Groq Whisper fails or GROQ_API_KEY is not set

### `core/intent-classifier.json`
LLM-based intent classification.
- Calls `JARVIS — LLM Adapter` with classification prompt
- Validates intent against known enum (27 intents)
- **Param Schema Validation**: Each intent has a `PARAMS_SCHEMA` defining required + optional params. Hallucinated params are stripped with a warning log. Missing required params are set to null.
- Output: `{ intent, confidence, params }`

### `core/capability-router.json`
Routes intent to capability agent.
- Switch node mapping intent prefix → capability
- Calls appropriate capability agent via `executeWorkflow`
- **Env-var-driven routing**: Workflow names are configurable via env vars (`MAIL_AGENT_NAME`, `CALENDAR_AGENT_NAME`, etc.) — swapping a provider is a one-line env var change
- No provider logic — only capability routing

### `core/llm-adapter.json`
Unified LLM interface.
- Supports: Groq, Ollama, OpenAI, Anthropic
- Configured via `LLM_PROVIDER` env var
- Normalizes request/response across providers
- Used by: Intent Classifier, General Chat, Memory Store (fact extraction)

### `core/memory-adapter.json`
Unified memory interface.
- Actions: `save-session`, `get-session`, `save-facts`, `get-facts`
- Providers: SQLite (default), n8n-static (fallback), PostgreSQL (stub)
- Configured via `MEMORY_PROVIDER` env var

### `core/memory-store.json`
Orchestrates memory persistence.
- Save session → Extract facts (LLM) → Parse facts → Save facts
- Uses `memory-adapter` for storage
- Uses `llm-adapter` for fact extraction

### `core/response-sender.json`
Formats and delivers responses.
- Markdown → HTML conversion
- Telegram length truncation
- Channels: Telegram, Webhook (website)

### `core/config-validator.json`
Validates required environment variables on startup.
- Required: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, OWNER_USER_ID, LLM_API_KEY, LLM_API_BASE, LLM_MODEL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
- SQLITE_MEMORY_URL/SQLITE_MEMORY_PATH are optional (code defaults to http://localhost:8710 / scripts/jarvis_memory.db)
- Fails fast if missing

### `core/error-handler.json`
Global error handling.
- Logs error with traceId
- Sends user-friendly message to Telegram or Webhook
- No complex DLQ or retry logic — simple and effective

---

## Capability Workflows

Each capability lives in `workflow/capabilities/<capability>/` and uses a provider-specific adapter (currently only Google).

| Capability | Workflow | Provider | Intents |
|---|---|---|---|
| Mail | `mail/gmail-agent.json` | Gmail | gmail_search, gmail_read, gmail_send, gmail_delete |
| Calendar | `calendar/calendar-agent.json` | Google Calendar | calendar_list, calendar_create, calendar_delete |
| Storage | `storage/drive-agent.json` | Google Drive | drive_list, drive_search, drive_upload, drive_download, drive_delete |
| Contacts | `contacts/contacts-agent.json` | Google Contacts | contacts_list, contacts_search, contacts_create |
| Docs | `docs/docs-agent.json` | Google Docs | docs_create, docs_read, docs_edit |
| Slides | `slides/slides-agent.json` | Google Slides | slides_create |
| Sheets | `sheets/sheets-agent.json` | Google Sheets | sheets_read, sheets_write, sheets_create |
| Tasks | `tasks/tasks-agent.json` | Google Tasks | tasks_list, tasks_create, tasks_update, tasks_delete |
| Knowledge | `knowledge/knowledge-agent.json` | WolframAlpha → Wikipedia → SerpAPI (waterfall) | knowledge_query |
| Chat | `chat/general-chat.json` | LLM Adapter | general_chat |

**Agent Pattern:** Each agent follows the same structure:
1. Input → 2. Get Google Auth → 3. Build Request (provider-specific, includes null checks for required params) → 4. HTTP Request (`continueOnFail`) → 5. API Success? (If) → [true] Format Response / [false] Handle API Error (with 401 retry)

**Knowledge Agent Pattern** (non-Google):
1. Input → 2. Prepare Query → 3. Wolfram|Alpha (waterfall start) → [has result?] → 4. Format → 5. Output
                                                                 ↳ [no] → Wikipedia Search → [has result?] → Summary → [has extract?] → Format → Output
                                                                                                          ↳ [no] → SerpAPI Search → [has result?] → Format → Output
                                                                                                                                   ↳ [no] → "No answer found"

---

## Adapters (Implemented Today)

| Capability | Current Provider | Status | Future Providers |
|---|---|---|---|
| LLM | Groq (default), Ollama, OpenAI, Anthropic | ✅ Implemented | OpenRouter, Gemini, local models |
| Memory | SQLite (default), n8n-static (fallback) | ✅ Implemented (PG stubbed) | Chroma, Qdrant, Redis |
| Mail | Gmail | ✅ Implemented | Outlook, IMAP, SMTP |
| Calendar | Google Calendar | ✅ Implemented | CalDAV, Outlook Calendar |
| Storage | Google Drive | ✅ Implemented | Dropbox, OneDrive, S3, Local FS |
| Contacts | Google Contacts | ✅ Implemented | — |
| Docs | Google Docs | ✅ Implemented | — |
| Slides | Google Slides | ✅ Implemented (OAuth2) | — |
| Sheets | Google Sheets | ✅ Implemented | — |
| Tasks | Google Tasks | ✅ Implemented | — |
| Search | WolframAlpha, Wikipedia, SerpAPI | ✅ Implemented | — |
| Channel | Telegram, Webhook | ✅ Implemented | Discord, Slack, Matrix |

---

## Data Flow

```
User Message
    │
    ▼
Entry Workflow
    │  Normalize → Input Processor → Auth → Rate Limit
    ▼
Intent Classifier (LLM Adapter)
    │  Classify intent + extract params
    ▼
Capability Router
    │  Route to capability agent
    ▼
Capability Agent (e.g., Gmail Agent)
    │  Build request → HTTP → Format response
    ▼
Response Sender
    │  Format → Channel (Telegram/Webhook)
    ▼
Memory Store
    │  Save session → Extract facts (LLM) → Save facts (Memory Adapter)
    ▼
Done
```

---

## Configuration

All configuration via environment variables in n8n.

### Credential Abstraction

| Auth Type | Variables Required | Used By |
|---|---|---|
| Google OAuth2 | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | All Google capabilities (Gmail, Calendar, Drive, Contacts, Docs, Slides, Sheets, Tasks) |
| LLM | `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` | llm-adapter.json, general-chat, intent-classifier |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` | entry.json, response-sender.json |
| Knowledge | `WOLFRAM_ALPHA_APPID`, `SERPAPI_API_KEY` | knowledge-agent.json |
| Audio STT | `GROQ_API_KEY` | input-processor.json (Groq Whisper) |

**Note:** Google OAuth2 is managed exclusively by `JARVIS — Google Auth`. Neither `GOOGLE_API_KEY` nor `GOOGLE_ACCESS_TOKEN` should be set manually — the auth workflow handles token lifecycle internally.

### Required

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
| `SQLITE_MEMORY_URL` | `http://localhost:8710` | SQLite memory server URL (required if MEMORY_PROVIDER=sqlite) |
| `SQLITE_MEMORY_PATH` | — | SQLite memory DB path (alternative to URL) |
| `GROQ_API_KEY` | — | Groq API key (used for LLM and Whisper STT) |
| `WOLFRAM_ALPHA_APPID` | — | WolframAlpha App ID |
| `SERPAPI_API_KEY` | — | SerpAPI key |
| `AUTH_MODE` | `protected` | open, protected |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per user |
| `TELEGRAM_MAX_MESSAGE_LENGTH` | `4000` | Max message length |
| `LOG_LEVEL` | `info` | debug, info, warn, error |
| `GROQ_API_KEY` | — | Groq API key (used for LLM and Whisper STT) |
| `MAIL_AGENT_NAME` | `JARVIS — Gmail Agent` | Override target workflow for mail capability |
| `CALENDAR_AGENT_NAME` | `JARVIS — Calendar Agent` | Override target workflow for calendar capability |
| `STORAGE_AGENT_NAME` | `JARVIS — Drive Agent` | Override target workflow for storage capability |
| `CONTACTS_AGENT_NAME` | `JARVIS — Contacts Agent` | Override target workflow for contacts capability |
| `DOCS_AGENT_NAME` | `JARVIS — Docs Agent` | Override target workflow for docs capability |
| `SLIDES_AGENT_NAME` | `JARVIS — Slides Agent` | Override target workflow for slides capability |
| `SHEETS_AGENT_NAME` | `JARVIS — Sheets Agent` | Override target workflow for sheets capability |
| `TASKS_AGENT_NAME` | `JARVIS — Tasks Agent` | Override target workflow for tasks capability |
| `KNOWLEDGE_AGENT_NAME` | `JARVIS — Knowledge Agent` | Override target workflow for knowledge capability |
| `CHAT_AGENT_NAME` | `JARVIS — General Chat` | Override target workflow for chat capability |

---

## Folder Structure

```
workflow/
├── core/
│   ├── entry.json              # Single entry point
│   ├── input-processor.json    # Non-text input preprocessing (STT, fallbacks)
│   ├── intent-classifier.json  # Intent classification
│   ├── capability-router.json  # Intent → capability routing
│   ├── llm-adapter.json        # Unified LLM interface
│   ├── memory-adapter.json     # Unified memory interface
│   ├── memory-store.json       # Session + fact persistence
│   ├── response-sender.json    # Response formatting + delivery
│   ├── config-validator.json   # Env validation
│   └── error-handler.json      # Global error handling
└── capabilities/
    ├── mail/
    │   └── gmail-agent.json
    ├── calendar/
    │   └── calendar-agent.json
    ├── storage/
    │   └── drive-agent.json
    ├── contacts/
    │   └── contacts-agent.json
    ├── docs/
    │   └── docs-agent.json
    ├── slides/
    │   └── slides-agent.json
    ├── sheets/
    │   └── sheets-agent.json
    ├── tasks/
    │   └── tasks-agent.json
    ├── knowledge/
    │   └── knowledge-agent.json
    └── chat/
        └── general-chat.json
```

---

## Adding a New Capability

1. Create `workflow/capabilities/<capability>/<provider>-agent.json`
2. Follow agent pattern: Input → Build Request → HTTP → Format Response
3. Add route in `capability-router.json` Switch node
4. Add intent prefix to `intent-classifier.json` VALID_INTENTS list
5. Document in this file

---

## Adding a New Provider for Existing Capability

1. Create new agent workflow: `<capability>/<new-provider>-agent.json`
2. Set the corresponding env var (e.g., `MAIL_AGENT_NAME=JARVIS — Outlook Agent`) — no changes to `capability-router.json` needed
3. No changes to core workflows needed

---

## Known Limitations

1. **Google-only providers** — Only Google adapters implemented today. Architecture supports others but not built.
2. **PostgreSQL memory** — Not implemented yet. Only SQLite and n8n-static providers are available, with SQLite as the default.
3. **Whisper STT only** — Voice transcription only works with Groq Whisper. No offline/local STT.
4. **Single n8n instance** — No horizontal scaling.
5. **No workflow versioning** — Workflows are JSON files, no migration system.
6. **Limited error recovery** — Failed workflows don't auto-retry beyond HTTP retry config.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| n8n as brain | Visual workflow, built-in retry, webhook, credentials, executeWorkflow |
| Capability-first | Decouples core from providers; enables swapping Gmail→Outlook |
| Single entry workflow | Eliminates duplicate auth/rate-limit/normalize logic |
| LLM adapter | Single place to add/switch LLM providers |
| Memory adapter | Swap storage backend without changing agents |
| No config framework | Env vars are simple, universal, n8n-native |
| No secrets manager | Overkill for single-user; env vars + file perms sufficient |
| No metrics/telemetry | Personal use only; logs sufficient for debugging |
| Switch node for routing | Simple, visual, n8n-native; no custom code needed |
| executeWorkflow for composition | Native n8n composition; workflows stay independent |
| Env-var-driven agent routing | Swapping providers is a one-line env var change; no workflow edits needed |
| Input Processor workflow | Voice/photos/documents get consistent handling without cluttering entry workflow |
| Intent param schema validation | Prevents LLM hallucinated params from reaching agent code; each boundary is typed |
| Knowledge waterfall chain | WolframAlpha → Wikipedia → SerpAPI with per-source credential detection |
| Google Auth single source of truth | All Google auth flows through one workflow; no GOOGLE_API_KEY/GOOGLE_ACCESS_TOKEN confusion |

---

## Traceability

Every request gets a `traceId` (format: `sess_<epoch>_<6char-random>`) at entry point.
- Passed through all workflows via JSON payload
- Included in all inline log entries
- Included in error responses (`error-handler.json`)
- Enables end-to-end debugging
