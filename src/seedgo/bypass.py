"""
Seed Go Bypass Utility

Shared bypass logic extracted from Seed's ~15 duplicated is_bypassed() implementations.
Plugins call this from seedgo.bypass — no per-plugin copies needed.

Bypass rules live in .seedgo/bypass.json and support:
  - Entire standard bypass for a file (no lines specified)
  - Line-specific bypass for targeted suppressions

Bypass config format (.seedgo/bypass.json):
  {
    "version": "1.0.0",
    "bypass": [
      {
        "file": "src/legacy.py",
        "plugin": "type-hints-required",
        "reason": "Legacy code — rewrite planned for Q2"
      },
      {
        "file": "src/utils.py",
        "plugin": "no-bare-except",
        "lines": [42, 78],
        "reason": "Generic handler for external API calls"
      }
    ]
  }
"""

import json
from pathlib import Path


def load_bypass_rules(project_root: str) -> list[dict]:
    """Load bypass rules from .seedgo/bypass.json.

    Args:
        project_root: Path to the project root (directory containing .seedgo/).

    Returns:
        List of bypass rule dicts. Empty list if bypass.json does not exist.
    """
    bypass_path = Path(project_root) / ".seedgo" / "bypass.json"
    if not bypass_path.exists():
        return []

    try:
        with open(bypass_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    return data.get("bypass", [])


def is_bypassed(
    file_path: str,
    plugin: str,
    line: int | None = None,
    bypass_rules: list[dict] | None = None,
    project_root: str | None = None,
) -> bool:
    """Check if a violation should be bypassed.

    This is the single shared implementation — plugins import this instead of
    maintaining their own copy. Eliminates the duplication pattern seen in Seed.

    Matching logic:
      - A rule matches when BOTH file and plugin match (or are omitted in the rule).
      - If the rule has no lines[], it bypasses the entire plugin for that file.
      - If the rule has lines[], it only bypasses if the given line is in the list.

    Args:
        file_path: Absolute (or relative) path to the file being checked.
        plugin: Plugin name to check bypass for (e.g., "no-bare-except").
        line: Optional line number for line-specific bypass. If None, only
              whole-file bypass rules are matched.
        bypass_rules: Pre-loaded list of bypass rule dicts from load_bypass_rules().
                      If None or empty, returns False (nothing bypassed).
        project_root: Optional project root for computing relative paths. When
                      provided, file_path is compared as a relative path against
                      the rule's "file" field.

    Returns:
        True if the violation should be suppressed, False otherwise.
    """
    if not bypass_rules:
        return False

    # Compute relative path for matching against rule "file" fields
    rel_path = file_path
    if project_root:
        try:
            rel_path = str(Path(file_path).relative_to(project_root))
        except ValueError:
            pass  # file_path not under project_root — use as-is

    for rule in bypass_rules:
        # Plugin match: rule must name this plugin (or have no plugin filter)
        rule_plugin = rule.get("plugin", "")
        if rule_plugin and rule_plugin != plugin:
            continue

        # File match: rule must match this file (or have no file filter)
        rule_file = rule.get("file", "")
        if rule_file and rule_file != rel_path:
            continue

        # Line-specific bypass
        rule_lines = rule.get("lines", [])
        if rule_lines:
            if line is not None and line in rule_lines:
                return True
            # Has line restrictions but our line doesn't match — keep looking
            continue

        # No line restriction — entire plugin/file is bypassed
        return True

    return False
