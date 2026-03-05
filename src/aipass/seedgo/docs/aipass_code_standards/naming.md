# Naming Conventions
**Status:** Draft v2 (Truth-checked against codebase)
**Date:** 2025-11-13

---

## Core Principle: Path = Context, Name = Action

**Bad:** `cortex/apps/handlers/branch/cortex_branch_file_ops.py`
**Good:** `cortex/apps/handlers/branch/file_ops.py`

**WHY:** The path already tells you it's Cortex → apps → handlers → branch operations. Adding "cortex_branch_" repeats information you already have.

**Result:** Clean, scannable names. No lies when code moves. Easier imports.

**REALITY CHECK:** This principle is aspirational. Current codebase has violations (e.g., `json_ops.py`, `json_handler.py` in json/ directory). New code should follow the principle; legacy code being migrated gradually.

---

## What Problems Does Consistent Naming Solve?

### 1. The Navigation Problem

Without consistency, finding functionality becomes search:
- "Where is JSON handler? Maybe `json_ops.py`? Or `cortex_json.py`? Or `json_operations.py`?"
- Every branch uses different names
- Agents and humans waste time exploring instead of executing

**Solution:** Standardized locations = predictable navigation
- Need JSON operations? Always `handlers/json/ops.py`
- Need error decorators? Always `handlers/error/decorators.py`
- No guessing. Direct access.

### 2. The Comparison Problem

**Without consistency:**
```bash
# Can't compare - different names, different locations
cortex/cortex_json_handler.py
flow/json_operations.py
prax/handlers/json_ops.py
```

**With consistency:**
```bash
# Easy comparison - same name, same location
cat cortex/apps/handlers/json/ops.py
cat flow/apps/handlers/json/ops.py
cat prax/apps/handlers/json/ops.py
```

**WHY this matters:** Comparison reveals what's common vs branch-specific. You can't standardize what you can't compare.

### 3. The Marketplace Problem

**Without consistency:**
```
Branch A needs: json operations
Marketplace has: 7 different JSON handlers, different APIs
Result: Integration nightmare, manual adaptation
```

**With consistency:**
```
Branch A needs: handlers/json/ops.py
Marketplace has: handlers/json/ops.py v1.2
Result: Drop in, works immediately
```

---

## Why No Redundant Prefixes?

### The Redundancy Cascade

`cortex/apps/handlers/json/cortex_json_ops.py`

**What breaks:**
1. **Length explosion:** 50+ character filenames
2. **Import ugliness:** `from cortex.apps.handlers.json.cortex_json_ops import CortexJsonOps`
3. **Refactoring nightmare:** Move to different directory? Prefix now lies
4. **Search pollution:** Grep for "cortex" returns every file
5. **Visual scanning:** Can't quickly scan directory listings

**Principle:** Information should exist in exactly ONE place. Path tells you context, filename tells you action.

---

## Standard Verbs: The Shared Language

Same operation should have same name everywhere:

**Core operations (verified in codebase):**
- `create` - Create new resource (e.g., `create_thing.py`)
- `ops` - General operations (e.g., `ops.py` in domain handlers)
- `load` - Load configuration/data (e.g., `load_config.py`)
- `save` - Save data (e.g., `save.py` in json handlers)
- `initialize` - Setup/initialization (e.g., `initialize.py`)

**Transformation/Formatting:**
- `formatters` - Transform/format data (e.g., `formatters.py` in error)
- `decorators` - Function decorators (e.g., `decorators.py` in error)
- `logger` - Logging operations (e.g., `logger.py`)

**Handler patterns:**
- `prompts` - User interaction handlers (e.g., `prompts.py` in cli)
- `content` - Content providers (e.g., `cli_content.py`, `naming_content.py`)

**WHY standardize verbs:**
- Grep works: Search for "load" finds all loading operations
- Mental model: See `load_config.py` → instantly know what it does
- API consistency: All "load" operations follow similar patterns
- Cross-branch comparison: Same name = same purpose across all branches

---

## Examples: Good vs Bad

**Good (from real codebase):**
```
cli/apps/handlers/error/decorators.py     # Path: error domain, name: what it does
cli/apps/handlers/error/formatters.py     # Path: error domain, name: what it does
prax/apps/handlers/config/load_config.py  # Path: config domain, name: action
seed/apps/handlers/domain1/ops.py         # Path: domain1, name: operations
```

**Bad (real violations):**
```
prax/apps/handlers/json/json_ops.py       # Redundant "json_" prefix
modules/plan_manager_module.py            # Redundant "module" suffix (hypothetical)
```

**Note:** `json_handler.py` is documented as a standardized exception (see Handler Naming Exceptions section below).

---

## Handler Naming by Domain

**Pattern:** `handlers/<domain>/<action>.py`

**Real Examples from aipass_core/cli:**
```
cli/apps/handlers/
└── error/
    ├── decorators.py    # Error handling decorators
    ├── formatters.py    # Error message formatting
    ├── logger.py        # Error logging
    └── result_types.py  # Result type definitions
```

**Real Examples from aipass_core/prax:**
```
prax/apps/handlers/
├── config/
│   ├── load_config.py           # Config loading
│   └── load_ignore_patterns.py  # Ignore pattern loading
├── json/
│   ├── initialize.py   # JSON initialization
│   ├── load.py         # JSON loading
│   ├── save.py         # JSON saving
│   └── log.py          # JSON logging
└── cli/
    └── prompts.py      # CLI prompt handlers
```

**Real Examples from seed:**
```
seed/apps/handlers/
├── domain1/
│   └── ops.py          # Domain operations (showroom)
├── standards/
│   ├── cli_content.py  # CLI standards content
│   └── naming_content.py # Naming standards content
└── json/
    └── json_handler.py  # JSON operations (standardized exception)
```

---

## Handler Naming Exceptions

### `json_handler.py` - Standardized Exception

`json_handler.py` is a documented exception to the "no redundant prefixes" rule. This file exists across 8+ branches with an identical or near-identical API, making it a de facto standard in the ecosystem. Renaming it to `ops.py`, `handler.py`, or other variants would break established patterns and consumer code depending on this specific name. The redundant prefix is intentional here: it serves as a standardized identifier that marks this as THE canonical JSON handler implementation across the AIPass ecosystem. This exception demonstrates that standardization sometimes requires preserving a slightly non-ideal name rather than breaking existing integrations.

---

## Why This Enables Speed at Scale

### Zero-Cost Navigation
**Agent workflow:**
```
Task: Update JSON operations in Flow
Path: flow/apps/handlers/json/ops.py
Status: FOUND (0 searches required)
```

**Without consistency:**
```
Task: Update JSON operations in Flow
Attempt 1: Search for "json"... 47 results
Attempt 2: Search in handlers/... 12 files
Attempt 3: Read each to find right one
Status: FOUND (3 searches, 5 file reads)
```

**Scale impact:** 20 branches × 50 operations = 1000 handlers
- Consistent: Direct navigation to any handler
- Inconsistent: Search required for every access

### Pattern Emergence

Standardization happens naturally when files align:

1. Each branch implements `handlers/json/ops.py` for their needs
2. Compare all `handlers/json/ops.py` files → common patterns visible
3. Extract common patterns → create standard handler v1.0
4. Freeze and reuse → no reinvention needed

**Critical:** This ONLY works with consistent naming. Different names = patterns invisible.

### Learning Transfer

**With consistency:**
```
Day 1: Learn Cortex structure
Day 2: Work on Flow (same structure, instant productivity)
Day 3: Work on PRAX (same structure, instant productivity)
```

**Without consistency:**
```
Day 1: Learn Cortex structure
Day 2: Learn Flow structure (different pattern, slower)
Day 3: Learn PRAX structure (another pattern, still slower)
```

---

## What Breaks with Inconsistent Naming?

1. **Agent assumptions fail** - AI builds mental model ("JSON is always in handlers/json/ops.py") → one branch violates → agent fails
2. **Comparison tools break** - `diff cortex/.../ops.py flow/.../ops.py` only works if files align
3. **Search becomes ambiguous** - Every search requires filtering, every filter requires domain knowledge
4. **Refactoring becomes expensive** - Move file with prefixed name? Now name lies → rename → update imports → test everything
5. **Marketplace fragments** - Every variant needs own entry, integration guides, version tracking

---

## The Speed Equation

**Without consistency:**
- Navigation = Search (O(n) complexity)
- Comparison = Manual mapping (human labor)
- Learning = Per-branch overhead (20 branches = 20 learning curves)
- Standardization = Nearly impossible (patterns hidden)

**With consistency:**
- Navigation = Direct access (O(1) complexity)
- Comparison = Automated tools (machine labor)
- Learning = One-time investment (20 branches = 1 curve)
- Standardization = Natural emergence (patterns obvious)

---

## Summary

1. **Path provides context** - Don't encode directory structure in filenames
2. **Short names win** - Less typing, easier scanning, cleaner imports
3. **Comparison enables standardization** - Can't standardize what you can't compare
4. **Standard verbs = shared language** - Same operation, same name, everywhere
5. **Consistency compounds** - Benefits multiply across branches and time

**The meta-lesson:** Naming consistency isn't pedantry—it's the prerequisite for emergent standardization at scale.
