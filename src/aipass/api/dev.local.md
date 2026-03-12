# dev.local.md - API
```
Branch: src/aipass/api
Created: 2026-03-07
Updated: 2026-03-10
```

## Issues

- `track` command shows "TODO" — workflow not fully implemented in usage_tracker module
- `make_call(args)`, `test_connection()`, `check_status()` in openrouter_client.py are TODO stubs
- `list_providers()` in api_key.py hardcoded to "openrouter" only — should load dynamically

## Todos

- Wire up real `track` workflow in usage_tracker.py
- Implement `make_call()`, `test_connection()`, `check_status()` in openrouter_client.py
- Consider logging import failures during module auto-discovery (currently silent)

## Notes

- 2026-03-10: Fixed missing `requests` + `openai` deps in pyproject.toml. All 6 commands now route correctly. Added `~/.secrets/aipass/.env` as priority search path. Configured branch prompt.
