# Spawn Templates Recon
**Date:** 2026-03-06

## Templates Available
1. `agent.template/` — Base agent skeleton
2. `agent_mock_branch/` — Reference implementation (fully spawned example)

## agent.template Structure
```
agent.template/
├── .agent/                   # System metadata
│   ├── .migrations.json      # Structural migration rules
│   ├── .backup_ignore.json   # Backup exclusion patterns
│   ├── .registry_ignore.json # Template update exclusions
│   └── .template_registry.json  # File tracking with SHA hashes
├── .aipass/
│   └── aipass_local_prompt.md  # Branch prompt (needs config)
├── .trinity/
│   ├── passport.json         # Identity ({{BRANCHNAME}}, {{ROLE}}, etc.)
│   ├── local.json            # Session history
│   └── observations.json     # Collaboration patterns
├── .archive/.gitkeep
├── .claude/settings.local.json
├── apps/
│   ├── branch.py             # Entry point (auto-discovery + routing)
│   ├── modules/__init__.py   # Empty (agent builds its own)
│   ├── handlers/__init__.py
│   ├── plugins/__init__.py
│   └── extensions/__init__.py  # (not in devpulse)
├── artifacts/
│   └── birth_certificate.json  # Citizenship record
├── docs/.gitkeep
├── tests/conftest.py, __init__.py
├── tools/verify_branch.py     # Template verification
├── {{BRANCH}}_json/.gitkeep   # Renamed on spawn
├── DASHBOARD.local.json
├── flow.local.md
├── README.md
├── pytest.ini
└── .gitignore
```

## DevPulse vs Template Comparison

| Item | Template | DevPulse | Status |
|------|----------|----------|--------|
| .trinity/ | Yes | Yes | Done |
| .agent/ | Yes | Yes | Done |
| .aipass/ | Yes | Yes | Done |
| artifacts/ | Yes | Yes | Done |
| tools/verify_branch.py | Yes | Yes (fixed Path.home) | Done |
| docs/ | Yes | Yes | Done |
| {{BRANCH}}_json/ | Yes | devpulse_json/ | Done |
| .archive/ | Yes | Yes | Done |
| DASHBOARD.local.json | Yes | Yes | Done |
| flow.local.md | Yes | Yes | Done |
| apps/extensions/ | Yes | No | Missing |
| apps/json_templates/ | Yes | No | Missing (optional) |

## Template Issues
- branch.py:35 uses relative import `apps.modules.{stem}` (propagates to all agents)
- conftest.py has hardcoded `/home/aipass/` shebang (propagates)
- modules/ dir is intentionally empty (agents build their own)
