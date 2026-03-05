# DRONE

**Purpose:** Command routing, @ resolution, module discovery and dispatch
**Module:** `aipass.drone`
**Created:** 2026-03-05

---

## Overview

### What I Do


### How I Work
- **Entry Point:** `apps/drone.py`
- **Pattern:** Auto-discovers and routes to modules

---

## Architecture

```
DRONE/
├── apps/
│   ├── drone.py       # Entry point
│   ├── modules/            # Business logic
│   ├── handlers/           # Implementation
│   └── plugins/            # Extensions
├── docs/
├── tests/
├── passport.json           # Identity
├── local.json              # Session history
├── observations.json       # Collaboration patterns
└── README.md
```

---

## Commands

*Configure after initialization*

---

## Integration Points

### Depends On


### Provides To

