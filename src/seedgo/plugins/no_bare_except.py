"""
Seed Go Plugin: no-bare-except

Flags bare `except:` clauses in Python files. Bare excepts swallow all
exceptions including KeyboardInterrupt and SystemExit, which can cause
programs to become unresponsive or hide serious errors.

Correct usage:
    except Exception:          # catches all normal exceptions
    except (ValueError, TypeError):  # specific exceptions preferred

Linters like ruff have this rule (E722), so this plugin demonstrates how
Seed Go can layer additional context and fixable hints on top of or alongside
traditional linter rules.
"""

import re
from pathlib import Path

from seedgo.models import CheckItem, CheckResult, Severity

PLUGIN_NAME = "no-bare-except"
PLUGIN_DESCRIPTION = "Flag bare except: clauses that swallow all exceptions."
FILE_TYPES = ["*.py"]
PLUGIN_VERSION = "1.0.0"

# Matches `except:` with nothing after the colon (bare except)
# Allows for trailing whitespace and inline comments
_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:\s*(#.*)?$")


def check(file_path: str, config: dict | None = None) -> CheckResult:
    """Check a Python file for bare except: clauses.

    Parses the file line-by-line, tracking docstring/multiline string state
    to avoid false positives from `except:` appearing inside string literals.

    Args:
        file_path: Absolute path to the Python file to check.
        config: Optional plugin config dict (unused by this plugin).

    Returns:
        CheckResult with one CheckItem per bare except found, plus a summary
        item if none are found.
    """
    _ = config  # Part of plugin interface contract

    try:
        source = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        # Cannot read file — return passing result (don't block on I/O errors)
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "file_read_error"},
        )

    violations: list[CheckItem] = []
    lines = source.splitlines()

    # Track whether we're inside a triple-quoted string to avoid false positives
    in_triple_single = False
    in_triple_double = False

    for lineno, raw_line in enumerate(lines, start=1):
        # Simplified triple-quote tracking (handles common cases)
        # Count unescaped triple quotes — toggle state
        stripped = raw_line

        # Toggle triple-string state before checking for except
        # Count occurrences of ''' and """ (not inside each other)
        if not in_triple_double:
            triple_single_count = stripped.count("'''")
            if triple_single_count % 2 == 1:
                in_triple_single = not in_triple_single

        if not in_triple_single:
            triple_double_count = stripped.count('"""')
            if triple_double_count % 2 == 1:
                in_triple_double = not in_triple_double

        # Only check lines that are not inside a string literal
        if in_triple_single or in_triple_double:
            continue

        # Strip the line to check if it's a comment
        stripped_line = raw_line.strip()
        if stripped_line.startswith("#"):
            continue

        if _BARE_EXCEPT_RE.match(raw_line):
            violations.append(
                CheckItem(
                    name="bare-except",
                    passed=False,
                    message=f"Bare `except:` at line {lineno} — catches ALL exceptions including KeyboardInterrupt.",
                    severity=Severity.WARNING,
                    line=lineno,
                    fix_hint="Replace with `except Exception:` or a more specific exception type.",
                )
            )

    if violations:
        passed = False
        checks = violations
    else:
        passed = True
        checks = [
            CheckItem(
                name="bare-except",
                passed=True,
                message="No bare except: clauses found.",
                severity=Severity.WARNING,
            )
        ]

    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=passed,
        checks=checks,
        file_path=file_path,
        metadata={"violations_found": len(violations)},
    )
