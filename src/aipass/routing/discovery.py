"""
Module and command discovery for AIPass branch introspection.

Introspects branch capabilities by querying entry points for help text
and scanning module directories as a fallback.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import CommandExecutionError
from .resolver import list_branches, resolve_branch

logger = logging.getLogger(__name__)


@dataclass
class HelpResult:
    """
    Structured result from a help query.

    Attributes:
        branch: The branch name the help was retrieved from.
        command: The specific command queried, or None for top-level help.
        text: Raw help text (stdout or stderr from the entry point).
        commands_found: List of command names parsed from the help text.
    """

    branch: str
    command: Optional[str]
    text: str
    commands_found: List[str] = field(default_factory=list)


def _get_entry_point(branch_path: str, branch_name: str) -> Optional[Path]:
    """
    Return the apps/{branch_name}.py entry point path if it exists, else None.

    Args:
        branch_path: Absolute path to the branch directory.
        branch_name: Lowercase branch name.

    Returns:
        Path to the entry point, or None if it does not exist.
    """
    entry_point = Path(branch_path) / "apps" / f"{branch_name}.py"
    return entry_point if entry_point.exists() else None


def _scan_modules_directory(branch_path: str) -> List[str]:
    """
    Scan apps/modules/ for .py files and return their stems as command names.

    Used as a fallback when the entry point's --help output cannot be parsed.

    Args:
        branch_path: Absolute path to the branch directory.

    Returns:
        Sorted list of module stem names (without .py extension), excluding
        __init__ and __main__.
    """
    modules_dir = Path(branch_path) / "apps" / "modules"
    if not modules_dir.is_dir():
        return []

    excluded = {"__init__", "__main__"}
    return sorted(
        f.stem
        for f in modules_dir.glob("*.py")
        if f.stem not in excluded
    )


def _parse_help_for_commands(help_text: str) -> List[str]:
    """
    Parse --help output to extract a list of available commands.

    Handles multiple CLI framework formats:
    - Section-based (custom CLIs, argparse subparsers): looks for headers
      labelled "commands", "subcommands", or "available commands".
    - Click-style: looks for indented entries under "Commands:" or "Options:".
    - Positional args listing: lines matching ``{command}`` or ``[command]``
      at the start of usage lines.

    Falls back to returning an empty list if no recognisable pattern is found.

    Args:
        help_text: Raw stdout from ``python3 entry.py --help``.

    Returns:
        List of command names parsed from the help text.
    """
    commands: List[str] = []
    in_commands_section = False

    section_markers = {"commands", "subcommands", "available commands"}

    for line in help_text.splitlines():
        stripped = line.strip()

        # Detect section header lines (e.g. "Commands:", "Available commands:")
        if any(marker in stripped.lower() for marker in section_markers):
            in_commands_section = True
            continue

        # A blank line ends the current section.
        if in_commands_section and not stripped:
            in_commands_section = False
            continue

        if in_commands_section:
            # Indented lines that start with a word are command entries.
            if line.startswith((" ", "\t")) and stripped:
                # Take the first token as the command name.
                token = stripped.split()[0]
                # Skip lines that look like option flags.
                if not token.startswith("-"):
                    commands.append(token)

    return commands


def discover_modules(target: str) -> List[str]:
    """
    Discover available commands for a branch.

    Resolution order:
    1. Resolve @target to its absolute path via the registry.
    2. Attempt to run ``python3 apps/{name}.py --help`` and parse the output
       for a commands section.
    3. If parsing yields nothing, fall back to scanning ``apps/modules/`` for
       .py file stems.

    Args:
        target: Symbolic branch name with or without @ prefix (e.g., "@flow").

    Returns:
        List of discovered command/module names (may be empty).

    Raises:
        BranchNotFoundError: If the target branch is not in the registry.
    """
    # Step 1: resolve — BranchNotFoundError propagates to caller.
    branch_path = resolve_branch(target)
    branch_name = target.lstrip("@").lower()

    # Step 2: try --help on the entry point.
    entry_point = _get_entry_point(branch_path, branch_name)
    if entry_point is not None:
        try:
            result = subprocess.run(
                ["python3", str(entry_point.relative_to(branch_path)), "--help"],
                cwd=branch_path,
                capture_output=True,
                timeout=10,
                shell=False,
            )
            help_text = result.stdout.decode("utf-8", errors="replace")
            if not help_text:
                help_text = result.stderr.decode("utf-8", errors="replace")

            commands = _parse_help_for_commands(help_text)
            if commands:
                return commands
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Step 3: fallback — scan modules directory.
    return _scan_modules_directory(branch_path)


def get_help(target: str, command: Optional[str] = None) -> HelpResult:
    """
    Get structured help for a branch or a specific command.

    Executes:
        python3 apps/{name}.py --help              (when command is None)
        python3 apps/{name}.py {command} --help    (when command is given)

    Args:
        target: Symbolic branch name with or without @ prefix (e.g., "@flow").
        command: Specific command to get help for (default: None).

    Returns:
        HelpResult with branch, command, text, and commands_found populated.

    Raises:
        BranchNotFoundError: If the target branch is not in the registry.
        CommandExecutionError: If the entry point does not exist or execution
            fails.
    """
    branch_path = resolve_branch(target)
    branch_name = target.lstrip("@").lower()

    entry_point = _get_entry_point(branch_path, branch_name)
    if entry_point is None:
        raise CommandExecutionError(
            f"Entry point not found for branch '{branch_name}': "
            f"{Path(branch_path) / 'apps' / (branch_name + '.py')}"
        )

    relative_entry = str(entry_point.relative_to(branch_path))
    if command is None:
        cmd_args = [relative_entry, "--help"]
    else:
        cmd_args = [relative_entry, command, "--help"]

    try:
        result = subprocess.run(
            ["python3"] + cmd_args,
            cwd=branch_path,
            capture_output=True,
            timeout=10,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        raise CommandExecutionError(
            f"Help command timed out for branch '{branch_name}'"
        ) from e
    except OSError as e:
        raise CommandExecutionError(
            f"OS error getting help for branch '{branch_name}': {e}"
        ) from e

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    # Many CLIs write help to stderr; return whichever is non-empty.
    text = stdout if stdout.strip() else stderr
    commands_found = _parse_help_for_commands(text)

    return HelpResult(
        branch=branch_name,
        command=command,
        text=text,
        commands_found=commands_found,
    )


def get_system_help() -> Dict[str, HelpResult]:
    """
    Aggregate help across all active branches in the registry.

    Iterates over every active branch and attempts to retrieve top-level help
    via ``get_help()``.  Branches whose entry point is missing or whose help
    command fails are silently skipped (the error is logged at DEBUG level).

    Returns:
        Mapping of branch name (without @ prefix) to its HelpResult.
        Branches that cannot be queried are omitted from the result.

    Example:
        >>> results = get_system_help()
        >>> for branch, help_result in results.items():
        ...     print(f"{branch}: {help_result.commands_found}")
    """
    results: Dict[str, HelpResult] = {}

    # list_branches returns names with @ prefix; iterate all active branches.
    active_branches = list_branches(status="active")

    for symbolic_name in active_branches:
        branch_name = symbolic_name.lstrip("@")
        try:
            help_result = get_help(symbolic_name)
            results[branch_name] = help_result
        except Exception as exc:
            logger.debug(
                "get_system_help: skipping branch '%s': %s",
                branch_name,
                exc,
            )

    return results
