"""
Seed Go Result Reporter

Formats check results for display in three output modes:

  "human"  — Rich-formatted terminal output using the display module.
             Shows plugin names, pass/fail verdicts, scores, and per-check
             items with severity markers. Summary line at the bottom.

  "json"   — Machine-readable JSON dict. Includes all result data and the
             overall summary. Safe for piping to other tools.

  "github" — GitHub Actions annotation format. Emits ::error and ::warning
             annotation lines that GitHub renders inline on PR diffs.

All formats are produced by a single entry point: report_results().
"""

import dataclasses
import json
from .models import CheckResult, Severity
from .display import (
    print_header,
    print_plugin,
    print_check_item,
    print_summary,
    print_counts,
    print_separator,
    print_no_results,
)


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
                  "human"  — Rich terminal output (default). Prints directly,
                             returns empty string.
                  "json"   — JSON-encoded string, machine-readable.
                  "github" — GitHub Actions annotation lines.

    Returns:
        Formatted string ready to print or write to stdout.
        For "human" format, prints directly and returns empty string.

    Raises:
        ValueError: If format is not one of the three supported values.
    """
    if format == "human":
        _format_human(results, overall)
        return ""
    elif format == "json":
        return _format_json(results, overall)
    elif format == "github":
        return _format_github(results, overall)
    else:
        raise ValueError(f"Unknown format {format!r}. Choose: human, json, github")


# ---------------------------------------------------------------------------
# Human formatter
# ---------------------------------------------------------------------------


def _format_human(results: list[CheckResult], overall: dict) -> None:
    """Print Rich-formatted terminal output for human consumption.

    Prints directly to the Rich console via the display module.

    Layout:
        ╭─ SEEDGO ─────────────────────────────╮
        │  Code Standards Check                 │
        │  5 plugins · 3 files · threshold: 75  │
        ╰───────────────────────────────────────╯

        ✓ plugin-name  file.py ········· PASS (100/100)
            ✓ check-name: message
        ✗ another-plugin  file.py ······ FAIL (60/100)
            ✗ check-name: message [line N]
              hint: fix_hint text

        ─────────────────────────────────────────
        Overall: 80/100 — PASS (threshold: 75)
        2 checks ran, 1 passed, 1 failed
    """
    score = overall.get("overall_score", 100)
    threshold = overall.get("threshold", 75)
    passed = overall.get("passed", True)
    p_passed = overall.get("plugins_passed", 0)
    p_failed = overall.get("plugins_failed", 0)

    # Header
    total_plugins = p_passed + p_failed
    subtitle = f"{total_plugins} plugin(s) · threshold: {threshold}"
    print_header("SEEDGO — Code Standards Check", subtitle)

    if not results:
        print_no_results()
        print_separator()
        print_summary(score, passed, threshold)
        return

    for result in results:
        print_plugin(result.plugin, result.file_path, result.passed, result.score)
        for item in result.checks:
            print_check_item(
                item.name, item.passed, item.message, item.severity,
                line=item.line, fix_hint=item.fix_hint,
            )

    print_separator()
    print_summary(score, passed, threshold)
    print_counts(
        p_passed, p_failed,
        error_count=overall.get("error_count", 0),
        warning_count=overall.get("warning_count", 0),
    )


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
