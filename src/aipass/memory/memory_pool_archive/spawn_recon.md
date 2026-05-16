# Spawn Module Recon
**Date:** 2026-03-06

## Summary
Agent creation utility library. Flat structure (not 3-layer — it's infrastructure, not an agent). Well-designed, stable.

## Structure
```
spawn/
├── spawn.py                  # Main engine (210 lines, 7-step spawn)
├── file_ops.py               # Template copy + path manipulation
├── placeholders.py           # {{PLACEHOLDER}} replacement
├── metadata.py               # Branch name extraction
├── registry.py               # AIPASS_REGISTRY.json CRUD
├── __init__.py               # Single export: spawn_agent
├── templates/
│   ├── agent.template/       # Base template (full agent skeleton)
│   └── agent_mock_branch/    # Reference spawned agent
└── tests/
    └── test_spawn.py         # 126 lines, covers full spawn lifecycle
```

## How spawn_agent() Works (7 Steps)
1. Validate target doesn't exist
2. Extract branch name from path
3. Get next citizen number from registry
4. Build placeholder mapping (14 variables)
5. Copy template recursively, replacing placeholders
6. Rename `{{BRANCH}}_*` directories
7. Update AIPASS_REGISTRY.json

## Placeholder Variables
`{{BRANCHNAME}}` (UPPER), `{{branchname}}` (lower), `{{BRANCH}}` (module name), `{{CWD}}`, `{{DATE}}`, `{{MODULE}}`, `{{EMAIL}}`, `{{PROFILE}}`, `{{ROLE}}`, `{{TRAITS}}`, `{{PURPOSE_BRIEF}}`, `{{CITIZEN_NUMBER}}`, `{{KEY_CAPABILITIES}}`, `{{DEPENDS_ON}}`, `{{PROVIDES_TO}}`

## Path Debt
- No Path.home() in spawn code
- Template conftest.py has hardcoded shebang (propagates to all spawned agents)
- Template branch.py has relative import bug (propagates to all spawned agents)

## Notes
- Flat structure is intentional — spawn is a utility, not an autonomous agent
- No .trinity files (by design)
- Has actual tests (only module with test_*.py files)
- Skip list: `__pycache__`, `.git`, `.template_registry.json`, `.gitkeep`
