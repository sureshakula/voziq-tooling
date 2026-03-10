# API

**Purpose:** LLM API access layer with provider abstraction, key management, model routing, and usage tracking.
**Module:** `aipass.api`
**Last Updated:** 2026-03-08

---

## Overview

### What I Do
- Manage API keys for LLM providers (currently OpenRouter)
- Route requests to LLM models with provider-level abstraction
- Track API usage metrics and provide statistics
- Validate credentials and test provider connectivity
- Discover available models from configured providers

### How I Work
- **Entry Point:** `apps/api.py` -- auto-discovers and routes to modules
- **Pattern:** Standard AIPass 3-tier architecture (entry point / modules / handlers)

---

## Commands / Usage

```bash
drone @api get-key           # Retrieve API key for provider
drone @api validate          # Validate API credentials and connection
drone @api test              # Test OpenRouter connection status
drone @api models            # List available models from provider
drone @api track             # Track API usage metrics
drone @api stats             # Display API usage statistics
drone @api --help            # Full help output
drone @api --version         # Show version
```

Running `drone @api` with no arguments displays module introspection (discovered modules and status).

---

## Architecture

```
api/
├── __init__.py                    # Public API exports
├── apps/
│   ├── api.py                     # Entry point (module discovery, command routing)
│   ├── modules/
│   │   ├── api_key.py             # Key retrieval and validation logic
│   │   ├── openrouter_client.py   # OpenRouter API client
│   │   └── usage_tracker.py       # Usage metrics tracking
│   └── handlers/
│       ├── auth/
│       │   ├── env.py             # Environment variable credential loading
│       │   └── keys.py            # API key storage and retrieval
│       ├── config/
│       │   └── provider.py        # Provider configuration management
│       ├── json/
│       │   └── json_handler.py    # JSON operation logging
│       ├── openrouter/
│       │   ├── caller.py          # HTTP request execution
│       │   ├── client.py          # OpenRouter client implementation
│       │   ├── models.py          # Model discovery and listing
│       │   └── provision.py       # Provider provisioning
│       └── usage/
│           ├── aggregation.py     # Usage data aggregation
│           ├── cleanup.py         # Usage data cleanup
│           └── tracking.py        # Usage event tracking
└── README.md
```

---

## Integration Points

### Depends On
- `aipass.prax` -- structured logging via `system_logger`
- `aipass.cli` -- Rich console output formatting

### Provides To
- All modules -- LLM API access for any branch that needs model inference
- System-wide API key management and credential validation

---

*Last Updated: 2026-03-08*
