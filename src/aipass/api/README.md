[← Back to AIPass](../../../README.md)

# API

> Centralized external API gateway — authenticated service clients for all external APIs

**Module:** `aipass.api` | **Role:** `api_gateway` | **Version:** 1.0.0
**Seedgo:** 100% (34/34) | **Tests:** 306 pass | **Functions:** 74 public (73 tested)
**Last Updated:** 2026-04-22

---

## Overview

API is the centralized external service gateway for AIPass. It provides authenticated clients for external APIs (OpenRouter, Google, future providers). Consumers import ready-to-use service objects — API owns the plumbing, consumers own the business logic.

### What I Do
- Provide authenticated service clients for external APIs (OpenRouter, Google Drive, Calendar, etc.)
- Manage OAuth2 flows, credential storage, and token refresh
- Offer thread-safe service factories for concurrent consumers
- Handle API key management and validation across providers
- Host the generic contract registry for private integration drivers (DPLAN-0133)
- Provide SSL retry and connection resilience utilities

### What I Don't Do
- Host business logic — consumers own what they do with the service
- Set default models or configs — consumers provide their own
- Manage application workflows, polling loops, or orchestration

### Design Principle
If it's not auth, credentials, or service factory — it doesn't belong here.

---

## Commands

```bash
# Key Management
drone @api get-key [provider]         # Retrieve API key (default: openrouter)
drone @api validate [provider]        # Validate API key (default: openrouter)
drone @api validate google            # Validate Google OAuth2 credentials
drone @api reauth google              # Re-authenticate Google OAuth2
drone @api list-providers             # List available API providers
drone @api init                       # Initialize .env template at ~/.secrets/aipass/

# OpenRouter
drone @api test                       # Test OpenRouter connection status
drone @api models [--all]             # List available models (default: top 10)
drone @api status                     # Check OpenRouter client status (key, SDK, cache)
drone @api call "prompt" --model MODEL  # Make API call to model

# Usage Tracking
drone @api track <gen_id>             # Track API usage for a generation
drone @api stats                      # Display overall usage statistics
drone @api session                    # Show current session usage
drone @api caller-usage <caller>      # Show usage by caller module
drone @api cleanup [days]             # Clean up data older than N days (default: 30)

# Integration Contracts
drone @api integrations list          # List registered contracts
drone @api integrations call <contract> [args...]  # Call a registered contract

# Meta
drone @api --help                     # Full help output
drone @api --version                  # Show version (v1.0.0)
drone @api                            # Module introspection (7 discovered modules)
```

---

## Cross-Branch API

```python
# LLM access (OpenRouter)
from aipass.api.apps.modules.openrouter_client import get_response
response = get_response(prompt="...", model="anthropic/claude-3.5-sonnet", caller="flow")

# Google Drive (or any Google API)
from aipass.api.apps.modules.google_client import get_drive_service
service = get_drive_service()                   # Single-threaded
service = get_drive_service(thread_safe=True)   # For concurrent workers

# Any Google service
from aipass.api.apps.modules.google_client import get_google_service
service = get_google_service("calendar", "v3")

# Retry utility for raw API calls
from aipass.api.apps.modules.google_client import api_call_with_retry
```

---

## Architecture

Three-tier design: entry point routes to modules (orchestration), which delegate to handlers (business logic). Modules are auto-discovered from `apps/modules/*.py` — each implements `handle_command(command, args) -> bool`.

```
api/
├── __init__.py
├── apps/
│   ├── api.py                         # Entry point — module discovery, command routing
│   ├── modules/                       # Tier 2: orchestration layer (7 modules)
│   │   ├── api_key.py                 # Key retrieval, validation, provider listing
│   │   ├── openrouter_client.py       # OpenRouter client — calls, models, status
│   │   ├── google_client.py           # Google API services (Drive, Calendar, etc.)
│   │   ├── usage_tracker.py           # Usage metrics — track, stats, cleanup
│   │   ├── bridge.py                  # Generic contract registry (register/resolve)
│   │   ├── integrations_manager.py    # Contract dispatch — integrations list/call
│   │   └── registry.py               # Driver auto-discovery (load_drivers)
│   ├── handlers/                      # Tier 3: business logic (7 packages, 15 files)
│   │   ├── auth/
│   │   │   ├── env.py                 # .env template creation (0o600 permissions)
│   │   │   └── keys.py               # Key storage, retrieval, validation rules
│   │   ├── config/
│   │   │   └── provider.py            # Provider config deep-merge, validation rules
│   │   ├── google/
│   │   │   ├── auth.py                # OAuth2 lifecycle — load, refresh, save credentials
│   │   │   ├── service_factory.py     # Service object factory (single + thread-safe)
│   │   │   └── retry.py              # Exponential backoff with SSL error detection
│   │   ├── integrations/
│   │   │   ├── list.py                # List registered contracts
│   │   │   └── call.py               # Invoke contract driver functions
│   │   ├── json/
│   │   │   └── json_handler.py        # JSON persistence — 3-file pattern per operation
│   │   ├── openrouter/
│   │   │   ├── caller.py             # Stack-based caller detection
│   │   │   ├── client.py             # OpenRouter client (OpenAI SDK wrapper)
│   │   │   ├── models.py             # Model discovery and listing
│   │   │   └── provision.py          # Per-caller config auto-provisioning
│   │   └── usage/
│   │       ├── aggregation.py         # Stats rollup — per-caller, daily, monthly
│   │       ├── cleanup.py             # Data retention and cleanup
│   │       └── tracking.py            # Generation metrics from OpenRouter API
│   └── integrations/                  # Private driver space (gitignored)
│       └── {project}/driver.py        # Each driver registers contracts via bridge
├── tests/                             # 306 tests across 15 files
│   ├── test_api_key.py                # Key management (39 tests)
│   ├── test_caller.py                 # Caller detection (9 tests)
│   ├── test_cli_routing.py            # Command routing (9 tests)
│   ├── test_config_provider.py        # Config merging (16 tests)
│   ├── test_contracts.py              # JSON contract operations (11 tests)
│   ├── test_critical_paths.py         # End-to-end critical flows (19 tests)
│   ├── test_error_resilience.py       # Error handling (4 tests)
│   ├── test_google_client.py          # Google OAuth2 + services (46 tests)
│   ├── test_init_provisioning.py      # Provisioning init (4 tests)
│   ├── test_integrations.py           # Bridge, registry, contracts (17 tests)
│   ├── test_json_handler.py           # JSON persistence (41 tests)
│   ├── test_openrouter_client.py      # OpenRouter client (37 tests)
│   ├── test_provision.py              # Auto-provisioning (20 tests)
│   ├── test_tracking.py              # Usage tracking (13 tests)
│   └── test_usage_tracker.py          # Usage module (21 tests)
└── docs/
    └── SECURITY.md                    # Key handling and leak prevention
```

---

## Integration Contract System

Private integration drivers live in `apps/integrations/{project}/driver.py` (gitignored). Each driver registers named contracts via `bridge.register()`. Callers resolve contracts by name — never referencing private projects directly.

**Three-layer design (DPLAN-0133):**
1. **Drivers** (`apps/integrations/*/driver.py`) — private, gitignored, register contracts on load
2. **Bridge** (`bridge.py`) — public contract registry: `register()`, `resolve()`, `list_contracts()`
3. **Handlers** (`integrations/list.py`, `call.py`) — public dispatch for `drone @api integrations`

**Auto-discovery:** `registry.py` walks `apps/integrations/*/driver.py` via `importlib.util.spec_from_file_location`. Handles empty dirs, missing files, and import errors gracefully.

---

## Integration Points

### Depends On
- `aipass.prax` — structured logging via `system_logger`
- `aipass.cli` — Rich console output formatting

### Provides To
- All branches — authenticated external API clients via `get_response()`, `get_drive_service()`, `get_google_service()`
- System-wide API key management and credential validation

### Credentials
All credentials live at `~/.secrets/aipass/` (0o700 directory, 0o600 files):
- `.env` — API keys (OpenRouter, etc.)
- `google_creds.json` — Google OAuth2 tokens
- `google_client_secret.json` — Google OAuth app config

### Provider Pattern
One module per provider (`openrouter_client.py`, `google_client.py`), one handler directory per provider (`openrouter/`, `google/`). Module orchestrates and presents CLI; handlers implement business logic. Pattern scales to future providers.

---

## Known Issues
- Google auth libraries are optional deps — commands fail with install instructions if missing
- 1/74 public functions untested per seedgo test_map
- Backup branch credential migration pending (`~/.aipass/` to `~/.secrets/aipass/`)

---

*Last Updated: 2026-04-22*

---
[← Back to AIPass](../../../README.md)
