# JARVIS Workflows Reference

Complete reference for all n8n workflows in the JARVIS architecture.

---

## Core Workflows (`workflow/core/`)

### 1. `entry.json` — Single Entry Point

**Purpose:** Unified entry for all user inputs (Telegram, Website webhook).

**Triggers:**
- Telegram Trigger (`jarvis-telegram` webhook)
- Webhook (`jarvis-webhook-site` path)

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Telegram Trigger | `telegramTrigger` | Receives Telegram messages/callbacks |
| Website Webhook | `webhook` | Receives POST from website |
| Merge Entry Points | `merge` | Combines both triggers |
| Normalize Request | `code` | Unifies payload to common shape |
| Auth Gate | `code` | Validates owner + webhook secret |
| Rate Limit | `code` | Per-user, per-minute limit |
| Intent Classifier | `executeWorkflow` | Calls `JARVIS — Intent Classifier` |
| Capability Router | `executeWorkflow` | Calls `JARVIS — Capability Router` |
| Merge Results | `merge` | Combines capability outputs |
| Response Sender | `executeWorkflow` | Calls `JARVIS — Response Sender` |
| Memory Store | `executeWorkflow` | Calls `JARVIS — Memory Store` |

**Output Shape (Normalized):**
```json
{
  "source": "telegram|website",
  "userId": "string",
  "sessionId": "string",
  "messageId": "string",
  "inputType": "text|voice|photo|document|location|unknown",
  "inputText": "string",
  "inputBinary": "null|object",
  "metadata": {
    "chatId": "string|null",
    "replyEndpoint": "string|null",
    "timestamp": "ISO8601",
    "clientInfo": "object"
  }
}
```

---

### 2. `intent-classifier.json` — Intent Classification

**Purpose:** Classify user input into one of 27 intents using LLM.

**Input:** Normalized request from entry workflow

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| LLM Adapter | `executeWorkflow` | Calls `JARVIS — LLM Adapter` with classification prompt |
| Parse Intent | `code` | Validates intent against enum, extracts params |

**LLM Prompt:** System prompt defines all valid intents with examples.

**Valid Intents (27):**
```
general_chat
drive_list, drive_search, drive_upload, drive_download, drive_delete
gmail_search, gmail_read, gmail_send, gmail_delete
calendar_list, calendar_create, calendar_delete
contacts_list, contacts_search, contacts_create
docs_create, docs_read, docs_edit
slides_create
sheets_read, sheets_write, sheets_create
tasks_list, tasks_create, tasks_update, tasks_delete
knowledge_query
```

**Output:**
```json
{
  "intent": "gmail_search",
  "intentConfidence": 0.95,
  "intentParams": { "q": "from:boss", "max_results": 10 }
}
```

---

### 3. `capability-router.json` — Capability Routing

**Purpose:** Route intent to correct capability agent.

**Input:** Classified intent from intent-classifier

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Route to Capability | `switch` | Maps intent prefix → capability |
| Mail Agent (Gmail) | `executeWorkflow` | `JARVIS 4.6 — Gmail Agent` |
| Calendar Agent | `executeWorkflow` | `JARVIS 4.6 — Calendar Agent` |
| Storage Agent (Drive) | `executeWorkflow` | `JARVIS 4.6 — Drive Agent` |
| Contacts Agent | `executeWorkflow` | `JARVIS 4.6 — Contacts Agent` |
| Docs Agent | `executeWorkflow` | `JARVIS 4.6 — Docs Agent` |
| Slides Agent | `executeWorkflow` | `JARVIS 4.5 — Slides Agent` |
| Tasks Agent | `executeWorkflow` | `JARVIS 4.6 — Tasks Agent` |
| Sheets Agent | `executeWorkflow` | `JARVIS 4.6 — Sheets Agent` |
| Knowledge Agent | `executeWorkflow` | `JARVIS 4.6 — Knowledge Agent` |
| General Chat | `executeWorkflow` | `JARVIS — General Chat` |

**Routing Logic:**
| Intent Prefix | Capability | Agent Workflow |
|---|---|---|
| `gmail_` | mail | Gmail Agent |
| `calendar_` | calendar | Calendar Agent |
| `drive_` | storage | Drive Agent |
| `contacts_` | contacts | Contacts Agent |
| `docs_` | docs | Docs Agent |
| `slides_` | slides | Slides Agent |
| `tasks_` | tasks | Tasks Agent |
| `sheets_` | sheets | Sheets Agent |
| `knowledge_` | knowledge | Knowledge Agent |
| `general_chat` | chat | General Chat |

---

### 4. `llm-adapter.json` — Unified LLM Interface

**Purpose:** Single interface for all LLM providers.

**Input:** `{ messages, temperature?, response_format? }`

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Provider Switch | `if` | Routes by `LLM_PROVIDER` env var |
| Groq / OpenAI Compatible | `httpRequest` | Groq, OpenAI-compatible APIs |
| Ollama | `httpRequest` | Local Ollama instance |
| OpenAI | `httpRequest` | Official OpenAI API |
| Anthropic | `httpRequest` | Anthropic Claude API |
| Merge LLM Results | `merge` | Combines provider outputs |
| Parse LLM Response | `code` | Normalizes response across providers |

**Supported Providers (via `LLM_PROVIDER`):**
- `groq` (default) — `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`
- `ollama` — `OLLAMA_API_BASE`, `OLLAMA_MODEL`
- `openai` — `OPENAI_API_BASE`, `OPENAI_API_KEY`, `OPENAI_MODEL`
- `anthropic` — `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`

**Output:**
```json
{
  "llmResponse": "raw string response",
  "llmParsed": "parsed JSON if response_format=json_object",
  "provider": "groq|ollama|openai|anthropic",
  "success": true
}
```

---

### 5. `memory-adapter.json` — Unified Memory Interface

**Purpose:** Single interface for memory backends.

**Input:** `{ action, sessionId, userId, inputText?, responseText?, intent?, facts? }`

**Actions:**
| Action | Description |
|---|---|
| `save-session` | Persist session (last message, response, intent) |
| `get-session` | Retrieve session by sessionId |
| `save-facts` | Persist extracted facts (category, key, value) |
| `get-facts` | Retrieve facts (filtered by userId, category) |

**Providers (via `MEMORY_PROVIDER`):**
| Provider | Status |
|---|---|
| `n8n-static` (default) | ✅ Implemented — uses n8n workflow static data |
| `sqlite` | 🔄 Stub — returns not implemented error |
| `postgres` | 🔄 Stub — returns not implemented error |

**Output:**
```json
{
  "saved": true,
  "session": { ... },
  "factsSaved": 3,
  "facts": [...]
}
```

---

### 6. `memory-store.json` — Session + Fact Persistence

**Purpose:** Orchestrate saving session and extracting/persisting facts.

**Input:** Normalized request + capability response (has `responseText`, `intent`)

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Add `action: save-session` |
| Save Session | `executeWorkflow` | Calls `JARVIS — Memory Adapter` with `save-session` |
| Extract Facts (LLM) | `executeWorkflow` | Calls `JARVIS — LLM Adapter` with fact extraction prompt |
| Parse Facts | `code` | Parses LLM JSON response into facts array |
| Save Facts | `executeWorkflow` | Calls `JARVIS — Memory Adapter` with `save-facts` |

**Fact Extraction Prompt:** Extracts profile, preference, fact categories from conversation.

---

### 7. `response-sender.json` — Response Delivery

**Purpose:** Format and send response to user via correct channel.

**Input:** Capability agent output (has `responseText`, `source`, `metadata`)

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Format Output | `code` | Markdown→HTML, truncate for Telegram |
| Is Telegram? | `if` | Checks `source === 'telegram'` |
| Is Website? | `if` | Checks `source === 'website'` |
| Send to Telegram | `httpRequest` | POST to Telegram Bot API |
| Respond to Website | `respondToWebhook` | Returns JSON to webhook caller |

**Formatting:**
- `**bold**` → `<b>bold</b>`
- `*italic*` → `<i>italic</i>`
- `` `code` `` → `<code>code</code>`
- Truncates to `TELEGRAM_MAX_MESSAGE_LENGTH` (default 4000)

---

### 8. `config-validator.json` — Configuration Validation

**Purpose:** Validate required environment variables on startup.

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Validate Config | `code` | Checks required + optional env vars |
| Config Invalid? | `if` | Branches on validation result |
| Throw Error | `code` | Throws if missing required vars |
| Config Valid | `code` | Returns validated config object |

**Required Variables:**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `OWNER_USER_ID`
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
- `GOOGLE_API_KEY`, `GOOGLE_ACCESS_TOKEN`

---

### 9. `error-handler.json` — Global Error Handling

**Purpose:** Catch errors, log them, send user-friendly message.

**Input:** Error object from failed workflow

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Log Error | `code` | Console.error with traceId, workflow, error |
| Is Telegram? | `if` | Checks `source === 'telegram'` |
| Is Website? | `if` | Checks `source === 'website'` |
| Send to Telegram | `httpRequest` | Sends error message to user |
| Respond to Website | `respondToWebhook` | Returns error JSON |

**User Message:** `⚠️ Something went wrong (traceId). Please try again or check logs.`

---

### 10. `logger.json` — Structured Logging

**Purpose:** Consistent JSON logging with trace IDs.

**Input:** `{ level, message, traceId, workflow, meta }`

**Nodes:**
| Node | Type | Purpose |
|---|---|---|
| Input | `code` | Pass-through |
| Write Log | `code` | Outputs JSON to console if level >= `LOG_LEVEL` |

**Log Levels:** `debug` (0), `info` (1), `warn` (2), `error` (3)

**Log Entry:**
```json
{
  "timestamp": "2026-06-30T12:00:00.000Z",
  "level": "info",
  "traceId": "sess_123_1700000000000",
  "workflow": "gmail-agent",
  "message": "Gmail search completed",
  "meta": { "results": 5 }
}
```

---

## Capability Workflows (`workflow/capabilities/`)

### Mail — `mail/gmail-agent.json`
**Intents:** `gmail_search`, `gmail_read`, `gmail_send`, `gmail_delete`
**Provider:** Gmail API (Google)
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Calendar — `calendar/calendar-agent.json`
**Intents:** `calendar_list`, `calendar_create`, `calendar_delete`
**Provider:** Google Calendar API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Storage — `storage/drive-agent.json`
**Intents:** `drive_list`, `drive_search`, `drive_upload`, `drive_download`, `drive_delete`
**Provider:** Google Drive API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Contacts — `contacts/contacts-agent.json`
**Intents:** `contacts_list`, `contacts_search`, `contacts_create`
**Provider:** Google People API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Docs — `docs/docs-agent.json`
**Intents:** `docs_create`, `docs_read`, `docs_edit`
**Provider:** Google Docs API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Slides — `slides/slides-agent.json`
**Intents:** `slides_create`
**Provider:** Google Slides API
**Auth:** `GOOGLE_API_KEY`

### Sheets — `sheets/sheets-agent.json`
**Intents:** `sheets_read`, `sheets_write`, `sheets_create`
**Provider:** Google Sheets API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Tasks — `tasks/tasks-agent.json`
**Intents:** `tasks_list`, `tasks_create`, `tasks_update`, `tasks_delete`
**Provider:** Google Tasks API
**Auth:** `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN`

### Knowledge — `knowledge/knowledge-agent.json`
**Intents:** `knowledge_query`
**Providers:** WolframAlpha, Wikipedia, SerpAPI
**Auth:** `WOLFRAM_ALPHA_APPID`, `SERPAPI_API_KEY`

### Chat — `chat/general-chat.json`
**Intents:** `general_chat`
**Provider:** LLM Adapter (any configured provider)
**Auth:** Via LLM Adapter

---

## Common Agent Pattern

All capability agents follow this structure:

```
Input (code)
    │
    ▼
Build Request (code)
    - Validates intent + params
    - Checks API credentials
    - Builds provider-specific HTTP request
    │
    ▼
HTTP Request (httpRequest)
    - Calls provider API
    - Handles auth (API key or Bearer token)
    │
    ▼
Format Response (code)
    - Parses provider response
    - Formats user-friendly output
    - Returns { responseText, success }
```

---

## Workflow Execution Order

```
1. entry.json (triggered by Telegram/Webhook)
   │
   ├── Normalize Request
   ├── Auth Gate
   ├── Rate Limit
   ├── intent-classifier.json
   │   │
   │   └── llm-adapter.json
   │
   ├── capability-router.json
   │   │
   │   └── capability agent (e.g., gmail-agent.json)
   │       │
   │       └── (provider HTTP call)
   │
   ├── Merge Results
   │
   ├── response-sender.json
   │   │
   │   ├── Format Output
   │   ├── Send to Telegram (if telegram)
   │   └── Respond to Webhook (if website)
   │
   └── memory-store.json
       │
       ├── Save Session → memory-adapter.json
       ├── Extract Facts → llm-adapter.json
       ├── Parse Facts
       └── Save Facts → memory-adapter.json
```

---

## Environment Variables by Workflow

| Workflow | Required | Optional |
|---|---|---|
| `entry.json` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `OWNER_USER_ID` | `AUTH_MODE`, `RATE_LIMIT_PER_MINUTE` |
| `intent-classifier.json` | Via `llm-adapter.json` | — |
| `llm-adapter.json` | `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` | `LLM_PROVIDER`, `OLLAMA_*`, `OPENAI_*`, `ANTHROPIC_*` |
| `memory-adapter.json` | — | `MEMORY_PROVIDER` |
| `memory-store.json` | Via `llm-adapter.json` + `memory-adapter.json` | — |
| `response-sender.json` | `TELEGRAM_BOT_TOKEN` | `TELEGRAM_MAX_MESSAGE_LENGTH` |
| `config-validator.json` | All required vars | All optional vars |
| `error-handler.json` | `TELEGRAM_BOT_TOKEN` | — |
| `logger.json` | — | `LOG_LEVEL` |
| Gmail/Calendar/Drive/Contacts/Docs/Sheets/Tasks | `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN` | — |
| Slides | `GOOGLE_API_KEY` | — |
| Knowledge | `WOLFRAM_ALPHA_APPID`, `SERPAPI_API_KEY` | — |

---

## Testing Workflows

### Import into n8n
1. Open n8n → Workflows → Import
2. Select workflow JSON file
3. Configure credentials (Telegram, Google OAuth2, etc.)
4. Set environment variables in n8n settings
5. Activate workflow

### Test Entry Flow
```bash
# Telegram: Send message to bot
# Webhook: POST to /webhook/jarvis-webhook
curl -X POST http://localhost:5678/webhook/jarvis-webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "session_id": "test-123"}'
```

### Verify Workflow References
All `executeWorkflow` nodes reference workflows by **name**. The names must match what the workflow is imported as:

| JSON File | Workflow Name |
|---|---|
| `entry.json` | `JARVIS — Entry` |
| `intent-classifier.json` | `JARVIS — Intent Classifier` |
| `capability-router.json` | `JARVIS — Capability Router` |
| `llm-adapter.json` | `JARVIS — LLM Adapter` |
| `memory-adapter.json` | `JARVIS — Memory Adapter` |
| `memory-store.json` | `JARVIS — Memory Store` |
| `response-sender.json` | `JARVIS — Response Sender` |
| `config-validator.json` | `JARVIS — Config Validator` |
| `error-handler.json` | `JARVIS — Error Handler` |
| `logger.json` | `JARVIS — Logger` |
| `gmail-agent.json` | `JARVIS 4.6 — Gmail Agent` |
| `calendar-agent.json` | `JARVIS 4.6 — Calendar Agent` |
| `drive-agent.json` | `JARVIS 4.6 — Drive Agent` |
| `contacts-agent.json` | `JARVIS 4.6 — Contacts Agent` |
| `docs-agent.json` | `JARVIS 4.6 — Docs Agent` |
| `slides-agent.json` | `JARVIS 4.5 — Slides Agent` |
| `tasks-agent.json` | `JARVIS 4.6 — Tasks Agent` |
| `sheets-agent.json` | `JARVIS 4.6 — Sheets Agent` |
| `knowledge-agent.json` | `JARVIS 4.6 — Knowledge Agent` |
| `general-chat.json` | `JARVIS — General Chat` |

---

## Adding a New Workflow

1. Create JSON in appropriate folder (`core/` or `capabilities/<capability>/`)
2. Follow naming convention: `JARVIS — <Name>` for core, `JARVIS <version> — <Name>` for capabilities
3. Add to capability router if it's a capability agent
4. Add intent to intent-classifier VALID_INTENTS if new intent
5. Update this document
