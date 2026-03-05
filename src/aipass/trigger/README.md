# TRIGGER

**Purpose:** Error detection, pattern matching, auto-dispatch to responsible agents
**Module:** `aipass.trigger`
**Created:** 2026-03-05

---

## Overview

### What I Do


### How I Work
- **Entry Point:** `apps/trigger.py`
- **Pattern:** Auto-discovers and routes to modules

---

## Architecture

```
TRIGGER/
├── apps/
│   ├── trigger.py       # Entry point
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

