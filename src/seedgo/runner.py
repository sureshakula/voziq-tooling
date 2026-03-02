"""
Seed Go Check Runner

Orchestrates the full check pipeline: plugin discovery, file discovery,
check execution, and score calculation.

This module ties all Phase 1 components together:
  - discover_plugins() — finds all plugins from all sources
  - load_config()      — loads and resolves .seedgo/config.json
  - File walking       — finds target files matching plugin FILE_TYPES,
                         respecting config paths.include/exclude
  - Plugin execution   — calls plugin.check(file_path, plugin_config) per match
  - Scoring            — severity-weighted score calculation (see calculate_score)

Severity-weighted scoring model:
  - error_weight (default 1.0)   — full score deduction
  - warning_weight (default 0.5) — half score deduction
  - info_weight (default 0.0)    — no score deduction (informational)
  - score = (passed_weight / total_weight) * 100
  - Any unresolved ERROR blocks pass regardless of score
"""

import fnmatch
import os
from pathlib import Path
from typing import Optional

from .config import load_config
from .discovery import discover_plugins
from .models import CheckResult, Severity


def run_checks(
    project_root: str,
    files: Optional[list[str]] = None,
    plugins: Optional[list[str]] = None,
) -> tuple[list["CheckResult"], dict]:
    """Run all applicable checks against project files.

    Main orchestration function. Discovers plugins, finds target files,
    executes checks, and returns results with an overall summary.

    Args:
        project_root: Absolute path to the project root (must contain .seedgo/).
        files: Optional list of specific file paths to check. If None or empty,
               discovers all files under project_root matching plugin FILE_TYPES
               and config paths.include/exclude rules.
        plugins: Optional list of plugin names to run. If None or empty, runs
                 all discovered plugins (respecting config enabled/disabled).

    Returns:
        A tuple of:
          - list[CheckResult]: One result per (file, plugin) pair that ran.
          - dict: Overall summary from calculate_overall(). Keys:
              overall_score, passed, threshold, plugins_passed, plugins_failed,
              error_count, warning_count, info_count.
    """
    discovered = discover_plugins(project_root)
    config = load_config(project_root)

    # Apply enabled/disabled plugin filters from config
    enabled_set = set(config.get("plugins", {}).get("enabled", []))
    disabled_set = set(config.get("plugins", {}).get("disabled", []))
    plugin_configs = config.get("plugins", {}).get("config", {})

    # Filter discovered plugins
    active_plugins = []
    for plugin_info in discovered:
        name = plugin_info["name"]
        # Respect CLI plugin filter
        if plugins and name not in plugins:
            continue
        # Respect config enabled list (if non-empty, only those are active)
        if enabled_set and name not in enabled_set:
            continue
        # Respect config disabled list
        if name in disabled_set:
            continue
        active_plugins.append(plugin_info)

    # Determine target files
    if files:
        target_files = [str(Path(f).resolve()) for f in files]
    else:
        target_files = _find_project_files(project_root, config)

    scoring_config = config.get("scoring", {})
    all_results: list[CheckResult] = []

    for file_path in target_files:
        for plugin_info in active_plugins:
            module = plugin_info["module"]
            file_types = getattr(module, "FILE_TYPES", ["*"])

            # Only run plugin on files matching its FILE_TYPES patterns
            if not _file_matches_types(file_path, file_types):
                continue

            plugin_cfg = plugin_configs.get(plugin_info["name"], {})

            try:
                result = module.check(file_path, plugin_cfg or None)
                # Calculate severity-weighted score
                result.score = calculate_score(result, scoring_config)
                all_results.append(result)
            except Exception as exc:
                # Plugin crashed — record as failed result, don't propagate
                all_results.append(CheckResult(
                    plugin=plugin_info["name"],
                    passed=False,
                    checks=[],
                    score=0,
                    file_path=file_path,
                    metadata={"error": str(exc)},
                ))

    overall = calculate_overall(all_results, scoring_config)
    return all_results, overall


def calculate_score(result: "CheckResult", config: dict) -> int:
    """Calculate a severity-weighted score for a single plugin result.

    Score formula:
        score = (passed_weight / total_weight) * 100

    Where each CheckItem contributes its severity's weight to the total.
    If the item passed, its weight also goes to passed_weight.

    Weights (from config or defaults):
        error_weight:   1.0 — full deduction
        warning_weight: 0.5 — half deduction
        info_weight:    0.0 — no deduction (informational only)

    Special cases:
        - No checks → score = 100 (no checks means no violations)
        - total_weight == 0 → score = 100 (all checks are INFO-level only)

    Args:
        result: A CheckResult from a plugin's check() call.
        config: Scoring config dict. Typically config["scoring"] from load_config().
                Keys: error_weight, warning_weight, info_weight.

    Returns:
        Integer score from 0 to 100 (inclusive).
    """
    if not result.checks:
        return 100

    error_weight: float = config.get("error_weight", 1.0)
    warning_weight: float = config.get("warning_weight", 0.5)
    info_weight: float = config.get("info_weight", 0.0)

    weight_map = {
        Severity.ERROR: error_weight,
        Severity.WARNING: warning_weight,
        Severity.INFO: info_weight,
    }

    total_weight: float = 0.0
    passed_weight: float = 0.0

    for check_item in result.checks:
        w = weight_map.get(check_item.severity, error_weight)
        total_weight += w
        if check_item.passed:
            passed_weight += w

    if total_weight == 0.0:
        return 100

    return int((passed_weight / total_weight) * 100)


def calculate_overall(results: list["CheckResult"], config: dict) -> dict:
    """Aggregate per-plugin scores into a single overall summary.

    Pass condition: overall_score >= threshold AND error_count == 0.
    A single unresolved ERROR prevents passing regardless of score.

    Args:
        results: List of CheckResult objects (may span multiple files/plugins).
        config: Scoring config dict. Typically config["scoring"] from load_config().
                Keys used: threshold, error_weight, warning_weight, info_weight.

    Returns:
        Dict with keys:
            overall_score (int): Mean of per-result scores (0-100).
            passed (bool): True if score >= threshold and no ERRORs.
            threshold (int): Pass threshold from config (default 75).
            plugins_passed (int): Count of results with score >= threshold.
            plugins_failed (int): Count of results with score < threshold.
            error_count (int): Unresolved ERROR check items across all results.
            warning_count (int): Unresolved WARNING check items across all results.
            info_count (int): Unresolved INFO check items across all results.
    """
    threshold: int = int(config.get("threshold", 75))

    if not results:
        return {
            "overall_score": 100,
            "passed": True,
            "threshold": threshold,
            "plugins_passed": 0,
            "plugins_failed": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
        }

    # Recalculate scores for all results using the provided config
    scores = [calculate_score(r, config) for r in results]
    overall_score = int(sum(scores) / len(scores))

    # Count unresolved (failed) check items by severity
    error_count = sum(
        1 for r in results for c in r.checks
        if not c.passed and c.severity == Severity.ERROR
    )
    warning_count = sum(
        1 for r in results for c in r.checks
        if not c.passed and c.severity == Severity.WARNING
    )
    info_count = sum(
        1 for r in results for c in r.checks
        if not c.passed and c.severity == Severity.INFO
    )

    # Pass requires score above threshold AND zero unresolved errors
    passed = overall_score >= threshold and error_count == 0

    plugins_passed = sum(1 for s in scores if s >= threshold)
    plugins_failed = sum(1 for s in scores if s < threshold)

    return {
        "overall_score": overall_score,
        "passed": passed,
        "threshold": threshold,
        "plugins_passed": plugins_passed,
        "plugins_failed": plugins_failed,
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
    }


def _find_project_files(project_root: str, config: dict) -> list[str]:
    """Walk the project directory and return files matching include/exclude config.

    Respects config paths.include (list of paths/globs relative to project_root)
    and config paths.exclude (list of paths/globs to skip).

    Args:
        project_root: Absolute path to the project root.
        config: Fully resolved config dict from load_config().

    Returns:
        Sorted list of absolute file path strings.
    """
    root = Path(project_root).resolve()
    paths_config = config.get("paths", {})
    include_patterns: list[str] = paths_config.get("include", ["."])
    exclude_patterns: list[str] = paths_config.get("exclude", [])

    collected: set[str] = set()

    for include in include_patterns:
        include_path = root / include
        # Normalise: if the include pattern resolves to a directory, walk it.
        # Otherwise treat it as a glob from the root.
        if include_path.is_dir():
            for dirpath, _, filenames in os.walk(include_path):
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    collected.add(str(fp.resolve()))
        else:
            # Try as a glob pattern relative to root
            for fp in root.glob(include):
                if fp.is_file():
                    collected.add(str(fp.resolve()))

    # Apply exclude patterns — match against relative paths
    result: list[str] = []
    for file_path in sorted(collected):
        try:
            rel = str(Path(file_path).relative_to(root))
        except ValueError:
            rel = file_path

        excluded = False
        for pattern in exclude_patterns:
            # Match against relative path or just the filename
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(os.path.basename(rel), pattern):
                excluded = True
                break
            # Also handle directory prefixes: "tests/" should exclude "tests/foo.py"
            if rel.startswith(pattern.rstrip("/") + "/") or rel.startswith(pattern):
                excluded = True
                break

        if not excluded:
            result.append(file_path)

    return result


def _file_matches_types(file_path: str, file_types: list[str]) -> bool:
    """Check whether a file path matches any of the plugin's FILE_TYPES patterns.

    Uses fnmatch glob semantics against the file's basename.
    A pattern of "*" matches any file.

    Args:
        file_path: Absolute or relative path to the file.
        file_types: List of glob patterns from the plugin's FILE_TYPES constant
                    (e.g., ["*.py"], ["*.js", "*.ts"]).

    Returns:
        True if the file matches at least one pattern.
    """
    name = os.path.basename(file_path)
    for pattern in file_types:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False
