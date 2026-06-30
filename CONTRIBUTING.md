# Contributing to JARVIS

## Workflow Naming Convention

All workflows must follow the format: `JARVIS — <Name>`

| Type | Pattern | Example |
|---|---|---|
| Core | `JARVIS — <Function>` | `JARVIS — Entry`, `JARVIS — Intent Classifier` |
| Capability Agent | `JARVIS — <Capability> Agent` | `JARVIS — Gmail Agent`, `JARVIS — Outlook Agent` |

## Auth Documentation Rule

Auth references in documentation must always reference the auth workflow, not the raw variable.

- Correct: `Auth: via JARVIS — Google Auth`
- Incorrect: `Auth: GOOGLE_ACCESS_TOKEN`
- Incorrect: `Auth: GOOGLE_API_KEY`

Google OAuth2 is managed exclusively by the `JARVIS — Google Auth` workflow. Do not reference `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN` directly in documentation.

## Adding a New Capability

1. Create `workflow/capabilities/<capability>/<provider>-agent.json`
2. Follow the agent pattern:
   - Google agents: Input → Get Google Auth → Build Request (with null checks) → HTTP Request (`continueOnFail`) → API Success? → [true] Format Response / [false] Handle API Error (with 401 retry)
   - Non-Google agents: Input → Prepare → HTTP Request → Format Response
3. Add route in `capability-router.json` Switch node (with env var for the workflow name)
4. Add intent prefix to `PARAMS_SCHEMA` in `intent-classifier.json` (with required/optional param definitions)
5. Add the new env var to `config-validator.json` optional list
6. Document in `ARCHITECTURE.md` and `WORKFLOWS.md`

## Adding a New Provider for an Existing Capability

1. Create the new agent workflow: `<capability>/<new-provider>-agent.json`
2. Set the corresponding env var (e.g., `MAIL_AGENT_NAME=JARVIS — Outlook Agent`)
3. No changes to `capability-router.json` needed — routing is env-var driven

## Code Style Guidelines

### JavaScript (Code nodes)
- Use `const` / `let`, never `var`
- Use arrow functions for inline callbacks
- Use template literals for string interpolation
- Use optional chaining (`?.`) and nullish coalescing (`??`)
- Always use `return [{ json: { ... } }]` or `return [$input.item]` pattern

### Logging
Use the inline `jarvisLog()` utility function in each Code node:
```javascript
const jarvisLog = (level, message, meta = {}) => {
  const levels = { debug: 0, info: 1, warn: 2, error: 3 };
  const configLevel = ($env.LOG_LEVEL || 'info').toLowerCase();
  if (levels[level] >= (levels[configLevel] ?? 1)) {
    console[level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log'](
      JSON.stringify({
        timestamp: new Date().toISOString(),
        level,
        traceId: $json.sessionId || $json.traceId || 'unknown',
        workflow: '<workflow-name>',
        message,
        meta
      })
    );
  }
};
```

### Error Handling Pattern (Google agents)
```
HTTP Request (continueOnFail: true)
  → API Success? (If: statusCode === undefined || (200 ≤ statusCode < 300))
    → [true] Format Response (uses _ctx for context)
    → [false] Handle API Error (401 retry via $helpers.httpRequest → re-call API)
```

## Testing Checklist Before Commit

- [ ] All workflow JSON files pass JSON validation
- [ ] All `executeWorkflow` references use the correct workflow name (env var pattern for agents)
- [ ] No hardcoded `GOOGLE_API_KEY` or `GOOGLE_ACCESS_TOKEN` references remain
- [ ] New env vars are documented in `.env.example`
- [ ] New env vars are added to `config-validator.json` optional list
- [ ] Workflow has `errorWorkflow` setting pointing to `JARVIS — Error Handler`
- [ ] All HTTP Request nodes use `continueOnFail: true`
- [ ] Smoke test sequence passes (see TESTING.md)
- [ ] `jarvisLog()` is present in all new Code nodes that perform operations
