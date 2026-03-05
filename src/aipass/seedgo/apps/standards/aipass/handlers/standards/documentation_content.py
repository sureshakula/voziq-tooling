#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: documentation_content.py - Documentation Standards Content Handler
# Date: 2025-11-13
# Version: 1.0.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-13): Truth-checked and condensed - verified against actual codebase
#   - v0.1.0 (2025-11-13): Initial handler - Documentation standards content
#
# CODE STANDARDS:
#   - Handler provides content, module orchestrates output
#   - Pure function - returns string, no side effects
# =============================================

"""
Documentation Standards Content Handler

Condensed documentation standards verified against actual codebase.
Truth-checked 2025-11-13 against cortex and seed production code.
"""


def get_documentation_standards() -> str:
    """Return formatted documentation standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]WHY DOCUMENT?[/bold cyan]",
        "  • AI agents need metadata for context extraction",
        "  • Humans need quick file understanding without reading code",
        "  • Consistency = predictability = faster development",
        "",
        "─" * 70,
        "",
        "[bold cyan]REQUIRED: META HEADER (Every Python file)[/bold cyan]",
        "",
        "  [dim]#!/home/aipass/.venv/bin/python3[/dim]",
        "  [dim]# -*- coding: utf-8 -*-  # Optional[/dim]",
        "  [dim][/dim]",
        "  [dim]# ===================AIPASS====================[/dim]",
        "  [dim]# META DATA HEADER[/dim]",
        "  [dim]# Name: filename.py - Brief Description[/dim]",
        "  [dim]# Date: 2025-XX-XX[/dim]",
        "  [dim]# Version: 0.1.0[/dim]",
        "  [dim]# Category: branch or branch/handlers[/dim]",
        "  [dim]#[/dim]",
        "  [dim]# CHANGELOG (Max 5 entries):[/dim]",
        "  [dim]#   - v0.1.0 (2025-XX-XX): What changed[/dim]",
        "  [dim]#[/dim]",
        "  [dim]# CODE STANDARDS:[/dim]",
        "  [dim]#   - Note about standards followed[/dim]",
        "  [dim]# ==============================================[/dim]",
        "",
        "[yellow]KEY RULES:[/yellow]",
        "  1. Shebang points to AIPass venv",
        "  2. META block = AI-scannable metadata",
        "  3. Category shows branch location (cortex vs cortex/handlers)",
        "  4. CHANGELOG keeps last 5 versions max",
        "",
        "─" * 70,
        "",
        "[bold cyan]REQUIRED: MODULE DOCSTRING[/bold cyan]",
        "",
        "  [dim]\"\"\"",
        "  Module Title",
        "",
        "  Brief purpose description.",
        "  Key features or workflow if needed.",
        "",
        "  Usage examples (optional).",
        "  \"\"\"[/dim]",
        "",
        "[yellow]RULES:[/yellow]",
        "  • Goes right after META block",
        "  • Tells WHAT the file does (not HOW)",
        "  • Keep brief - details go in function docstrings",
        "",
        "─" * 70,
        "",
        "[bold cyan]FUNCTION DOCSTRINGS (Google-style)[/bold cyan]",
        "",
        "  [dim]def function_name(arg: Type) -> ReturnType:",
        "      \"\"\"",
        "      One-line summary",
        "",
        "      Args:",
        "          arg: Description of parameter",
        "",
        "      Returns:",
        "          Description of return value",
        "",
        "      Raises:",
        "          Exception: When raised (optional)",
        "      \"\"\"[/dim]",
        "",
        "[yellow]RULES:[/yellow]",
        "  • Type hints REQUIRED on all functions",
        "  • Args/Returns/Raises sections for clarity",
        "  • Skip Raises if using error handler decorators",
        "",
        "─" * 70,
        "",
        "[bold cyan]IMPORT ORGANIZATION[/bold cyan]",
        "",
        "  [bold]Order (verified in actual code):[/bold]",
        "  1. Infrastructure (AIPASS_ROOT, sys.path) - if needed",
        "  2. Standard library imports",
        "  3. Prax logger (always: [dim]from prax.apps.modules.logger import system_logger as logger[/dim])",
        "  4. Internal handler imports",
        "",
        "─" * 70,
        "",
        "[bold cyan]SECTION SEPARATORS[/bold cyan]",
        "",
        "  [dim]# =============================================================================[/dim]",
        "  [dim]# SECTION NAME[/dim]",
        "  [dim]# =============================================================================[/dim]",
        "",
        "  Common sections: CONSTANTS, FILE OPERATIONS, HELPER FUNCTIONS",
        "",
        "─" * 70,
        "",
        "[bold cyan]INLINE COMMENTS (use sparingly)[/bold cyan]",
        "",
        "  [bold]Good:[/bold] Explain WHY, not WHAT",
        "  [dim]# Memory file suffixes to check (JSON format)[/dim]",
        "  [dim]memory_suffixes = [\".json\", \".local.json\"][/dim]",
        "",
        "  [bold]Bad:[/bold] Obvious narration",
        "  [dim]# Set x to 5[/dim]",
        "  [dim]x = 5[/dim]",
        "",
        "[yellow]REMEMBER:[/yellow] Good code documents itself. Comments are last resort.",
        "",
        "─" * 70,
        "",
        "[bold cyan]VERIFICATION:[/bold cyan]",
        "  Standards verified against actual production code:",
        "  • [dim]/home/aipass/aipass_core/cortex/apps/[/dim]",
        "  • [dim]/home/aipass/seed/apps/[/dim]",
        "",
        "[bold cyan]FULL REFERENCE:[/bold cyan]",
        "  [dim]/home/aipass/standards/CODE_STANDARDS/documentation.md[/dim]",
    ]

    return "\n".join(lines)
