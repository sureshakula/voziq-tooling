# SEEDGO — Branch Context
<!-- File: src/aipass/seedgo/.aipass/aipass_local_prompt.md — Injected on every prompt when in seedgo directory. -->

Standards compliance platform. Audits branches, queries standard content, manages bypass rules.

## Commands

```
seedgo audit aipass                              # Audit all branches
seedgo audit aipass flow                         # Single branch
seedgo standards_query aipass_standards cli       # Show standard content
seedgo diagnostics                               # Pyright type errors
seedgo readme update @branch                     # README auto-update
```

All modules also accept their filename: `standards_audit`, `diagnostics_audit`, `readme_update`.

## Apps Layout (extra layer vs standard branch)

```
apps/
├── seedgo.py              # Entry point — thin router
├── modules/               # standards_audit, standards_query, diagnostics_audit, readme_update
└── handlers/
    ├── aipass_standards/   # Checker pack (*_check.py + *_content.py pairs)
    ├── audit/              # branch_audit, discovery, audit_display
    ├── bypass/             # bypass_handler, ignore_handler
    ├── config/             # aipass_bypass, aipass_ignore
    ├── diagnostics/        # discovery (standalone disabled, runs via audit pipeline)
    ├── file/               # file_handler
    └── json/               # json_handler
```

`.sorting_unprocessed/` inside a pack = staging area, not dead. Move files out before using.

## Quick Reference

- Pack discovery: `handlers/*_standards/` dirs with `*_check.py` files
- `audit` strips `_standards` suffix: `aipass_standards/` → `audit aipass`
- `standards_query` uses full dir name: `standards_query aipass_standards`
- Rich markup only — never bare `print()`, never captured ANSI for drone output
- See README for full directory tree and integration points
