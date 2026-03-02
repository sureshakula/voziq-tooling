"""
Seed Go Configuration System

Handles loading, merging, and resolving .seedgo/config.json project configs.
Provides defaults for all settings so seedgo works with zero configuration.

Config resolution order (later sources win):
  1. DEFAULT_CONFIG (hardcoded here)
  2. Profile plugins (named preset, if configured)
  3. Project .seedgo/config.json
  4. Per-directory overrides (overrides[] entries matched by path prefix)
  5. CLI flags (applied by CLI layer, not here)
"""

import json
from pathlib import Path
from .exceptions import ConfigError


DEFAULT_CONFIG: dict = {
    "version": "1.0.0",
    "profile": None,
    "plugins": {
        "enabled": [],
        "disabled": [],
        "config": {},
    },
    "scoring": {
        "threshold": 75,
        "error_weight": 1.0,
        "warning_weight": 0.5,
        "info_weight": 0.0,
    },
    "paths": {
        "include": ["."],
        "exclude": [],
    },
    "overrides": [],
}


def load_config(project_root: str) -> dict:
    """Load and resolve config from .seedgo/config.json.

    Merges user config over defaults. If a profile is specified, the profile
    is merged between defaults and user config so user config always wins.

    Args:
        project_root: Path to the project root (directory containing .seedgo/).

    Returns:
        Fully resolved config dict ready for use.

    Raises:
        ConfigError: If .seedgo/config.json exists but cannot be parsed.
    """
    import copy

    config_path = Path(project_root) / ".seedgo" / "config.json"

    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Cannot read {config_path}: {e}") from e

    # Start from defaults
    resolved = copy.deepcopy(DEFAULT_CONFIG)
    _deep_merge(resolved, user_config)

    # Profile: merge between defaults and user config so user always wins
    if resolved.get("profile"):
        try:
            profile = _load_profile(resolved["profile"], project_root)
            # Re-start: defaults -> profile -> user config
            resolved = copy.deepcopy(DEFAULT_CONFIG)
            _deep_merge(resolved, profile)
            _deep_merge(resolved, user_config)
        except ConfigError:
            # Profile not found — continue without it
            pass

    return resolved


def resolve_file_config(config: dict, file_path: str, project_root: str) -> dict:
    """Apply per-directory overrides for a specific file.

    Matches the file's relative path against each override's paths list.
    All matching overrides are applied in order (last match wins for conflicts).

    Args:
        config: Fully resolved project config from load_config().
        file_path: Absolute path to the file being checked.
        project_root: Project root for computing relative paths.

    Returns:
        Config dict with applicable overrides merged in.
    """
    import copy

    try:
        rel_path = str(Path(file_path).relative_to(project_root))
    except ValueError:
        rel_path = file_path

    resolved = copy.deepcopy(config)

    for override in config.get("overrides", []):
        paths = override.get("paths", [])
        if any(rel_path.startswith(p) for p in paths):
            _deep_merge(resolved, override)

    return resolved


def find_project_root(start_path: str) -> str | None:
    """Walk up the directory tree looking for a .seedgo/ directory.

    Args:
        start_path: Starting file or directory path to search from.

    Returns:
        Absolute path string of the project root directory, or None if not found.
    """
    current = Path(start_path).resolve()

    # If start_path is a file, begin from its parent directory
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        if (directory / ".seedgo").is_dir():
            return str(directory)

    return None


def create_default_config(project_root: str, profile: str | None = None) -> str:
    """Create .seedgo/config.json with defaults (for `seedgo init`).

    Creates the .seedgo/ directory and plugins/ subdirectory if they do not exist.

    Args:
        project_root: Directory where .seedgo/ will be created.
        profile: Optional profile name to embed in the new config.

    Returns:
        Path to the created config file as a string.

    Raises:
        ConfigError: If the config file already exists or cannot be written.
    """
    import copy

    seedgo_dir = Path(project_root) / ".seedgo"
    plugins_dir = seedgo_dir / "plugins"
    config_path = seedgo_dir / "config.json"

    if config_path.exists():
        raise ConfigError(f"Config already exists at {config_path}. Remove it first or edit it directly.")

    try:
        seedgo_dir.mkdir(parents=True, exist_ok=True)
        plugins_dir.mkdir(exist_ok=True)
    except OSError as e:
        raise ConfigError(f"Cannot create .seedgo/ directory: {e}") from e

    config = copy.deepcopy(DEFAULT_CONFIG)
    if profile:
        config["profile"] = profile

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
    except OSError as e:
        raise ConfigError(f"Cannot write config to {config_path}: {e}") from e

    return str(config_path)


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place. Dicts are merged recursively; other types replace.

    Args:
        base: The dict to merge into (modified in-place).
        override: The dict whose values take priority.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _load_profile(profile_name: str, project_root: str | None = None) -> dict:
    """Load a named profile from the profiles search path.

    Searches in order:
      1. Local project .seedgo/profiles/<name>.json
      2. Built-in seedgo/profiles/<name>.json (not yet shipped)

    Args:
        profile_name: Name of the profile (e.g., "python-strict").
        project_root: Optional project root for local profile lookup.

    Returns:
        Profile config dict (subset of full config).

    Raises:
        ConfigError: If the profile cannot be found or parsed.
    """
    search_paths: list[Path] = []

    if project_root:
        search_paths.append(Path(project_root) / ".seedgo" / "profiles" / f"{profile_name}.json")

    # Built-in profiles directory (alongside this file)
    builtin_profiles = Path(__file__).parent / "profiles"
    search_paths.append(builtin_profiles / f"{profile_name}.json")

    for profile_path in search_paths:
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"Invalid JSON in profile {profile_path}: {e}") from e

    raise ConfigError(f"Profile '{profile_name}' not found. Checked: {[str(p) for p in search_paths]}")
