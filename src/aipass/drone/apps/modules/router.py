"""
Command routing logic for the AIPass drone module.

Routes commands to branch entry points by resolving symbolic @branch names,
locating the branch's apps/{name}.py entry point, and executing via subprocess.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from aipass.drone.apps.handlers.exceptions import CommandExecutionError
from aipass.drone.apps.handlers.executor import CommandResult, execute_command
from .resolver import list_branches, resolve_branch

logger = logging.getLogger(__name__)


def _find_entry_point(branch_path: str, branch_name: str) -> Path:
    """Locate the apps/{branch_name}.py entry point for a branch."""
    entry_point = Path(branch_path) / "apps" / f"{branch_name}.py"
    if not entry_point.exists():
        raise CommandExecutionError(
            f"Entry point not found for branch '{branch_name}': {entry_point}"
        )
    return entry_point


def route_command(
    target: str,
    command: str,
    args: Optional[List[str]] = None,
    timeout: int = 30,
    interactive: bool = False,
) -> CommandResult:
    """Route a command to a branch's entry point.

    Resolves @target to an absolute path, locates the branch entry point at
    {path}/apps/{branch_name}.py, then executes:
        python3 apps/{name}.py {command} [args...]

    Args:
        interactive: If True, inherit stdio for long-running/interactive commands.
    """
    if args is None:
        args = []

    branch_path = resolve_branch(target)
    branch_name = target.lstrip("@").lower()

    entry_point = _find_entry_point(branch_path, branch_name)

    relative_entry = str(entry_point.relative_to(branch_path))
    cmd_args = [relative_entry, command] + list(args)

    # Pass caller's CWD so target branches can detect who invoked them
    caller_env = {"AIPASS_CALLER_CWD": str(Path.cwd())}

    result = execute_command(
        executable=sys.executable,
        args=cmd_args,
        cwd=branch_path,
        timeout=timeout,
        env=caller_env,
        interactive=interactive,
    )

    return CommandResult(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        branch=branch_name,
        command=command,
    )


def route_all(
    command: str,
    args: Optional[List[str]] = None,
    timeout: int = 30,
) -> Dict[str, CommandResult]:
    """Route the same command to ALL active branches in the registry."""
    if args is None:
        args = []

    results: Dict[str, CommandResult] = {}
    active_branches = list_branches(status="active")

    for symbolic_name in active_branches:
        branch_name = symbolic_name.lstrip("@")
        try:
            result = route_command(symbolic_name, command, args=list(args), timeout=timeout)
            results[branch_name] = result
        except Exception as exc:
            logger.warning(
                "route_all: branch '%s' failed for command '%s': %s",
                branch_name, command, exc,
            )
            results[branch_name] = CommandResult(
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                branch=branch_name,
                command=command,
            )

    return results
