# Repo Root Recon
**Date:** 2026-03-06

## Summary
Well-structured Python package repo with 10 modules, Hatchling build, GitHub Actions CI.

## Key Files
- `AIPASS_REGISTRY.json` — 10 branches, all active, all at `src/aipass/{module}`
- `pyproject.toml` — aipass v1.0.0, Python >=3.10, Hatchling build
- `CLAUDE.md` — Agent startup protocol
- `Dockerfile` — codercom/code-server base, Python 3.x, isolated venv
- `DPLAN-047_...md` — Critical path purge plan

## pyproject.toml Details
```
[project]
name = "aipass", version = "1.0.0", python = ">=3.10"
dependencies = ["rich >= 13.0", "watchdog >= 3.0"]

[project.scripts]
drone = "aipass.drone.cli:main"
seedgo = "seedgo.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/aipass", "src/seedgo"]
```

## CI Pipeline (.github/workflows/ci.yml)
- Python 3.10, 3.11, 3.12, 3.13
- Steps: ruff check, pytest

## AIPASS_REGISTRY.json
All 10 modules registered: ai_mail, api, cli, devpulse, drone, flow, prax, seedgo, spawn, trigger.
All status: active. All profile: library.

## Claude Config (.claude/)
- settings.json: acceptEdits mode, denies git reset/rebase/force-push
- Hooks: prompt loader, tool sounds, notification sounds, stop sounds
- branch_prompt_loader.py: discovers branch root via .trinity/ or apps/, loads .aipass/ prompts
- Sound files referenced but not present (graceful fallback)

## Notes
- No root-level tests/ (tests live in each module)
- No global aipass_global_prompt.md exists yet (hook would load it if present)
- `your` — empty file at root (cleanup candidate)
