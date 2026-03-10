# Flow

**Purpose:** Plan lifecycle management for AIPass. Creates, tracks, closes, and archives numbered work plans (FPLANs) with registry-backed state, async post-processing, and cross-branch aggregation.
**Module:** `aipass.flow`
**Created:** 2025-11-15
**Last Updated:** 2026-03-08

---

## Overview

### What I Do
- Create numbered FPLANs from templates (default, master, proposal)
- Close plans with async post-processing and archival
- List and filter plans across branches
- Restore plans from backups
- Monitor registry health with orphan detection and auto-healing
- Aggregate plans across branches
- Background post-close processing via `dplan_post_close_runner`
- Delegated plan management via `dplan_flow` orchestrator

## Commands / Usage

```bash
drone @flow create . "Subject"                  # Create FPLAN in current dir
drone @flow create . "Subject" master           # Create master plan
drone @flow close FPLAN-XXXX                    # Close a plan
drone @flow list                                # List active plans
drone @flow --help                              # Full help
```

---

## Architecture

```
flow/
├── apps/
│   ├── flow.py                  # Entry point (auto-discovers modules)
│   ├── modules/                 # Business logic
│   │   ├── create_plan.py       # Plan creation with template support
│   │   ├── close_plan.py        # Closure with async archival
│   │   ├── list_plans.py        # Plan listing and filtering
│   │   ├── restore_plan.py      # Plan recovery from backups
│   │   ├── registry_monitor.py  # Orphan detection, auto-healing
│   │   ├── aggregate_central.py # Cross-branch plan aggregation
│   │   ├── post_close_runner.py # Background post-processing
│   │   ├── dplan_flow.py        # Delegated plan management orchestrator
│   │   └── dplan_post_close_runner.py # DPLAN-specific post-close runner
│   └── handlers/                # Implementation details
│       ├── plan/                # Lifecycle, file ops, validation
│       ├── registry/            # Load, save, auto-heal
│       ├── template/            # Plan templates (default, master, proposal)
│       ├── dashboard/           # Status aggregation
│       ├── dplan/               # DPLAN handlers (list, create, close, display, etc.)
│       ├── mbank/               # Memory bank archival
│       └── summary/             # AI-generated plan summaries
├── templates/                   # Plan template files
├── docs/                        # Documentation
├── flow_json/                   # Configuration and registry data
└── tests/
```

---

## Plan Naming

Plans follow the convention `FPLAN-XXXX_topic_slug_YYYY-MM-DD.md` where XXXX is an auto-incrementing number.

---

## Integration Points

### Depends On
- `aipass.cli` — Terminal formatting (console, header, success, error)
- `aipass.prax` — Structured logging via `system_logger`
- `aipass.trigger` — Error reporting (optional)
- Python stdlib (`pathlib`, `json`, `importlib`, `sys`, `signal`)

### Provides To
- All modules — Plan creation, tracking, closure, and archival
- `aipass.devpulse` — Plan status aggregation for system dashboards
- Registry: Reads/writes plan registry in `flow_json/`

---

*Last Updated: 2026-03-08*
