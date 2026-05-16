# Flow Module Recon
**Date:** 2026-03-06

## Summary
PLAN lifecycle management. Well-designed architecture but **incomplete** — missing infrastructure dirs. 15 Path.home() hits.

## Structure
```
flow/
├── apps/
│   ├── flow.py               # Entry point (auto-discovery)
│   ├── modules/              # 8 modules
│   │   ├── create_plan.py    # FPLAN creation (v1.0.0)
│   │   ├── close_plan.py     # Plan closure with async archival (v3.4.0)
│   │   ├── list_plans.py     # Plan listing
│   │   ├── restore_plan.py   # Plan recovery (4 Path.home() hits)
│   │   ├── registry_monitor.py  # Orphan detection (ECOSYSTEM_ROOT = Path("/home/aipass"))
│   │   ├── aggregate_central.py # Cross-branch aggregation
│   │   └── post_close_runner.py
│   ├── handlers/             # 11 categories
│   │   ├── plan/             # 16 files - lifecycle, file ops
│   │   ├── registry/         # 4 files - load, save, auto-heal
│   │   ├── template/         # 2 files - content, loading
│   │   ├── dashboard/        # 3 files - local, central, branch
│   │   ├── summary/          # write_plan_outputs.py (4 Path.home())
│   │   └── mbank/, json/, config/, events/
└── tests/                    # Empty (conftest only)
```

## Plan Naming Convention
`FPLAN-XXXX_slug_YYYY-MM-DD.md`

## Missing Infrastructure (BLOCKERS)
- `flow_json/` — needs `flow_registry.json` (plan registry)
- `templates/` — needs `default.md`, `master.md`, `proposal.md`
- `.trinity/` — no identity files

## Path.home() Debt: 15 instances
- registry_monitor.py:83 — `ECOSYSTEM_ROOT = Path("/home/aipass")` (CRITICAL, import-time)
- write_plan_outputs.py:57,81,93,106,142 — CLAUDE.json, ai_mail paths [stale: was AI_CENTRAL]
- restore_plan.py:159-184 — 4 hits in recovery logic
- push_central.py:54, push_branch_dashboard.py:69, aggregate_central.py:69
- process.py:55,57 — MEMORY [stale: was MEMORY_BANK], AIPASS_REGISTRY [stale: was PRIVATE_BRANCH_REGISTRY]

## Working (architecturally)
- Plan creation, closure with async archival
- Registry auto-healing and orphan detection
- Central aggregation, dashboard three-tier system
- Template content detection, trigger integration
