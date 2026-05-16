# Claude Code Config Recon
**Date:** 2026-03-06

## Hooks Active

### UserPromptSubmit — branch_prompt_loader.py
- Walks up from CWD looking for `.trinity/` or `apps/` to find branch root
- Loads `.aipass/branch_system_prompt.md` or `.aipass/aipass_local_prompt.md`
- Only DevPulse currently has a prompt file

### PreToolUse — tool_use_sound.py
- Plays ATM key press sound on Bash/Edit/Read/Grep/Glob/Write/etc.
- Sound files NOT present — silent fallback

### Stop — stop_sound.py
- Plays achievement bell when AI finishes
- Sound files NOT present — silent fallback

### Notification — notification_sound.py
- Plays announce tone on permission requests
- Sound files NOT present — silent fallback

## Module Settings
All 10 modules have `.claude/settings.local.json` with empty permissions. No module-specific config.

## Prompt Architecture
- **Global prompt:** Not present (hook would load `aipass_global_prompt.md` if it existed)
- **Branch prompts:** Only DevPulse has one (`.aipass/aipass_local_prompt.md`)
- **Branch discovery:** Looks for `.trinity/` or `apps/` directory to identify branch root

## Commands
- `.claude/commands/memo.md` — Guidance for updating .trinity memory files after work

## Permissions
- Default mode: acceptEdits
- Denied: git reset, rebase, config, force push, EnterPlanMode
