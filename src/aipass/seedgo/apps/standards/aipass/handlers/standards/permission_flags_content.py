#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: permission_flags_content.py - Permission Flags Standards Content
# Date: 2026-02-26
# Version: 1.0.0
# Category: seed/standards/content
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-02-26): Initial content - permission flags standard
#
# CODE STANDARDS:
#   - Content handler provides Rich-formatted text for display
# =============================================

"""
Permission Flags Standards Content

Provides Rich-formatted reference text for the permission flags standard.
"""


def get_permission_flags_standards() -> str:
    """Return Rich-formatted permission flags standards text"""
    return """[bold white]PERMISSION FLAGS STANDARD[/bold white]

[yellow]PURPOSE:[/yellow]
  Enforce a single, approved permission bypass pattern across AIPass.
  The only acceptable flag is '--permission-mode bypassPermissions'.
  All other bypass patterns are prohibited.

[yellow]THE RULES:[/yellow]

  [bold green]APPROVED[/bold green]
    - --permission-mode bypassPermissions
    - This is the AIPass standard for autonomous agent execution

  [bold red]PROHIBITED[/bold red]
    - --dangerously-skip-permissions
    - --skip-permissions
    - --no-permissions
    - --allow-dangerously-skip-permissions
    - Any other permission bypass flag variant

[yellow]EXAMPLES:[/yellow]

  [red]BAD:[/red]
    # [WRONG] Dangerous skip flag
    claude --dangerously-skip-permissions
    # [WRONG] Generic skip
    subprocess.run(['claude', '--skip-permissions'])

  [green]GOOD:[/green]
    # [CORRECT] AIPass standard permission flag
    subprocess.run(['claude', '--permission-mode', 'bypassPermissions'])
    # [CORRECT] In command construction
    cmd = [CLAUDE_BIN, '--permission-mode', 'bypassPermissions']

[yellow]WHY THIS MATTERS:[/yellow]
  '--dangerously-skip-permissions' is a deprecated Claude CLI flag that
  bypasses ALL safety checks without any granularity. The AIPass standard
  '--permission-mode bypassPermissions' provides controlled permission
  bypass that integrates with the AIPass permission system.
  Using non-standard flags creates inconsistency and security risk."""
