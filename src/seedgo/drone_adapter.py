"""Drone adapter for seedgo — code standards framework.

Provides the drone module interface so `drone @seedgo` commands work.
Delegates to the seedgo CLI via subprocess for clean stdout/stderr capture.

Drone adapter contract:
  - DRONE_MODULE: dict with name, version, description
  - handle_command(command, args) -> dict with stdout/stderr/exit_code
  - get_help(command=None) -> str  (usage documentation)
  - get_introspective() -> str     (discovery — what's connected)
"""

from __future__ import annotations

import subprocess
import sys

DRONE_MODULE = {
    "name": "seedgo",
    "version": "1.0.0",
    "description": "Code standards framework — check and audit code against configurable standards",
}

_HELP_TEXT = """\
seedgo — code standards framework

Commands:
  check [FILE ...]   Run checks on files (or project if no files given)
  audit [PATH ...]   Alias for check (run audit on paths)
  list               Show all discovered plugins
  init               Initialize .seedgo/ config in current directory

Options (for check/audit):
  --format FORMAT    Output format: human, json, github (default: human)
  --threshold N      Pass threshold 0-100 (default: 75)
  --plugin NAME      Run only this plugin

Examples:
  drone @seedgo check src/myfile.py
  drone @seedgo audit src/
  drone @seedgo list
  drone @seedgo init --profile strict
"""


def get_introspective() -> str:
    """Return discovery view — what's connected to this module.

    Called when user types `drone @seedgo` with no arguments.
    Shows connected plugins and available commands at a glance.

    Uses direct import of seedgo's discovery module instead of parsing
    CLI output, since the adapter lives in the same package.
    """
    # Import discovery directly — no subprocess parsing needed
    try:
        from seedgo.discovery import discover_plugins
    except ImportError:
        return f"SEEDGO — Code Standards Framework (v{DRONE_MODULE['version']})\n\nDiscovered Plugins: 0\n"

    try:
        plugins = discover_plugins(None)
    except Exception:
        plugins = []

    lines = []
    lines.append(f"SEEDGO — Code Standards Framework (v{DRONE_MODULE['version']})")
    lines.append("")
    lines.append("Auto-discovered plugin orchestration")
    lines.append("")

    if plugins:
        lines.append(f"Discovered Plugins: {len(plugins)}")
        lines.append("")
        max_name = max(len(p["name"]) for p in plugins)
        for p in plugins:
            desc = getattr(p["module"], "PLUGIN_DESCRIPTION", "")
            if desc:
                lines.append(f"  * {p['name']:<{max_name}}  {desc}")
            else:
                lines.append(f"  * {p['name']}")
    else:
        lines.append("Discovered Plugins: 0")

    lines.append("")
    lines.append("Run 'drone @seedgo --help' for usage information")
    lines.append("")

    return "\n".join(lines)


def handle_command(command: str, args: list[str] | None = None) -> dict:
    """Handle a command routed by drone.

    Returns dict with stdout, stderr, exit_code.
    """
    cmd_args = args or []

    # Map commands to seedgo CLI arguments
    if command == "audit":
        # audit is an alias for check
        cli_args = ["check"] + cmd_args
    elif command in ("check", "list", "init"):
        cli_args = [command] + cmd_args
    else:
        return {
            "stdout": "",
            "stderr": f"seedgo: unknown command '{command}'\nRun 'drone @seedgo --help' for usage.\n",
            "exit_code": 1,
        }

    try:
        result = subprocess.run(
            [sys.executable, "-m", "seedgo"] + cli_args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "seedgo: command timed out after 120 seconds\n",
            "exit_code": 1,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": "seedgo: Python executable not found\n",
            "exit_code": 1,
        }


def get_help(command: str | None = None) -> str:
    """Return help text for drone @seedgo."""
    if command is None:
        return _HELP_TEXT

    # For specific command help, delegate to seedgo
    try:
        result = subprocess.run(
            [sys.executable, "-m", "seedgo", command, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout if result.stdout else _HELP_TEXT
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _HELP_TEXT
