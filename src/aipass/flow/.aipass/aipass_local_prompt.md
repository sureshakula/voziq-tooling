# Flow -- Plan Lifecycle Management

Flow is AIPass's unified plan lifecycle system. It creates, tracks, closes, and archives numbered work plans across multiple plan types (FPLAN, DPLAN) via a data-driven plugin architecture.

## Commands

```bash
drone @flow create . "Subject"              # FPLAN (default)
drone @flow create . "Subject" master       # FPLAN master template
drone @flow create . "Design topic" dplan   # DPLAN
drone @flow close FPLAN-0042                # Close specific plan
drone @flow close --all                     # Close all open plans
drone @flow list                            # List open plans (all types)
drone @flow list all                        # List all plans
drone @flow restore FPLAN-0042              # Reopen a closed plan
```

## Architecture

- `apps/flow.py` -- Entry point. Auto-discovers modules in `apps/modules/` via `handle_command()` convention.
- `apps/modules/` -- Thin orchestrators. No business logic. Route to handlers and display results.
- `apps/handlers/` -- Implementation. Grouped by domain: `plan/`, `registry/`, `template/`, `dashboard/`, `mbank/`, `summary/`.
- `templates/` -- Plan type directories. Each subdirectory contains Markdown templates. Registered via `drone @flow register`.
- `flow_json/` -- Registries: per-type plan registries + `template_registry.json` (plan type definitions).

## Plan Type System

Plan types are filesystem-driven. Drop a directory with `.md` templates into `templates/`, register it, done:
```bash
drone @flow register testing TPLAN          # Register new type
drone @flow unregister testing              # Remove type
drone @flow templates                       # List registered types
drone @flow scan                            # Find unregistered directories
```

Discovered at runtime by `plan_type_loader.py` + `registry_ops.py`. No per-directory JSON config needed.

| Type | Prefix | Registry File | Templates |
|------|--------|---------------|-----------|
| flow_plans | FPLAN | fplan_registry.json | default, master |
| dev_plans | DPLAN | dplan_registry.json | default |

## Critical Files

- `apps/flow.py` -- CLI entry point, module discovery, command routing
- `apps/modules/create_plan.py` -- Plan creation orchestrator
- `apps/modules/close_plan.py` -- Plan closure orchestrator (async post-processing, archival)
- `apps/modules/list_plans.py` -- Multi-registry plan listing
- `apps/handlers/plan/list_ops.py` -- Merges plans from all registries for display
- `apps/handlers/plan/display.py` -- All formatting functions (prefix-aware)
- `apps/handlers/plan/close_ops.py` -- Close implementation (file ops, registry update, vector intake)
- `apps/handlers/template/plan_type_loader.py` -- Plugin discovery and config resolution
- `apps/handlers/registry/load_registry.py` -- Registry loader (supports per-type registry files)

## Integration Points

- **aipass.cli** -- Rich console output (`console`, `header`, `success`, `error`, `warning`)
- **aipass.prax** -- System logger
- **aipass.memory** -- Vector intake pipeline on plan close
- **aipass.trigger** -- Startup events and branch dashboard updates

## Conventions

- Modules return `True` from `handle_command()` when the command was recognized (even on failure), `False` only for "not my command".
- Plan IDs follow `{PREFIX}-{NNNN}_topic_slug_YYYY-MM-DD.md`.
- All file I/O uses `pathlib.Path` and `encoding='utf-8'`.
- Handlers are stateless functions; modules inject dependencies.
