# dev.local.md - DEVPULSE
```
Branch: src/aipass/devpulse
Created: 2026-03-07
Updated: 2026-03-10
```

## Active Work

- Nothing active — clean slate after FPLAN-0025 close

## Issues

- **flow/FPLAN archive**: FIXED by flow — now archives to flow/processed_plans/. Orphan backup_system/ removed.
- **flow/DPLAN CWD default**: DPLANs always go to flow's dev_planning/ regardless of caller's CWD. Should default to current directory.
- **backup**: Missing `config.json` template in json_templates/
- **api**: `models` command not routed through drone
- **commons**: DB init failure (14/15 branches operational, commons only blocker)
- **ai_mail**: `get_current_user()` returns relative `mailbox_path` — causes doubled paths in reply
- **drone**: stderr kwarg crash on some error paths

## Completed

- FPLAN-0025 STATUS board — built and closed (2026-03-10)
  - STATUS.local.md seeded across 15 branches + spawn template
  - Prax built sync handler autonomously (handlers/status/sync.py)
  - drone @prax status sync verified: 14 operational, 1 in-progress
  - Prax also fixed dashboard command collision + created central/reader.py
- Claude Code statusline: ANSI colors, context bar, cost, LOC, hook activity flash
- Hook logger pattern: ~/.claude/hook_logger.sh → /tmp/aipass-hook-last → statusline reads
- Added Claude Code local docs breadcrumb to global prompt
- PR #31 merged: seedgo v2, 589 files, full system audit
- Prompt architecture: breadcrumbs in global+local, dev.local.md system-wide
- Flow plan lifecycle: DPLAN paths fixed, FPLAN template detection fixed
- FPLAN-0021 dispatched+completed by flow: DPLANs wired into CLI router

---

## Todos

- [ ] Scaffold remaining modules with system prompts (.aipass/aipass_local_prompt.md)
- [ ] Test dispatch wake to branches beyond ai_mail/prax
- [ ] Address drone stderr kwarg crash
- [ ] Close stale FPLANs (0017, 0021) once verified complete
- [ ] GWS CLI integration exploration for ai_mail external email transport

## Notepad

- Dev-Pass reference: `/home/patrick/Projects/Dev-Pass/`
- seed=Dev-Pass name, seedgo=AIPass name
- STATUS board: `drone @prax status sync` rebuilds STATUS.md from all STATUS.local.md files
- GWS CLI: `@googleworkspace/cli` — Rust-based, dynamic discovery. Future ai_mail integration candidate.
- Claude Code API cost display in statusline — fun but not actionable (we don't use API directly)
