# JARVIS — Testing Guide

## Pre-Flight Checklist

Run this checklist before first use and after any workflow modification:

- [ ] All 21 workflows imported into n8n (compare with WORKFLOWS.md name table)
- [ ] All workflow names match exactly — `executeWorkflow` references are case-sensitive
- [ ] All required env vars set (reference `.env.example`)
- [ ] `JARVIS — Entry` is the **only** activated workflow (sub-workflows are called via `executeWorkflow`)
- [ ] Telegram webhook registered with n8n:
  ```bash
  curl -X POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://YOUR_N8N_URL/webhook/jarvis-telegram",
      "secret_token": "YOUR_TELEGRAM_WEBHOOK_SECRET"
    }'
  ```
- [ ] Website webhook responds:
  ```bash
  curl -X POST https://YOUR_N8N_URL/webhook/jarvis-webhook-site \
    -H "Content-Type: application/json" \
    -d '{"text": "ping", "session_id": "setup-test"}'
  # Expected: {"responseText": "I'm JARVIS, your AI assistant. How can I help?", "success": true}
  ```

## Smoke Test Sequence

Send these messages to your Telegram bot **in order**. Each should produce a reasonable response — not a crash or error.

| # | Message | Expected Behavior |
|---|---|---|
| 1 | `hello` | General chat response (e.g., "Hi! I'm JARVIS...") |
| 2 | `list my emails` | Gmail list result, auth error, or "No emails found" — not an unhandled exception |
| 3 | `what is 2+2` | Knowledge query result (WolframAlpha: "4") or fallback message |
| 4 | `create event tomorrow 3pm meeting` | Calendar creation result, auth error, or param validation error — not a crash |

**If any step fails:**
- Step 1 fails → Check LLM provider env vars and `JARVIS — LLM Adapter` is imported
- Step 2 fails → Check Google OAuth env vars and `JARVIS — Google Auth` is imported
- Step 3 fails → Check WolframAlpha env vars; if not set, fallback should return "I couldn't find information"
- Step 4 fails → Check Google Calendar API is enabled in Google Cloud Console

## Debugging Guide

### Finding Execution Logs

1. In n8n, go to **Workflows** → **JARVIS — Entry** → **Executions** tab
2. Find the failed execution (red icon)
3. Click to open → each node shows input/output data and error messages
4. Code node `console.log()` output appears in the node's **Output** tab

### Tracing a Request

Every request gets a `traceId` (format: `sess_<timestamp>_<random6chars>`).

To trace a request through all workflows:
1. Note the `sessionId` from the execution JSON of the Entry workflow
2. Each sub-workflow execution includes this `sessionId` in its logs
3. Search n8n executions by time range to find related sub-workflow runs
4. The `jarvisLog()` function in each Code node outputs JSON log lines with the same `traceId`

### Common Error Messages

| Error Message | Root Cause | Fix |
|---|---|---|
| `RATE_LIMIT_EXCEEDED: N/30 requests in last 60s` | User exceeded rate limit | Wait 60s or increase `RATE_LIMIT_PER_MINUTE` |
| `AUTH_FAILED: Invalid Telegram webhook secret` | Webhook secret mismatch | Re-register webhook with correct `secret_token` |
| `JARVIS config error: Missing required env var(s): ...` | Missing env vars | Set all required variables in n8n Settings |
| `GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN must be set` | Google OAuth not configured | Set up Google OAuth (see README.md) |
| `⏳ Too many requests` | Rate limit exceeded | Wait before sending another message |
| `[Voice message — transcription unavailable...]` | Groq Whisper failed | Set `GROQ_API_KEY` env var |
| `I couldn't find information about that...` | All knowledge sources returned empty | Configure `WOLFRAM_ALPHA_APPID` or `SERPAPI_API_KEY` |

### Testing After Workflow Changes

After modifying any workflow:

1. Run the **Pre-Flight Checklist** above
2. Run the **Smoke Test Sequence** and confirm all 4 messages produce reasonable responses
3. Check n8n execution logs for any unexpected errors or warnings
4. Verify no workflow shows "Error" status in the n8n workflow list
