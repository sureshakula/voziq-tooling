# FPLAN-0006 - [framework] Skills System Build

**Created**: 2026-03-07
**Branch**: /home/aipass/aipass_business/AIPass
**Status**: Complete
**Type**: Master Plan

---

## Planning Phase

### Goal
Build the Skills system for AIPass framework. Skills are documented capabilities that any AI can use — from simple markdown SOPs to full 3-layer code implementations. Lives at `src/skills/` (peer to `src/aipass/`, not inside it — skills are separate from infrastructure).

### Approach
Three-tier skill architecture:
- **Tier 1 (Markdown):** SKILL.md only — instructions an LLM reads and follows
- **Tier 2 (Markdown + Handler):** SKILL.md + handler.py — code does the work
- **Tier 3 (Full 3-layer):** SKILL.md + apps/modules/handlers — complete implementation

Follows seedgo's pack pattern: auto-discovery via SKILL.md manifests, drone-routable via `handle_command()`.

OpenClaw SKILL.md format compatibility: their 52 skills (MIT license) can be adapted with minor metadata changes.

### Key Decisions
- **Location**: `src/skills/` — outside `src/aipass/` (skills are capabilities, not infrastructure)
- **Format**: SKILL.md with YAML frontmatter (compatible with OpenClaw format)
- **Discovery**: Glob + importlib + duck typing (same pattern as Nexus skills, seedgo packs)
- **Drone integration**: `drone @skills list|info|run|create|validate`
- **Handler contract**: `run(action, args, config) -> {"success": bool, "output": str, "error": str|None}`
- **No branch manager build** — directory structure only (like FPLAN-0003/0004/0005 pattern)

### Reference Documents
- Design: `vera/projects/framework/skills_system_design.md`
- Research: `vera/projects/framework/nexus_and_skills_design.md`
- Seedgo pattern: `src/aipass/seedgo/apps/standards/aipass/` (pack architecture)
- Telegram reference: `/home/aipass/aipass_core/api/apps/handlers/telegram/` (complex skill example)
- OpenClaw skills: `/home/aipass/external_repos/openclaw/skills/` (SKILL.md format reference)
- Architecture: `vera/projects/framework/architecture_reference.md`

---

## Execution Log

### Phase 1: Foundation — Directory Structure + Core
- [x] Create `src/skills/` directory structure (3-layer: apps/skills.py → modules/ → handlers/)
- [x] Create entry point: `apps/skills.py` with `handle_command()` for drone routing
- [x] Create discovery module: `apps/modules/discovery.py` (scan search paths, parse SKILL.md frontmatter)
- [x] Create loader module: `apps/modules/loader.py` (load full SKILL.md, import handler if present)
- [x] Create runner module: `apps/modules/runner.py` (execute handler or display instructions)
- [x] Create creator module: `apps/modules/creator.py` (scaffold new skills from templates)
- [x] Create registry handler: `apps/handlers/registry.py` (skill registry management)
- [x] Create validator handler: `apps/handlers/validator.py` (check requirements — bins, pip, config)
- [x] Create template handler: `apps/handlers/template.py` (skill templates for scaffolding)
- [x] Create Trinity files: `.trinity/passport.json`, `.trinity/local.json`, `.trinity/observations.json`
- [x] Create `__init__.py` files at all levels
- [x] Create README.md

### Phase 2: Templates
- [x] Markdown-only skill template (`templates/markdown_only/SKILL.md`)
- [x] Markdown + handler skill template (`templates/with_handler/SKILL.md` + `handler.py`)
- [x] Full 3-layer skill template (`templates/full/SKILL.md` + `apps/` structure)

### Phase 3: Test Skills (One Per Tier)
- [x] Tier 1: Adapt OpenClaw GitHub skill → `catalog/github/SKILL.md`
- [x] Tier 2: Build system_status skill → `catalog/system_status/SKILL.md` + `handler.py`
- [x] Tier 3: Create drone_commands skill skeleton → `catalog/drone_commands/` with apps structure

### Phase 4: Seedgo Skills Standard
- [x] Create skills standard pack: `src/aipass/seedgo/apps/standards/skills/`
- [x] Create `pack.json` manifest
- [x] Create `pack_entry.py` entry point
- [x] Create standard modules (skill_format, skill_structure, skill_handler)
- [x] Create standard handlers (content + check pairs)

### Phase 5: Testing
- [x] Unit tests for discovery engine (32 tests)
- [x] Unit tests for loader (7 tests)
- [x] Unit tests for runner (11 tests)
- [x] Unit tests for validator (10 tests)
- [x] Integration test: full skill lifecycle create → discover → load → run (14 tests)
- [x] Test OpenClaw skill adaptation works (github skill loads and runs correctly)

---

## Notes

- Same citizen-branch pattern as drone, ai_mail, prax — but directory structure only, no branch manager
- Skills are separate from aipass infrastructure (sit at `src/skills/`, not `src/aipass/skills/`)
- Patrick wants all three tiers supported: markdown SOPs, markdown+handler, full 3-layer
- Code skills cost zero tokens to run — markdown skills cost tokens every time. Both have a place.
- OpenClaw SKILL.md compatibility lets users adapt 52 existing MIT-licensed skills
- Seedgo standard for skills ensures all skills meet quality bar

---

## Completion Checklist

### Definition of Done
- Skills branch exists at `src/skills/` with full 3-layer architecture
- `drone @skills list|info|run|create|validate` commands work
- All three skill tiers supported (markdown, markdown+handler, full 3-layer)
- At least one test skill per tier working
- OpenClaw GitHub skill successfully adapted
- Seedgo skills standard created with at least 3 checks
- Tests passing
- Trinity files in place

---

## Close Command

When all boxes checked:
```bash
drone @flow close FPLAN-0006
```
