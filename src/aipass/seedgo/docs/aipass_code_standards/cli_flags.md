# CLI Flags Standard
**Status:** Active — Approved for Full Rollout
**Date:** 2026-02-21
**Proposed by:** SEED (Session 68, dispatch from DEV_CENTRAL)

## What This Covers

Universal CLI flags that every branch entry point should support. This standard defines a consistent set of flags, their behavior, and implementation patterns.

This is a companion to the existing CLI standard (`cli.md`), which covers output formatting, command naming, and argument design. This standard specifically addresses **flag conventions** across all branches.

---

## The Problem

Each branch independently decides which flags to support. Result:
- `--verbose` exists in 3 branches (PRAX, CORTEX, BACKUP_SYSTEM), absent from 13
- `--dry-run` exists in 3 branches (CORTEX, BACKUP_SYSTEM, MEMORY_BANK), absent from 13
- `--test` exists in 1 branch (BACKUP_SYSTEM only)
- `--version` exists in 0 branches
- `--help` is universal (the only consistent flag)

When Patrick or an agent runs `drone @flow --verbose` or `drone @trigger --version`, nothing happens. Flags should be predictable across the system.

---

## The Standard

### Tier 1: Required (every branch entry point)

| Flag | Short | Behavior |
|------|-------|----------|
| `--help` | `-h`, `help` | Show Rich-formatted help with Commands line for drone discovery |
| `--version` | `-V` | Print branch name and version from META DATA HEADER |

### Tier 2: Recommended (when applicable)

| Flag | Short | When Required | Behavior |
|------|-------|---------------|----------|
| `--verbose` | `-v` | Branches with multi-step operations | Extra diagnostic output via logger |
| `--dry-run` | | Branches with mutating/destructive commands | Preview what would happen, execute nothing |
| `--test` | | Branches with testable components | Run quick self-check, report pass/fail |

**"When applicable" means:** If your branch has commands that modify state, `--dry-run` is recommended. If your branch has multi-step operations where intermediate output helps debugging, `--verbose` is recommended. If your branch has components that can be health-checked, `--test` is recommended.

---

## Flag Specifications

### `--help` / `-h` / `help` (REQUIRED)

Already universal. No changes needed. Documented in `cli.md`.

Must include `Commands:` line for drone discovery. Must use Rich `console.print()` formatting.

### `--version` / `-V` (REQUIRED)

Print the branch name and version, then exit.

**Output format:**
```
BRANCH_NAME v1.2.3
```

**Where the version comes from:** Every branch entry point has a META DATA HEADER with a `Version:` field. Read it from there.

**Implementation:**
```python
def show_version():
    """Print version from META DATA HEADER."""
    console.print("SEED v3.0.0")

# In main():
if args[0] in ['--version', '-V']:
    show_version()
    return
```

**Why `-V` (uppercase)?** `-v` is already taken by `--verbose`. This follows GNU convention (`python3 -V`, `git --version`).

**Why this matters:** Version info helps debugging dispatch issues, identifying stale agents, and confirming deployments. Today, the only way to check a branch's version is to read its source file.

### `--verbose` / `-v` (RECOMMENDED)

Enable extra diagnostic output for the current operation.

**What verbose output includes:**
- Module discovery details (which modules found, which matched)
- File paths being processed
- Timing information for slow operations
- Configuration values being used

**What verbose output does NOT include:**
- Debug-level internals (use logger.debug for that)
- Raw data dumps
- Stack traces (those belong in error handling)

**Implementation pattern:**
```python
# In entry point - set a global or pass through
verbose = '--verbose' in args or '-v' in args
if verbose:
    remaining_args = [a for a in args if a not in ['--verbose', '-v']]

# Pass to modules
route_command(command, remaining_args, modules, verbose=verbose)

# In modules - conditional output
if verbose:
    console.print(f"[dim]  Processing {len(files)} files...[/dim]")
```

**Convention:** Verbose output uses `[dim]` Rich formatting to visually distinguish it from primary output.

### `--dry-run` (RECOMMENDED for mutating branches)

Preview what would happen without executing.

**Branches where this applies:**
- FLOW (creating/deleting plans)
- AI_MAIL (sending emails)
- CORTEX (creating/deleting branches)
- BACKUP_SYSTEM (running backups)
- MEMORY_BANK (rolling over memories)
- TRIGGER (firing events)

**Branches where this does NOT apply:**
- SEED (read-only checks)
- CLI (display services)
- DEVPULSE (read-only dev notes display)

**Implementation pattern:**
```python
dry_run = '--dry-run' in args
if dry_run:
    remaining_args = [a for a in args if a != '--dry-run']

# In handler:
if dry_run:
    console.print("[yellow]DRY RUN[/yellow] — no changes will be made")
    console.print(f"  Would create: {target_path}")
    console.print(f"  Would update: {registry_path}")
    return
# ... actual execution ...
```

**Convention:** Dry-run output prefixes with `[yellow]DRY RUN[/yellow]`.

### `--test` (RECOMMENDED for testable branches)

Run a quick self-check to verify the branch is operational.

**What `--test` does:**
1. Verify the branch can import its dependencies
2. Verify key files/directories exist
3. Run a minimal operation (e.g., discover modules, parse a sample)
4. Report pass/fail with timing

**What `--test` does NOT do:**
- Run the full pytest suite (that's `pytest`)
- Modify any state
- Take more than 5 seconds

**Output format:**
```
BRANCH_NAME self-test
  ✅ Dependencies imported
  ✅ Module discovery (found 8 modules)
  ✅ JSON handler accessible
  ✅ Config files present
  4/4 passed (0.3s)
```

**Implementation pattern:**
```python
def run_self_test():
    """Quick operational self-check."""
    console.print(f"[bold cyan]{BRANCH_NAME} self-test[/bold cyan]")
    passed = 0
    total = 0

    # Test 1: Dependencies
    total += 1
    try:
        from cli.apps.modules import console  # noqa: F811
        from prax.apps.modules.logger import system_logger  # noqa: F811
        console.print("  ✅ Dependencies imported")
        passed += 1
    except ImportError as e:
        console.print(f"  ❌ Dependencies failed: {e}")

    # Test 2: Module discovery
    total += 1
    modules = discover_modules()
    if modules:
        console.print(f"  ✅ Module discovery (found {len(modules)} modules)")
        passed += 1
    else:
        console.print("  ❌ No modules discovered")

    # Summary
    console.print(f"  {passed}/{total} passed")
    return passed == total
```

---

## Flag Handling Order

Flags must be checked **before** command routing, in this order:

```python
def main():
    args = sys.argv[1:]

    # 1. No args → introspection
    if len(args) == 0:
        show_introspection()
        return

    # 2. Universal flags (checked before command routing)
    if args[0] in ['--help', '-h', 'help']:
        show_help()
        return

    if args[0] in ['--version', '-V']:
        show_version()
        return

    if args[0] == '--test':
        success = run_self_test()
        sys.exit(0 if success else 1)

    # 3. Extract optional flags from args
    verbose = '--verbose' in args or '-v' in args
    dry_run = '--dry-run' in args
    remaining_args = [a for a in args if a not in ['--verbose', '-v', '--dry-run']]

    # 4. Command routing
    command = remaining_args[0]
    command_args = remaining_args[1:]
    route_command(command, command_args, modules, verbose=verbose, dry_run=dry_run)
```

**Key rule:** Universal flags (`--help`, `--version`, `--test`) are handled as top-level actions — they execute and exit. Behavioral flags (`--verbose`, `--dry-run`) modify how commands execute and are stripped before routing.

---

## Drone's Role

Drone should NOT intercept or inject universal flags. Reasons:

1. **Transparency** — branches own their own behavior
2. **Simplicity** — drone is a router, not a preprocessor
3. **Consistency** — `python3 apps/seed.py --version` and `drone @seed --version` behave identically

Drone already passes `--help` through to branches correctly. The same pattern applies to all universal flags.

**One exception to consider (future):** Drone could add a `drone @branch --ping` command that checks if the branch is reachable and responds. This would be a drone-level feature, not a branch flag.

---

## What This Does NOT Standardize

- **Command-specific flags** (e.g., `--template`, `--note`, `--force`) — these are domain-specific and belong to individual branches
- **Subcommand flags** (e.g., `drone @flow create --template master`) — these are handled by modules, not the entry point
- **Short flags beyond -h, -v, -V** — branches can define their own short flags for command-specific options

---

## Migration Path

This standard does not require immediate system-wide changes. Recommended rollout:

**Phase 1: Add `--version` to all branches**
- Lowest effort, highest value
- Just read the META DATA HEADER version string
- Can be done branch-by-branch

**Phase 2: Add `--test` to core branches**
- SEED, DRONE, FLOW, AI_MAIL, PRAX, CORTEX first
- Each branch defines what "self-test" means for them
- Enables automated health checking

**Phase 3: Standardize `--verbose` and `--dry-run`**
- Branches that already have these: verify they follow the convention
- Branches that need them: add as part of normal development

**No big-bang migration.** New branches get these flags from the Cortex template. Existing branches adopt them naturally.

---

## Survey Results (2026-02-21)

Current flag support across 16 branch entry points:

| Branch | --help | --version | --verbose | --dry-run | --test | Parsing |
|--------|--------|-----------|-----------|-----------|--------|---------|
| SEED | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| DRONE | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| FLOW | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| AI_MAIL | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| PRAX | ✅ | ❌ | ✅ | ❌ | ❌ | argparse |
| CORTEX | ✅ | ❌ | ✅ | ✅ | ❌ | argparse |
| BACKUP_SYSTEM | ✅ | ❌ | ✅ | ✅ | ✅ | argparse |
| CLI | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| TRIGGER | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| MEMORY_BANK | ✅ | ❌ | ❌ | ✅ | ❌ | sys.argv |
| THE_COMMONS | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| DEVPULSE | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| SCHEDULER | ✅ | ❌ | ❌ | ❌ | ❌ | none |
| NEXUS | ✅ | ❌ | ❌ | ❌ | ❌ | argparse |
| SPEAKEASY | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |
| API | ✅ | ❌ | ❌ | ❌ | ❌ | sys.argv |

**Summary:** --help is 16/16. Everything else is 0-3/16. Significant opportunity for standardization.

---

## Notes

This standard is deliberately lightweight. It defines what flags should exist and what they should do, not how to build a flag parsing framework. The existing sys.argv and argparse patterns in `cli.md` handle the implementation side.

The goal is predictability: when you type `drone @anything --version`, you get a version. When you type `drone @anything --test`, you get a health check. No surprises.
