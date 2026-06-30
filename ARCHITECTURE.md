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
│  │ n8n-static      │  │ SQLite          │  │ PostgreSQL     │  │
│  │ (default)       │  │ (future)        │  │ + pgvector     │  │
│  └─────────────────┘  └─────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Workflows

### `core/entry.json`
Single entry point for all inputs.
- **Triggers**: Telegram, Webhook (website)
- **Normalization**: Unifies Telegram + Web payloads into common shape
- **Auth**: Validates `OWNER_USER_ID` + Telegram webhook secret
- **Rate Limit**: Per-user, per-minute (configurable)
- **Flow**: Normalize → Auth → Rate Limit → Intent Classifier → Capability Router → Merge → Response Sender + Memory Store

### `core/intent-classifier.json`
LLM-based intent classification.
- Calls `JARVIS — LLM Adapter` with classification prompt
- Validates intent against known enum (27 intents)
- Output: `{ intent, confidence, params }`

### `core/capability-router.json`
Routes intent to capability agent.
- Switch node mapping intent prefix → capability
- Calls appropriate capability agent via `executeWorkflow`
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
- Providers: n8n-static (default), SQLite (stub), PostgreSQL (stub)
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
- Required: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, OWNER_USER_ID, LLM_API_KEY, LLM_API_BASE, LLM_MODEL, GOOGLE_API_KEY, GOOGLE_ACCESS_TOKEN
- Fails fast if missing

### `core/error-handler.json`
Global error handling.
- Logs error with traceId
- Sends user-friendly message to Telegram or Webhook
- No complex DLQ or retry logic — simple and effective

### `core/logger.json`
Structured logging.
- Levels: debug, info, warn, error (controlled by `LOG_LEVEL`)
- Includes: timestamp, level, traceId, workflow, message, meta
- Console JSON output

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
| Knowledge | `knowledge/knowledge-agent.json` | WolframAlpha, Wikipedia, SerpAPI | knowledge_query |
| Chat | `chat/general-chat.json` | LLM Adapter | general_chat |

**Agent Pattern:** Each agent follows the same structure:
1. Input → 2. Build Request (provider-specific) → 3. HTTP Request → 4. Format Response

---

## Adapters (Implemented Today)

| Capability | Current Provider | Status | Future Providers |
|---|---|---|---|
| LLM | Groq (default), Ollama, OpenAI, Anthropic | ✅ Implemented | OpenRouter, Gemini, local models |
| Memory | n8n-static (default) | ✅ Implemented (SQLite/PG stubbed) | Chroma, Qdrant, Redis |
| Mail | Gmail | ✅ Implemented | Outlook, IMAP, SMTP |
| Calendar | Google Calendar | ✅ Implemented | CalDAV, Outlook Calendar |
| Storage | Google Drive | ✅ Implemented | Dropbox, OneDrive, S3, Local FS |
| Contacts | Google Contacts | ✅ Implemented | — |
| Docs | Google Docs | ✅ Implemented | — |
| Slides | Google Slides | ✅ Implemented | — |
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
    │  Normalize → Auth → Rate Limit
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

## Folder Structure

```
workflow/
├── core/
│   ├── entry.json              # Single entry point
│   ├── intent-classifier.json  # Intent classification
│   ├── capability-router.json  # Intent → capability routing
│   ├── llm-adapter.json        # Unified LLM interface
│   ├── memory-adapter.json     # Unified memory interface
│   ├── memory-store.json       # Session + fact persistence
│   ├── response-sender.json    # Response formatting + delivery
│   ├── config-validator.json   # Env validation
│   ├── error-handler.json      # Global error handling
│   └── logger.json             # Structured logging
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
2. Update `capability-router.json` to route to new workflow (or add provider selection logic)
3. No changes to core workflows needed

---

## Known Limitations

1. **Google-only providers** — Only Google adapters implemented today. Architecture supports others but not built.
2. **n8n-static memory** — In-memory, not persistent across n8n restarts. SQLite/PostgreSQL adapters stubbed.
3. **No OAuth refresh** — Google access token must be manually refreshed.
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

---

## Traceability

Every request gets a `traceId` (sessionId + timestamp) at entry point.
- Passed through all workflows via JSON payload
- Included in all log entries (`logger.json`)
- Included in error responses (`error-handler.json`)
- Enables end-to-end debugging
