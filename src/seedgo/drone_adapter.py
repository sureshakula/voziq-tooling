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
    """
    # Discover plugins by calling seedgo list and parsing output
    try:
        result = subprocess.run(
            [sys.executable, "-m", "seedgo", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        plugin_output = result.stdout if result.stdout else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        plugin_output = ""

    # Count plugins from the output
    # seedgo list outputs lines like "  plugin-name   source   file_types   description"
    plugin_lines = []
    in_table = False
    for line in plugin_output.splitlines():
        stripped = line.strip()
        if stripped.startswith("---"):
            in_table = True
            continue
        if in_table and stripped:
            parts = stripped.split()
            if len(parts) >= 2:
                name = parts[0]
                # Find description — everything after the file types column
                # The format is: NAME  SOURCE  FILE_TYPES  DESCRIPTION
                desc = ""
                if len(parts) >= 4:
                    # Rejoin from 3rd column onwards as description
                    # Actually the columns are fixed-width, let's just grab the name
                    desc = " ".join(parts[3:]) if len(parts) > 3 else ""
                plugin_lines.append((name, desc))

    lines = []
    lines.append(f"SEEDGO — Code Standards Framework (v{DRONE_MODULE['version']})")
    lines.append("")
    lines.append("Auto-discovered plugin orchestration")
    lines.append("")

    if plugin_lines:
        lines.append(f"Discovered Plugins: {len(plugin_lines)}")
        lines.append("")
        # Find max name length for alignment
        max_name = max(len(name) for name, _ in plugin_lines) if plugin_lines else 20
        for name, desc in plugin_lines:
            if desc:
                lines.append(f"  * {name:<{max_name}}  {desc}")
            else:
                lines.append(f"  * {name}")
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
