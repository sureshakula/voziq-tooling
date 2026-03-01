"""
Command routing logic for the AIPass routing module.

Routes commands to branch entry points by resolving symbolic @branch names,
locating the branch's apps/{name}.py entry point, and executing via subprocess.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import CommandExecutionError
from .executor import CommandResult, execute_command
from .resolver import list_branches, resolve_branch

logger = logging.getLogger(__name__)


def _find_entry_point(branch_path: str, branch_name: str) -> Path:
    """
    Locate the apps/{branch_name}.py entry point for a branch.

    Args:
        branch_path: Absolute path to the branch directory.
        branch_name: Lowercase branch name from the registry.

    Returns:
        Path to the entry point file.

    Raises:
        CommandExecutionError: If the entry point does not exist.
    """
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
) -> CommandResult:
    """
    Route a command to a branch's entry point.

    Resolves @target to an absolute path, locates the branch entry point at
    {path}/apps/{branch_name}.py, then executes:
        python3 apps/{name}.py {command} [args...]

    The process runs with cwd set to the branch root so relative paths inside
    the entry point (e.g. imports of sibling modules) resolve correctly.

    Args:
        target: Symbolic branch name with or without @ prefix (e.g., "@flow").
        command: Command to pass to the branch entry point (e.g., "status").
        args: Optional list of additional arguments (default: None).
        timeout: Maximum execution time in seconds (default: 30).

    Returns:
        CommandResult with stdout, stderr, exit_code, branch, and command.

    Raises:
        BranchNotFoundError: If the target branch is not in the registry.
        CommandExecutionError: If the entry point is missing or execution fails.
    """
    if args is None:
        args = []

    # Step 1: Resolve @target → absolute path.  BranchNotFoundError propagates.
    branch_path = resolve_branch(target)

    # Derive the canonical branch name (strip leading @).
    branch_name = target.lstrip("@").lower()

    # Step 2: Locate entry point.
    entry_point = _find_entry_point(branch_path, branch_name)

    # Step 3: Build argument list and execute.
    # Use a relative path to apps/{name}.py so the subprocess cwd is the branch root.
    relative_entry = str(entry_point.relative_to(branch_path))
    cmd_args = [relative_entry, command] + list(args)

    result = execute_command(
        executable="python3",
        args=cmd_args,
        cwd=branch_path,
        timeout=timeout,
    )

    # Annotate result with routing context.
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
    """
    Route the same command to ALL active branches in the registry.

    Iterates over every active branch and calls ``route_command`` on each.
    Individual branch failures (missing entry point, execution error) are
    logged at WARNING level and recorded as a CommandResult with exit_code=-1
    and the error message in stderr.  Processing continues regardless of
    per-branch failures.

    Args:
        command: Command to pass to every branch entry point (e.g., "status").
        args: Optional list of additional arguments forwarded to each branch.
        timeout: Maximum execution time per branch in seconds (default: 30).

    Returns:
        Dictionary mapping branch name (without @ prefix) to its CommandResult.
        Branches that fail are included with exit_code=-1 and error in stderr.

    Example:
        >>> results = route_all("status")
        >>> for branch, result in results.items():
        ...     print(f"{branch}: exit={result.exit_code}")
    """
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
                branch_name,
                command,
                exc,
            )
            results[branch_name] = CommandResult(
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                branch=branch_name,
                command=command,
            )

    return results
