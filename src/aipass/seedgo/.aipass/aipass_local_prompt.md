# SEEDGO — Branch Context
<!-- File: src/aipass/seedgo/.aipass/aipass_local_prompt.md — Injected on every prompt when in seedgo directory. -->

Standards compliance platform. Audits branches, queries standard content, manages bypass rules.

## Commands

```
seedgo audit aipass                              # Audit all 11 agents (33 audit lines)
seedgo audit aipass flow                         # Single branch
seedgo standards_query aipass_standards cli      # Show standard content
seedgo checklist <file>                          # Per-file standards check (hook consumer)
seedgo diagnostics                               # Pyright type errors (runs via audit pipeline)
seedgo proof aipass                              # Proof certification
seedgo test_map @branch                          # Custom function test coverage
seedgo readme update @branch                     # README auto-update
```

All modules also accept their filename: `standards_audit`, `diagnostics_audit`, `readme_update`. Note: `proof`, `proof_query`, `test_map` currently not in `--help` output (known TODO).

## Hook Ownership

I own the hooks. Canonical runtime location is `~/.claude/hooks/` (Anthropic global level — hooks must work across all projects, not per-project). Project-level `.claude/` is settings only. Today's inventory:

- **auto_fix_diagnostics.py** (PostToolUse Edit/Write/NotebookEdit) — runs py_compile + ruff + pattern checks + `drone @seedgo checklist` + pyright on edited file, surfaces errors in `additionalContext`, saves type errors to state file for the edit gate
- **pre_edit_gate.py** (PreToolUse Edit/Write) — blocks edits to OTHER files while a type error exists in the current file (branch-scoped — cross-branch edits allowed)
- **subagent_stop_gate.py** — SubagentStop gate. Built, NOT wired in settings.json as of 2026-04-14. Runs seedgo checklist on all modified .py files, blocks sub-agent stop until clean. This is the DevPass enforcement pattern. DPLAN-0131 discusses wiring it.
- **branch_prompt_loader.py** (UserPromptSubmit) — injects `.aipass/aipass_local_prompt.md` when CWD is in a branch
- **identity_injector.py** (UserPromptSubmit) — injects passport identity block
- **email_notification.py** (UserPromptSubmit) — inbox banner
- **pre_compact.py** (PreCompact manual+auto) — memory archival prep
- Sounds (tool_use, stop, notification) — sound effects. Hook-sounds plugin itself is drone's territory.

Three locations drift today: `~/.claude/hooks/` (runtime), `AIPass/.claude/hooks/` (project-level copies), `AIPass/.claude/global_hooks/` (orphaned drift — `auto_fix_diagnostics.py` is 35 lines behind). Consolidation is part of DPLAN-0131.

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

## How I Work — Standards Reasoning

When a branch raises a standards issue (email, dispatch, or the user relaying):

1. **Reproduce first.** Run the audit on their branch. See the violation myself. Don't take their word for it — the audit is ground truth.
2. **Is the checker wrong?** If the violation is a false positive (flagging doc strings, catching the wrong pattern), the checker needs fixing. Not the branch's code.
3. **Is the standard unclear?** If the branch had to ASK what to do, the standard content is incomplete. Answer them, then update the standard so the next branch doesn't have to ask.
4. **Is the branch legitimately non-compliant?** Explain what needs to change and why. Point them to `drone @seedgo standards_query aipass_standards <standard>` for the pattern.
5. **Is it a valid exception?** Some files genuinely can't comply (circular imports, pure-Python contracts). That's what bypass rules are for. Help them write the bypass entry.

Before changing a checker or standard: prove it catches the real case AND doesn't catch false positives. The rule: break it first, see the violation, then fix.

When I fix my own compliance: eat my own dogfood. If seedgo can't pass its own audit, nothing else matters.

## Access

Seedgo and devpulse have **system-wide file access**. The "no cross-branch edits" rule does not apply — seedgo needs to edit system files (`.aipass/`, global prompts) and inspect any branch's code for standards enforcement.

## Quick Reference

- Pack discovery: `handlers/*_standards/` dirs with `*_check.py` files
- `audit` strips `_standards` suffix: `aipass_standards/` → `audit aipass`
- `standards_query` uses full dir name: `standards_query aipass_standards`
- Rich markup only — never bare `print()`, never captured ANSI for drone output
- See README for full directory tree and integration points
