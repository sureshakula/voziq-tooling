# {{BRANCHNAME}}

**Purpose:** {{PURPOSE_BRIEF}}
**Module:** `aipass.{{MODULE}}`
**Created:** {{DATE}}

---

## Overview

### What I Do
{{KEY_CAPABILITIES}}

### How I Work
- **Entry Point:** `apps/{{MODULE}}.py`
- **Pattern:** Auto-discovers and routes to modules

---

## Architecture

```
{{BRANCHNAME}}/
├── apps/
│   ├── {{MODULE}}.py       # Entry point
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
{{DEPENDS_ON}}

### Provides To
{{PROVIDES_TO}}
