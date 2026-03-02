"""
Seed Go Plugin Discovery

Discovers plugins from three sources in priority order:
  1. Built-in plugins shipped with seedgo (seedgo/plugins/)
  2. Installed package plugins via pip entry points (group="seedgo.plugins")
  3. Local project plugins in .seedgo/plugins/

Later sources override earlier ones on name collision — local plugins always win.
This allows projects to override built-in or installed plugins with their own versions.

Duck typing contract: a .py file is a plugin if it has:
  - PLUGIN_NAME (str): unique kebab-case identifier
  - check (callable): the check function
"""

import importlib
import importlib.metadata
import importlib.util
from pathlib import Path

def discover_plugins(project_root: str | None = None) -> list[dict]:
    """Discover all available plugins from all sources.

    Searches built-ins, installed packages, and local project plugins.
    Deduplicates by plugin name with last-wins semantics (local overrides
    installed overrides builtin).

    Args:
        project_root: Optional path to project root. When provided, also
                      searches .seedgo/plugins/ for local project plugins.

    Returns:
        List of plugin descriptor dicts, each with keys:
          - "name" (str): plugin's PLUGIN_NAME value
          - "module" (module): the loaded module object
          - "source" (str): "builtin", "package:<dist-name>", or "local"
          - "path" (str): absolute path to the plugin file
    """
    plugins: list[dict] = []

    # Source 1: Built-in plugins (ships empty in production)
    plugins.extend(_discover_builtin())

    # Source 2: Installed package plugins via entry points
    plugins.extend(_discover_entry_points())

    # Source 3: Local project plugins (.seedgo/plugins/)
    if project_root:
        plugins.extend(_discover_local(project_root))

    # Deduplicate by name — last wins (local > installed > builtin)
    seen: dict[str, dict] = {}
    for plugin in plugins:
        seen[plugin["name"]] = plugin

    return list(seen.values())


def _discover_builtin() -> list[dict]:
    """Discover plugins shipped inside the seedgo package.

    Scans the seedgo/plugins/ directory. In production this directory ships
    empty — built-in examples live in examples/plugins/ (not installed).

    Returns:
        List of plugin descriptor dicts with source="builtin".
    """
    builtin_dir = Path(__file__).parent / "plugins"
    return _scan_directory(builtin_dir, source="builtin")


def _discover_entry_points() -> list[dict]:
    """Discover plugins installed as pip packages.

    Third-party plugin packages register under the "seedgo.plugins" entry
    point group in their pyproject.toml:

        [project.entry-points."seedgo.plugins"]
        no_bare_except = "seedgo_python_basics.no_bare_except"

    Returns:
        List of plugin descriptor dicts with source="package:<dist-name>".
    """
    plugins: list[dict] = []

    try:
        eps = importlib.metadata.entry_points(group="seedgo.plugins")
    except Exception:
        return plugins

    for ep in eps:
        try:
            module = ep.load()
            if hasattr(module, "PLUGIN_NAME") and callable(getattr(module, "check", None)):
                dist_name = ep.dist.name if ep.dist else "unknown"
                file_path = str(Path(module.__file__)) if getattr(module, "__file__", None) else ""
                plugins.append({
                    "name": module.PLUGIN_NAME,
                    "module": module,
                    "source": f"package:{dist_name}",
                    "path": file_path,
                })
        except Exception:
            pass  # Skip broken entry points silently

    return plugins


def _discover_local(project_root: str) -> list[dict]:
    """Discover plugins in the project's .seedgo/plugins/ directory.

    Local plugins override built-in and installed plugins of the same name,
    giving projects full control over their standards checking.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        List of plugin descriptor dicts with source="local".
    """
    local_dir = Path(project_root) / ".seedgo" / "plugins"
    return _scan_directory(local_dir, source="local")


def _scan_directory(directory: Path, source: str) -> list[dict]:
    """Scan a directory for plugin files using duck typing.

    A file is treated as a plugin if it:
      - Has a .py extension
      - Does not start with underscore (skips __init__.py, _helpers.py, etc.)
      - Defines PLUGIN_NAME (str attribute)
      - Defines check (callable)

    Plugins that fail to import are silently skipped to avoid one broken
    plugin preventing all other plugins from loading.

    Args:
        directory: Directory to scan. Returns empty list if it does not exist.
        source: Source label to embed in descriptors ("builtin", "local", etc.).

    Returns:
        List of plugin descriptor dicts sorted by plugin name for determinism.
    """
    plugins: list[dict] = []

    if not directory.exists():
        return plugins

    if not directory.is_dir():
        return plugins

    for file_path in sorted(directory.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]

            # Duck typing: needs PLUGIN_NAME (str) + check (callable)
            plugin_name = getattr(module, "PLUGIN_NAME", None)
            check_fn = getattr(module, "check", None)

            if isinstance(plugin_name, str) and callable(check_fn):
                plugins.append({
                    "name": plugin_name,
                    "module": module,
                    "source": source,
                    "path": str(file_path),
                })
        except Exception:
            pass  # Skip broken plugins silently

    return plugins
