# =================== AIPass ====================
# Name: preflight.py
# Description: Non-mutating cross-OS pre-flight runners (routing/version/hooks/e2e)
# Version: 1.0.0
# Created: 2026-07-02
# Modified: 2026-07-02
# =============================================

"""Cross-OS pre-flight runners — Layer-3-lite machine checks.

Each runner probes one machine-provable slice of the cross-OS acceptance
checklist and returns a small ``PreflightResult(name, ok, detail)``. Everything
here is *non-mutating* and NEVER wakes a citizen: the drone routes exercised
(``drone systems``, ``drone @ai_mail --help``, ``drone @hooks status``) only
print/route — they do not dispatch work to a branch.

Robustness contract: every subprocess has a timeout and every runner catches
``FileNotFoundError`` / ``TimeoutExpired`` (and other ``OSError``) and turns it
into ``ok=False`` with a clear ``detail`` — a runner never crashes the caller.

These are pre-flight rows. They can NEVER claim the checklist's human green
("you watched it work on that OS"); callers must label them pre-flight.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Sequence, Tuple

from aipass.prax import logger
from aipass.aipass.apps.handlers.json import json_handler

# Directory (relative to repo root) holding the Layer-2 e2e wiring suite.
E2E_RELATIVE = Path("tests") / "e2e"

# Subprocess timeouts (seconds). Light routes are quick; e2e is heavy (it builds
# a wheel and installs it into a fresh venv) so it gets a generous budget.
_ROUTE_TIMEOUT = 20
_VERSION_TIMEOUT = 15
_HOOKSTATUS_TIMEOUT = 20
_E2E_TIMEOUT = 600

# Detail prefix marking an e2e result that could NOT run (infra), so callers can
# map it to WARN rather than FAIL. Real pytest failures do not use this prefix.
E2E_UNRUNNABLE_PREFIX = "could not run"


class PreflightResult(NamedTuple):
    """One non-mutating pre-flight probe outcome."""

    name: str
    ok: bool
    detail: str


def _run(cmd: Sequence[str], timeout: int, cwd: str | None = None) -> Tuple[int | None, str]:
    """Run ``cmd`` non-interactively; return ``(returncode, combined_output)``.

    Never raises for the expected failure modes: a missing binary yields
    ``(None, "not found: ...")`` and a timeout yields ``(None, "timed out ...")``.
    """
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError as exc:
        logger.warning("[cross_os.preflight] binary not found for %s: %s", cmd, exc)
        return None, f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired as exc:
        logger.warning("[cross_os.preflight] %s timed out after %ss: %s", cmd, timeout, exc)
        return None, f"timed out after {timeout}s"
    except OSError as exc:
        logger.warning("[cross_os.preflight] error running %s: %s", cmd, exc)
        return None, f"error running {cmd[0]}: {exc}"


def _first_line(output: str) -> str:
    """Return the first non-empty stripped line of ``output`` (or "")."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def check_routing() -> PreflightResult:
    """Verify drone routing (Phase 4): ``drone systems`` + one subprocess route.

    Both ``drone systems`` (4.1) and ``drone @ai_mail --help`` (4.2) must exit 0.
    These are non-mutating routes — ``--help`` prints usage; neither dispatches
    work to a citizen.
    """
    sys_rc, sys_out = _run(["drone", "systems"], _ROUTE_TIMEOUT)
    route_rc, route_out = _run(["drone", "@ai_mail", "--help"], _ROUTE_TIMEOUT)

    ok = sys_rc == 0 and route_rc == 0
    if ok:
        detail = "drone systems exit 0; @ai_mail route exit 0"
    else:
        problems: List[str] = []
        if sys_rc != 0:
            problems.append(f"drone systems -> {sys_rc or _first_line(sys_out)}")
        if route_rc != 0:
            problems.append(f"@ai_mail --help -> {route_rc or _first_line(route_out)}")
        detail = "; ".join(problems)
    return PreflightResult("routing", ok, detail)


def check_versions() -> PreflightResult:
    """Verify ``drone --version`` and ``aipass --version`` exit 0 (Phase 1.3).

    Captures the version strings into the detail.
    """
    drone_rc, drone_out = _run(["drone", "--version"], _VERSION_TIMEOUT)
    aipass_rc, aipass_out = _run(["aipass", "--version"], _VERSION_TIMEOUT)

    def _ver(label: str, rc: int | None, out: str) -> str:
        if rc == 0:
            return _first_line(out)
        return f"{label} --version failed ({rc}: {_first_line(out)})"

    ok = drone_rc == 0 and aipass_rc == 0
    detail = f"{_ver('drone', drone_rc, drone_out)}; {_ver('aipass', aipass_rc, aipass_out)}"
    return PreflightResult("versions", ok, detail)


def check_hookstatus() -> PreflightResult:
    """Verify the @hooks per-project config renders (Phase 6.3).

    Note: the checklist labels this ``drone @hooks hookstatus``, but that command
    name does not route on the current drone build (it returns "Unknown command"
    — gap #9 in the wild). The real, non-mutating subcommand that renders the
    per-project hook config is ``drone @hooks status``, which is what Phase 6.3
    actually verifies, so that is what we probe.
    """
    rc, out = _run(["drone", "@hooks", "status"], _HOOKSTATUS_TIMEOUT)
    ok = rc == 0
    detail = _first_line(out) if ok else f"drone @hooks status exit {rc}: {_first_line(out)}"
    return PreflightResult("hookstatus", ok, detail)


def find_e2e_dir(start: Path | None = None) -> Path | None:
    """Search upward from ``start`` (or this file) for ``tests/e2e``.

    Portable — walks ancestors rather than hardcoding a path (mirrors the
    gap_registry ``find_gap_doc`` pattern). Returns ``None`` if not found.
    """
    base = (start or Path(__file__)).resolve()
    for parent in [base, *base.parents]:
        candidate = parent / E2E_RELATIVE
        if candidate.is_dir():
            return candidate
    return None


def _resolve_pytest(repo_root: Path) -> Tuple[List[str], str] | None:
    """Resolve a pytest invocation for the current box.

    Prefers ``<repo>/.venv/<bin>/pytest`` (system ``python`` may be absent);
    falls back to ``sys.executable -m pytest``. Returns ``(argv_prefix, source)``
    or ``None`` if neither can be resolved.
    """
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    exe = "pytest.exe" if os.name == "nt" else "pytest"
    venv_pytest = repo_root / ".venv" / bin_dir / exe
    if venv_pytest.is_file():
        return [str(venv_pytest)], "venv pytest"
    if sys.executable:
        return [sys.executable, "-m", "pytest"], "sys.executable -m pytest"
    return None


def run_e2e(start: Path | None = None) -> PreflightResult:
    """Run the Layer-2 e2e wiring suite (``pytest tests/e2e -q``). HEAVY.

    Only call this when explicitly opted into (``--e2e``): the suite builds the
    aipass wheel and installs it into a fresh venv. ``ok=True`` only when every
    test passes (pytest exit 0). Un-runnable cases (dir missing, no pytest,
    timeout, crash) return ``ok=False`` with a ``could not run`` detail so the
    caller can render them as WARN rather than a hard FAIL.
    """
    e2e_dir = find_e2e_dir(start)
    if e2e_dir is None:
        return PreflightResult("e2e", False, f"{E2E_UNRUNNABLE_PREFIX}: e2e dir not found")

    repo_root = e2e_dir.parent.parent
    resolved = _resolve_pytest(repo_root)
    if resolved is None:
        detail = f"{E2E_UNRUNNABLE_PREFIX}: pytest unavailable (no venv pytest, no interpreter)"
        return _log_e2e(PreflightResult("e2e", False, detail))

    argv_prefix, source = resolved
    logger.info("[cross_os.preflight] running e2e suite via %s (cwd=%s)", source, repo_root)
    rc, out = _run([*argv_prefix, str(e2e_dir), "-q"], _E2E_TIMEOUT, cwd=str(repo_root))

    if rc is None:
        # Timeout / missing binary / OSError — infra, not a real test failure.
        return _log_e2e(PreflightResult("e2e", False, f"{E2E_UNRUNNABLE_PREFIX}: {out}"))

    summary = _e2e_summary(out)
    if rc == 0:
        return _log_e2e(PreflightResult("e2e", True, summary))
    # Non-zero: could be real failures OR pytest itself being absent under
    # `python -m pytest`. Distinguish so the caller can WARN vs FAIL.
    if "no module named pytest" in out.lower():
        return _log_e2e(PreflightResult("e2e", False, f"{E2E_UNRUNNABLE_PREFIX}: pytest not importable"))
    return _log_e2e(PreflightResult("e2e", False, summary))


def _log_e2e(result: PreflightResult) -> PreflightResult:
    """Record the e2e pre-flight outcome via json_handler, then return it."""
    json_handler.log_operation("cross_os_e2e_preflight", {"ok": result.ok, "detail": result.detail})
    return result


def _e2e_summary(output: str) -> str:
    """Extract pytest's terminal summary line (e.g. '14 passed', '2 failed...')."""
    for line in reversed(output.splitlines()):
        stripped = line.strip().strip("=").strip()
        if any(tok in stripped for tok in ("passed", "failed", "error", "no tests ran")):
            return stripped
    return _first_line(output) or "no pytest summary parsed"
