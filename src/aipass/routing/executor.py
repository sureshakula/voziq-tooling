"""
Safe subprocess execution for branch command routing.

Wraps subprocess.run with safety guards: timeout enforcement, no shell injection,
captured output, and consistent error wrapping via CommandExecutionError.

Defines CommandResult, the shared return type for all routing operations.
"""

import subprocess
from dataclasses import dataclass
from typing import List

from .exceptions import CommandExecutionError


@dataclass
class CommandResult:
    """
    Result of a routed command execution.

    Attributes:
        stdout: Captured standard output from the command.
        stderr: Captured standard error from the command.
        exit_code: Process exit code (0 typically indicates success).
        branch: The branch name the command was routed to.
        command: The command string that was executed.
    """

    stdout: str
    stderr: str
    exit_code: int
    branch: str
    command: str


def execute_command(
    executable: str,
    args: List[str],
    cwd: str,
    timeout: int = 30,
) -> CommandResult:
    """
    Execute a command via subprocess with safety guards.

    Args:
        executable: The executable to run (e.g., "python3").
        args: List of arguments (e.g., ["apps/flow.py", "status"]).
        cwd: Working directory for command execution (absolute path).
        timeout: Maximum execution time in seconds (default: 30).

    Returns:
        CommandResult with stdout, stderr, exit_code populated.
        branch and command fields are empty strings; route_command populates them.

    Raises:
        CommandExecutionError: If the process times out, the executable is not
            found, or any other OS-level error prevents execution.

    Notes:
        - Never uses shell=True to prevent shell injection attacks.
        - Always captures stdout and stderr separately.
        - Decodes output as UTF-8, replacing undecodable bytes.
    """
    full_cmd = [executable] + list(args)

    try:
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        raise CommandExecutionError(
            f"Command timed out after {timeout}s: {' '.join(full_cmd)}"
        ) from e
    except FileNotFoundError as e:
        raise CommandExecutionError(
            f"Executable not found: {executable!r}"
        ) from e
    except OSError as e:
        raise CommandExecutionError(
            f"OS error executing command: {e}"
        ) from e

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    return CommandResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=result.returncode,
        branch="",
        command="",
    )
