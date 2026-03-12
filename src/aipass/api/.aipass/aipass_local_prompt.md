# API Branch — Local Context

## Identity

API is the **LLM access layer** for AIPass. All branches route through here for model calls, key management, and usage tracking. Gateway to OpenRouter (and future providers).

## Commands

```
drone @api get-key [provider]   # Retrieve API key (fallback: ~/.secrets/aipass/.env → config → env)
drone @api validate [provider]  # Validate key format + connectivity
drone @api test                 # Test OpenRouter connection
drone @api models               # List available models
drone @api track                # Track usage metrics
drone @api stats                # Usage statistics
```

## Architecture

3-tier: Entry point (`apps/api.py`) → Modules (3) → Handlers (9 files, 6 domains)

**Modules:** `api_key.py` (key mgmt), `openrouter_client.py` (LLM client), `usage_tracker.py` (metrics)

**Handlers:** `auth/` (keys, env), `config/` (provider), `openrouter/` (client, models, caller, provision), `usage/` (tracking, aggregation, cleanup), `json/` (auto-creating JSON ops)

## Cross-Branch API

```python
from aipass.api.apps.modules.openrouter_client import get_response
response = get_response(prompt="...", model="anthropic/claude-3.5-sonnet", caller="flow")
```

Used by: flow, prax, skills. Callers must specify model — no default (intentional).

## Key Files

- `apps/api.py` — Entry point with auto-discovery
- `apps/handlers/auth/keys.py` — Key fallback chain (config → env → .env)
- `apps/handlers/auth/env.py` — .env search paths (priority: `~/.secrets/aipass/`)
- `api_json/` — Auto-created JSON storage (config, data, logs)

## Memory & Tracking

- `.trinity/` — Identity, session history, observations
- `dev.local.md` — Working notes, todos, friction
- `logs/` — Prax log output
