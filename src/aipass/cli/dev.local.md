# dev.local.md - CLI
```
Branch: src/aipass/cli
Created: 2026-03-07
```

## Issues

- `handlers/display/` dir does NOT exist — display.py `print_introspection()` references it but shows "not found". Either create it or remove the reference.
- `plugins/`, `extensions/`, `json_templates/` are empty stub packages from scaffold — consider if these are needed.
- `__init__.py` top-level re-exports display functions but NOT templates (`operation_start`, `operation_complete`). README shows `from aipass.cli import operation_start` but that would fail.
- Seedgo architecture at 91% — missing `.ai_mail.local/sent/`, `dropbox/`, `logs/` dirs.

---

## Todos

- Fix top-level `__init__.py` to also re-export `operation_start`, `operation_complete` (or update README)
- Create missing scaffold dirs for 100% seedgo architecture
- Configure branch prompt (.aipass/aipass_local_prompt.md)
- Consider creating handlers/display/ dir or removing reference from display.py introspection
