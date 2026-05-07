# Project-Level Hooks

These hooks are provisioned by `aipass init` and live in the project's
`.claude/settings.json`. They fire when CWD is inside this project.

## What fires and what doesn't

**UserPromptSubmit** hooks fire from project settings. These work:
- `branch_prompt_loader.py` — injects branch-specific prompt
- `email_notification.py` — shows unread email count
- `identity_injector.py` — injects branch identity from passport

**PreToolUse / PostToolUse** hooks are provisioned but **DO NOT FIRE** from
project-level settings. This is a Claude Code limitation (confirmed S122,
GitHub issue #36071). These scripts exist but are dead weight:
- `pre_edit_gate.py` — intended to block cross-branch writes (never runs)
- `auto_fix_diagnostics.py` — intended to run pyright+ruff (never runs)
- `subagent_stop_gate.py` — intended to check subagent files (never runs)

These same hooks DO fire from provider settings (`~/.claude/settings.json`)
where they are also wired. The provider copies handle all enforcement.

**PreCompact** hooks fire from project settings:
- `pre_compact.py` — injects recovery context after compaction

## CWD guard interaction

When this project has UserPromptSubmit hooks (it does), the provider-level
UserPromptSubmit hooks detect this and exit silently. This prevents the AIPass
global prompt from being injected into projects that manage their own context.

The provider-level PreToolUse/PostToolUse hooks still fire (they can only run
at provider level) — so enforcement (git_gate, pre_edit_gate, auto_fix) is
always active regardless of CWD.

## Testing

Provider-level test harness covers project-level behavior:
```bash
python3 $AIPASS_HOME/.claude/hooks/hook_test.py --direct
```

Tests include:
- `direct_provider_guards_for_init_project` — verifies provider hooks are
  CWD-guarded when run from an aipass init project
- `direct_project_settings_schema` — validates project settings.json has
  expected hooks and all referenced scripts exist

## Updating hooks

```bash
drone @cli aipass init update    # Refresh managed project files to latest templates
```

## Related
See `$AIPASS_HOME/.claude/hooks/README.md` for the full hook system documentation.
