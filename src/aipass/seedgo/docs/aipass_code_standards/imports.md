# Import Standards
**Status:** Draft v1
**Date:** 2025-11-12

---

## Standard Import Order

**Every Python file follows this pattern:**

```python
#!/home/aipass/.venv/bin/python3

# [META BLOCK]

"""Module docstring"""

# Infrastructure setup (if needed)
import sys
from pathlib import Path
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))

# Standard library imports
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Prax logger (system-wide - nearly always imported)
from prax.apps.modules.logger import system_logger as logger

# Services (CLI, etc.)
from cli.apps.modules import console, header, success, error

# Internal/local imports
from seed.apps.handlers.json import json_handler
from seed.apps.handlers.domain1 import ops
```

**WHY this order:**
1. **Infrastructure first** - Must run before other imports can work
2. **Standard library** - Python built-ins grouped together
3. **Prax logger** - System-wide logging service
4. **Services** - CLI, other branch services (import before internal handlers)
5. **Internal imports** - After all external dependencies resolved

---

## AIPASS_ROOT Pattern

**The standard:**
```python
from pathlib import Path
AIPASS_ROOT = Path.home() / "aipass_core"
```

**WHY Path.home():**
- Works across all environments (no hardcoded paths)
- User-agnostic (any user can run AIPass)
- System-agnostic (Linux, Mac, Windows)

**Where it's used:**
```python
# Finding branch components
PRAX_ROOT = AIPASS_ROOT / "prax"
CLI_ROOT = AIPASS_ROOT / "cli"
SEED_ROOT = Path.home() / "seed"  # Seed is outside aipass_core

# Accessing shared resources
TEMPLATES_DIR = AIPASS_ROOT / "templates"
```

**Consistency rule:** Always use `AIPASS_ROOT` or `Path.home()`, never hardcode `/home/username/`

---

## sys.path Setup (When Needed)

**Pattern:**
```python
import sys
from pathlib import Path
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
```

**WHY sys.path.insert(0, ...):**
- Allows imports from any branch without relative path gymnastics
- Makes `from prax.apps.modules.logger import system_logger` work from anywhere
- Adds aipass_core to Python's import search path

**When to use:**
- **Modules and handlers:** Need it (they're deep in directory structure)
- **Main entry points:** Usually need it
- **Standalone scripts:** Definitely need it

**Example enabling import:**
```python
# Without sys.path setup - fails
from prax.apps.modules.logger import system_logger  # ModuleNotFoundError

# With sys.path setup - works
sys.path.insert(0, str(AIPASS_ROOT))
from prax.apps.modules.logger import system_logger  # ✓
```

### Branch-Specific sys.path Patterns

**Seed-specific pattern:**
```python
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))  # Seed-specific: enables `from seed.apps.handlers...` imports
```

**Why seed needs both:** Seed lives at `/home/aipass/seed/` (outside `aipass_core`), so adding `Path.home()` to sys.path allows `from seed.apps.handlers...` imports to work. Other branches typically only need the `AIPASS_ROOT` line since they live inside `aipass_core`.

---

## Prax Logger Import (Nearly Always)

**The most common import in the system:**

```python
from prax.apps.modules.logger import system_logger as logger
```

**WHY Prax is important:**
- **System-wide logging** for all branches that subscribe
- **Service provider model** - Prax provides logging as a service
- **Consistent import pattern** - Same everywhere for easy recognition
- **Nearly universal** - Used in almost every module and handler

**Usage:**
```python
logger.info("Branch created successfully")
logger.warning("Memory file not found, using defaults")
logger.error("Failed to backup branch", exc_info=True)
```

**Consistency:** Same import pattern everywhere
```python
# Always this
from prax.apps.modules.logger import system_logger as logger

# Never variations like these
from prax import logger  # ✗
import prax.system_logger  # ✗
```

**Output location:** Prax manages log files, branches don't need to worry about where logs go

---

## Handler Independence Import Rule

**Core rule:** Handlers CANNOT import from parent branch modules

**Example - Seed:**

```python
# ✓ ALLOWED - Handler imports another handler
# seed/apps/handlers/domain1/ops.py
from seed.apps.handlers.json import json_handler

# ✓ ALLOWED - Handler imports standard library
import json
from pathlib import Path

# ✓ ALLOWED - Handler imports Prax service
from prax.apps.modules.logger import system_logger as logger

# ✓ ALLOWED - Handler imports CLI service
from cli.apps.modules import console, error

# ✗ FORBIDDEN - Handler imports parent module
from seed.apps.modules.create_thing import something  # BREAKS INDEPENDENCE
```

**WHY this matters:**
- **Marketplace transportability** - Handlers can be moved to other branches
- **No circular dependencies** - Clean one-way flow
- **Self-contained units** - Handlers work independently

**Pattern:**
```
Modules import handlers ✓
Handlers import handlers ✓
Handlers import modules ✗
```

---

## Internal Import Patterns

**From modules to handlers:**
```python
# In seed/apps/modules/create_thing.py
from seed.apps.handlers.json import json_handler
from seed.apps.handlers.domain1 import ops
```

**From handlers to handlers (within same branch):**
```python
# In seed/apps/handlers/domain1/ops.py
from seed.apps.handlers.json import json_handler
```

**Cross-branch service imports:**
```python
# Services can be imported anywhere (modules or handlers)
from prax.apps.modules.logger import system_logger as logger
from cli.apps.modules import console, header, success, error
```

**Relative imports (avoided):**
```python
# ✗ Don't use relative imports
from ...handlers.json import json_handler  # Confusing, hard to trace

# ✓ Use absolute imports from sys.path
from seed.apps.handlers.json import json_handler  # Clear, explicit
```

---

## External Services - Invocation Context

Some AIPass services need to know **which branch is calling them** to provide proper context-aware functionality. This requires specific invocation patterns beyond simple imports.

### Service Categories

**Library Services (Import & Use):**
- **Prax** - Logging service
- **CLI** - Console formatting and output
- **API** - LLM calls and AI interactions
- **Memory Bank** - Vector storage and search

**Router Services (CLI Invocation Only):**
- **Drone** - NOT a library service, it's a CLI router
  - Resolves `@` targets before passing commands to branches
  - Branches NEVER import from `drone.apps.modules`
  - Invoked via subprocess: `subprocess.run(["drone", "command", ...])`

### Context-Independent Services (Import & Use Anywhere)

**These services work from any location:**

```python
# Prax Logger - context-independent
from prax.apps.modules.logger import system_logger as logger
logger.info("Works from anywhere")

# CLI Services - context-independent
from cli.apps.modules import console, header
console.print("Works from anywhere")
```

**Why they work anywhere:** These services don't need to know who's calling them. They provide generic functionality.

### Drone: CLI Router Pattern (NOT for Import)

**Drone is NOT a library service.** It's a CLI router that:
1. Resolves `@` targets to actual branch paths
2. Routes commands to the appropriate branch
3. Handles context switching and invocation

**✓ CORRECT - Invoke Drone as CLI:**
```python
import subprocess

# Drone resolves @ and routes the command
subprocess.run(["drone", "email", "send", "@recipient", "Subject", "Message"])
subprocess.run(["drone", "log", "show"])
subprocess.run(["drone", "@seed", "some-command"])
```

**✗ FORBIDDEN - Never import from Drone:**
```python
# ✗ WRONG - Drone is not a library service
from drone.apps.modules import resolve_target  # NO!
from drone.apps.modules.router import route_command  # NO!

# Branches should NOT handle @ resolution themselves
# That's Drone's job - it resolves @ before passing to branches
```

**Why Drone is different:**
- **Prax/CLI/API/Memory Bank**: Library services providing functionality via imports
- **Drone**: CLI router that resolves targets and invokes other tools
- Branches receive already-resolved paths/commands from Drone
- Branches don't need @ handling code - Drone does that BEFORE calling them

---

### Context-Dependent Services (PWD Detection Required)

**AI_MAIL** uses PWD (Present Working Directory) detection to determine sender identity and configuration. This means **you must invoke AI_MAIL from your branch directory** for proper operation.

#### The Pattern: Call from Branch Directory

```python
# ✓ CORRECT - Call from your branch directory
# Working dir: /home/aipass/seed/

import subprocess
subprocess.run(["python3", "/home/aipass/aipass_core/ai_mail/apps/ai_mail.py",
                "send", "@drone", "Subject", "Message"])

# AI_MAIL walks up from your CWD, finds SEED.id.json, knows you're @seed
# Your email sends FROM @seed (not @dev_central or @ai_mail)
```

```python
# ✗ WRONG - Call from wrong directory
# Working dir: /home/aipass/

subprocess.run(["python3", "/home/aipass/aipass_core/ai_mail/apps/ai_mail.py",
                "send", "@drone", "Subject", "Message"])

# AI_MAIL can't find branch identity, falls back to @dev_central
# Email sends from wrong identity
```

#### How PWD Detection Works

1. **AI_MAIL starts** at your current working directory
2. **Walks up** the directory tree looking for `*.id.json` file
3. **Finds** (e.g.) `SEED.id.json` at `/home/aipass/seed/`
4. **Derives identity**: Branch name = "seed", email = "@seed"
5. **Auto-generates config** at `/home/aipass/seed/seed_json/user_config.json`
6. **Uses correct sender**: Email sends FROM @seed

#### Best Practice: Use Drone for AI_MAIL

**Recommended approach:**
```python
# Drone handles PWD detection automatically
import subprocess
subprocess.run(["drone", "email", "send", "@recipient", "Subject", "Message"])

# Drone:
# 1. Detects which branch is calling
# 2. Changes to that branch's directory
# 3. Invokes AI_MAIL from correct context
# 4. Email sends with proper identity
```

#### Direct Python Invocation (Advanced)

If calling AI_MAIL directly without Drone:

```python
import subprocess
from pathlib import Path

# Ensure you're in your branch directory
branch_dir = Path(__file__).parent.parent  # Adjust based on file depth
result = subprocess.run(
    ["python3", "/home/aipass/aipass_core/ai_mail/apps/ai_mail.py",
     "send", "@recipient", "Subject", "Message"],
    cwd=str(branch_dir),  # Force working directory to branch root
    capture_output=True
)
```

**Key insight:** The `cwd=` parameter ensures AI_MAIL runs from the correct directory for PWD detection.

#### When to Use Which Approach

| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| Simple email from module | `drone email send ...` | Drone handles context automatically |
| Email from handler | `drone email send ...` | Handlers shouldn't know branch structure |
| Complex automation | Direct call with `cwd=branch_dir` | Full control over context |
| Interactive scripts | Ensure `os.chdir(branch_dir)` first | Interactive sessions need explicit CWD |

#### Files Auto-Generated by AI_MAIL

When you call AI_MAIL from your branch directory, it auto-generates:

```
/home/aipass/seed/
├── seed_json/
│   └── user_config.json          # Your email config (@seed identity)
├── ai_mail.local/
│   ├── inbox.json                # Your inbox
│   └── sent/                     # Your sent folder
└── SEED.ai_mail.json             # Your email summary dashboard
```

**Pattern:** Each branch gets its own isolated email configuration and mailbox.

---

### Future Context-Dependent Services

This PWD detection pattern will be used by other services that need per-branch configuration:

- **AI_MAIL**: Sender identity (current - implemented)
- **Future services**: Database configs, API keys, branch-specific settings

**Design principle:** Services that need "who am I?" should use PWD detection + auto-generated config pattern pioneered by AI_MAIL.

---

## Third-Party Libraries

**Philosophy:** Pragmatic - install what you need, when you need it

**No complex standards:**
- No version pinning requirements (yet)
- No requirements.txt management process (yet)
- Install as you build

**Workflow:**

1. **Build something** → See red squiggly lines in IDE
2. **Check import** → See what library is missing
3. **Install it** → `pip install library_name`
4. **Continue building**

**Example:**
```python
# Writing code
from questionary import select  # Red squiggly line
from rich.console import Console  # Red squiggly line

# Terminal
pip install questionary
pip install rich

# Back to coding - lines now work
```

**AI/Human split:**
- Sometimes AI handles imports and installs them
- Sometimes human sees console errors and installs
- 50-50 split, no rigid process
- Just get what's needed

**When packages aren't obvious:**
```bash
# Import name != package name sometimes
from PIL import Image  # Package is "pillow" not "PIL"
pip install pillow

# Ask for help if unclear
"I need to import X but not sure what package to install"
```

**Virtual environment:**
- AIPass uses `~/.venv/` (user's home directory venv)
- Shebang points to it: `#!/home/aipass/.venv/bin/python3`
- All branches share the same venv
- Packages install once, available everywhere

**EXCEPTION - MEMORY_BANK:**
- MEMORY_BANK uses its own venv: `/home/aipass/MEMORY_BANK/.venv`
- Shebang for MEMORY_BANK: `#!/home/aipass/MEMORY_BANK/.venv/bin/python3`
- Isolated environment for memory management operations

---

## Standard Library Organization

**Group by category:**

```python
# File/path operations
from pathlib import Path
import os
import shutil

# Data handling
import json
from datetime import datetime

# Type hints
from typing import Dict, List, Optional, Tuple, Any

# System operations
import sys
import subprocess
```

**Alphabetical within categories:**
```python
# ✓ Good - grouped and alphabetical
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Dict, List

# ✗ Bad - random order
import json
from pathlib import Path
from datetime import datetime
from typing import Dict
import shutil
```

**WHY:** Easy to scan, find duplicates, see what's imported at a glance

---

## Import Anti-Patterns

**Don't do these:**

```python
# ✗ Wildcard imports
from cortex.apps.handlers.json import *  # What did I import? Who knows!

# ✗ Hardcoded paths
sys.path.insert(0, "/home/patrick/aipass_core")  # Breaks on other machines

# ✗ Relative imports
from ...handlers import something  # Hard to trace, confusing

# ✗ Import entire modules when you need one function
import seed.apps.handlers.json.json_handler  # Long, repetitive
# Better:
from seed.apps.handlers.json import json_handler

# ✗ Circular imports (handler imports module that imports handler)
# Module imports handler ✓
# Handler imports module ✗  # BREAKS INDEPENDENCE
```

---

## Quick Reference

| Import Type | Pattern | Required? |
|-------------|---------|-----------|
| Infrastructure | `AIPASS_ROOT = Path.home() / "aipass_core"` | When needed |
| sys.path | `sys.path.insert(0, str(AIPASS_ROOT))` | When needed |
| Prax logger | `from prax.apps.modules.logger import system_logger as logger` | **Nearly always** |
| CLI service | `from cli.apps.modules import console, header` | When needed |
| API service | `from api.apps.modules import llm_call` | When needed |
| Memory Bank | `from memory_bank.apps.modules import vector_search` | When needed |
| **Drone** | `subprocess.run(["drone", "cmd", ...])` | **CLI only - NEVER import** |
| Standard lib | Grouped by category, alphabetical | Yes |
| Internal | Absolute imports (not relative) | Yes |
| Handler→Module | **FORBIDDEN** (breaks independence) | Never |

---

## Summary

**Import order:** Infrastructure → Standard lib → Prax → Services → Internal

**AIPASS_ROOT pattern:** `Path.home() / "aipass_core"` - never hardcode paths

**Prax logger:** Nearly always imported - system-wide logging service

**Service imports:** CLI, API, Memory Bank imported as libraries; Drone invoked via CLI only

**Drone is special:** NOT a library service - it's a CLI router. Never import from drone.apps.modules

**Handler independence:** Same-branch handler→handler ✓, Handler→own-branch-module ✗, Cross-branch handler ✗

**Third-party libraries:** Pragmatic approach - install what you need as you build

**Consistency:** Same patterns everywhere enables instant comprehension across entire system

---

## Comments

#@comments:2025-11-13:claude: Updated examples to use seed/ instead of fictional cortex/ references
#@comments:2025-11-13:claude: Added Services import section (CLI) to match actual codebase patterns
#@comments:2025-11-13:claude: Toned down "critical" language around Prax to "nearly always" for accuracy
#@comments:2025-11-29:claude: Added Service Categories section clarifying Drone is NOT a library service
#@comments:2025-11-29:claude: Added explicit "Drone: CLI Router Pattern" section with FORBIDDEN import examples
#@comments:2025-11-29:claude: Clarified that branches should NEVER import from drone.apps.modules - Drone resolves @ before calling them
