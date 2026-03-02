"""
Seed Go Result Reporter

Formats check results for display in three output modes:

  "human"  — Colored terminal output using raw ANSI escape codes.
             Shows plugin names, pass/fail verdicts, scores, and per-check
             items with severity markers. Summary line at the bottom.
             No external dependencies (no Rich, no colorama).

  "json"   — Machine-readable JSON dict. Includes all result data and the
             overall summary. Safe for piping to other tools.

  "github" — GitHub Actions annotation format. Emits ::error and ::warning
             annotation lines that GitHub renders inline on PR diffs.

All formats are produced by a single entry point: report_results().
"""

import dataclasses
import json
from .models import CheckResult, Severity


# ---------------------------------------------------------------------------
# ANSI color codes (raw escape sequences — zero dependencies)
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_DIM = "\033[2m"


def report_results(
    results: list[CheckResult],
    overall: dict,
    format: str = "human",
) -> str:
    """Format check results for display.

    Dispatches to the appropriate formatter based on the format argument.

    Args:
        results: List of CheckResult objects returned by run_checks().
        overall: Overall summary dict returned by run_checks() (from
                 calculate_overall()). Expected keys: overall_score, passed,
                 threshold, plugins_passed, plugins_failed, error_count,
                 warning_count, info_count.
        format: Output format. One of:
                  "human"  — Colored terminal output (default).
                  "json"   — JSON-encoded string, machine-readable.
                  "github" — GitHub Actions annotation lines.

    Returns:
        Formatted string ready to print or write to stdout.

    Raises:
        ValueError: If format is not one of the three supported values.
    """
    if format == "human":
        return _format_human(results, overall)
    elif format == "json":
        return _format_json(results, overall)
    elif format == "github":
        return _format_github(results, overall)
    else:
        raise ValueError(f"Unknown format {format!r}. Choose: human, json, github")


# ---------------------------------------------------------------------------
# Human formatter
# ---------------------------------------------------------------------------


def _format_human(results: list[CheckResult], overall: dict) -> str:
    """Produce colored terminal output for human consumption.

    Layout:
        plugin-name .............. PASS (100/100)
        another-plugin ........... FAIL (60/100)
          ✗ check-name: message [line N]
            hint: fix_hint text
          ✓ passing-check: message

        Overall: 80/100 — PASS (threshold: 75)
        2 checks ran, 1 passed, 1 failed
    """
    lines: list[str] = []

    if not results:
        lines.append(f"{_DIM}No checks ran.{_RESET}")
        lines.append(_summary_line(overall))
        return "\n".join(lines)

    # Group results by plugin name for a cleaner display
    for result in results:
        lines.append(_plugin_header_line(result))
        for item in result.checks:
            lines.extend(_check_item_lines(item))

    lines.append("")
    lines.append(_summary_line(overall))
    lines.append(_counts_line(overall))

    return "\n".join(lines)


def _plugin_header_line(result: CheckResult) -> str:
    """Format the plugin name + verdict + score header line."""
    name = result.plugin
    score = result.score
    file_label = f"  [{result.file_path}]" if result.file_path else ""

    dots = "." * max(1, 50 - len(name) - len(file_label))

    if result.passed:
        verdict = f"{_GREEN}PASS{_RESET}"
    else:
        verdict = f"{_RED}FAIL{_RESET}"

    score_str = f"({score}/100)"
    return f"  {_BOLD}{name}{_RESET}{file_label} {_DIM}{dots}{_RESET} {verdict} {_DIM}{score_str}{_RESET}"


def _check_item_lines(item) -> list[str]:
    """Format a single CheckItem into one or two display lines."""
    lines: list[str] = []

    if item.passed:
        marker = f"{_GREEN}✓{_RESET}"
        color = _DIM
    elif item.severity == Severity.ERROR:
        marker = f"{_RED}✗{_RESET}"
        color = _RED
    elif item.severity == Severity.WARNING:
        marker = f"{_YELLOW}⚠{_RESET}"
        color = _YELLOW
    else:
        marker = f"{_CYAN}ℹ{_RESET}"
        color = _CYAN

    line_ref = f" [line {item.line}]" if item.line is not None else ""
    main = f"    {marker} {color}{item.name}{_RESET}: {item.message}{line_ref}"
    lines.append(main)

    if item.fix_hint and not item.passed:
        lines.append(f"      {_DIM}hint: {item.fix_hint}{_RESET}")

    return lines


def _summary_line(overall: dict) -> str:
    """Format the overall score summary line."""
    score = overall.get("overall_score", 100)
    passed = overall.get("passed", True)
    threshold = overall.get("threshold", 75)

    if passed:
        verdict = f"{_GREEN}{_BOLD}PASS{_RESET}"
    else:
        verdict = f"{_RED}{_BOLD}FAIL{_RESET}"

    return f"  {_BOLD}Overall:{_RESET} {score}/100 — {verdict} {_DIM}(threshold: {threshold}){_RESET}"


def _counts_line(overall: dict) -> str:
    """Format the plugin count summary line."""
    p_passed = overall.get("plugins_passed", 0)
    p_failed = overall.get("plugins_failed", 0)
    total = p_passed + p_failed
    errors = overall.get("error_count", 0)
    warnings = overall.get("warning_count", 0)

    parts = [f"{total} check(s) ran", f"{p_passed} passed", f"{p_failed} failed"]
    if errors:
        parts.append(f"{_RED}{errors} error(s){_RESET}")
    if warnings:
        parts.append(f"{_YELLOW}{warnings} warning(s){_RESET}")

    return "  " + ", ".join(parts)


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def _format_json(results: list[CheckResult], overall: dict) -> str:
    """Produce a JSON string containing all results and the overall summary.

    The JSON structure is:
    {
      "overall_score": int,
      "passed": bool,
      "threshold": int,
      "plugins_passed": int,
      "plugins_failed": int,
      "error_count": int,
      "warning_count": int,
      "info_count": int,
      "results": [
        {
          "plugin": str,
          "passed": bool,
          "score": int,
          "file_path": str,
          "checks": [...],
          "metadata": {...}
        },
        ...
      ]
    }
    """
    serializable_results = []
    for result in results:
        d = dataclasses.asdict(result)
        # Convert Severity enum values to plain strings for JSON
        for check in d.get("checks", []):
            if isinstance(check.get("severity"), Severity):
                check["severity"] = check["severity"].value
            elif hasattr(check.get("severity"), "value"):
                check["severity"] = check["severity"].value
        serializable_results.append(d)

    payload = dict(overall)
    payload["results"] = serializable_results

    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# GitHub Actions formatter
# ---------------------------------------------------------------------------


def _format_github(results: list[CheckResult], overall: dict) -> str:  # noqa: ARG001
    """Produce GitHub Actions workflow annotation lines.

    Each failed check item becomes an annotation:
      ::error file=path/to/file.py,line=42::message [plugin-name]
      ::warning file=path/to/file.py,line=42::message [plugin-name]
      ::notice file=path/to/file.py::message [plugin-name]

    INFO items are emitted as ::notice. Passed items are omitted.

    See: https://docs.github.com/en/actions/writing-workflows/
         choosing-what-your-workflow-does/workflow-commands-for-github-actions
    """
    lines: list[str] = []

    for result in results:
        for item in result.checks:
            if item.passed:
                continue  # Skip passing checks — no annotation needed

            file_part = f"file={result.file_path}" if result.file_path else ""
            line_part = f",line={item.line}" if item.line is not None else ""
            location = f"{file_part}{line_part}"
            location_prefix = f"{location}::" if location else ""

            message = f"{item.message} [{result.plugin}]"

            if item.severity == Severity.ERROR:
                lines.append(f"::error {location_prefix}{message}")
            elif item.severity == Severity.WARNING:
                lines.append(f"::warning {location_prefix}{message}")
            else:
                lines.append(f"::notice {location_prefix}{message}")

    return "\n".join(lines)
