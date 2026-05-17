# Project Night Research — S69

## What AIPass Already Has (Don't Rebuild)
- Inter-branch messaging + dispatch (ai_mail)
- Commons collaboration rooms + voting + boardrooms
- Medic auto-dispatch for errors (trigger, partially wired)
- Dashboard system (prax, partially wired)
- Agent handover (natural via dispatch lifecycle)
- Plan lifecycle (flow — FPLAN/DPLAN/APLAN/RPLAN/master)
- Semantic memory + rollover (memory — ChromaDB)
- Standards compliance (seedgo — 32 standards)
- Event bus (trigger — 14 events)
- Branch lifecycle (spawn — create/update/delete)
- CLI routing (drone — @branch resolution)
- Background scheduling (daemon — cron + plugins)
- Multi-mode backup (backup — snapshot/versioned/Drive)
- API gateway (api — OpenRouter/Google)
- Skill discovery framework (skills — 3-tier)
- 20 diagnostic scanners (devpulse tools/)

## What AIPass Doesn't Have (Opportunity Space)
- Nothing that produces value OUTSIDE the system
- No ability to analyze/process external codebases programmatically
- No ability to generate reports/artifacts for human consumption beyond CLI
- No cost/budget tracking across agent operations
- No structural failure detection (tool loops, context bloat, reasoning stalls)
- No automated regression testing (run tests, compare results over time)
- No ability to onboard external projects into the AIPass ecosystem
- No external webhook/notification system (only internal dbus)
- No cross-project knowledge sharing (AIPass ↔ Nexus ↔ external)

## Patrick's Interests (Starred Repos)
- Dunetrace: structural failure detection in multi-agent systems
- Phantom: autonomous agents with persistent VM, self-creating tools
- Paperclip: multi-agent company with budgets and org charts
- Syrin: budget control + semantic memory pools
- OpenClaw Nerve: real-time ops cockpit for agent fleets
- Virtual Context: semantic memory compression
- Citadel: persistent campaigns + fleet coordination
- Jork: autonomous agent with independent thinking cycles
- Galactic: infrastructure-level multi-instance management

## Key Insight
AIPass is entirely self-referential. Every branch serves the system.
The gap: something that uses the system to DO something for the outside world.

## Constraints
- CLI only (no UI/dashboards beyond what prax already has)
- Must require NEW work from all 13 core branches (exclude commons/skills)
- Must be genuinely new, not rebuilding existing capabilities
- Should run through prax logging, get seedgo standards, use all plan types
- Can be a new citizen (src/aipass/newbranch/) or standalone project
