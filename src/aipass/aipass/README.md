# AIPASS

Concierge and librarian for AIPass. Greets new users, walks them through setup, answers how-things-work questions, hands off to their chosen CLI.

## Invoke

```
drone @aipass <command>
```

## Architecture

```
aipass/
├── apps/
│   ├── aipass.py                          # Entry point — subcommand dispatch
│   ├── modules/
│   │   ├── doctor.py                      # System health aggregation + cross-OS pre-flight (--cross-os)
│   │   ├── doctor_fix.py                  # Remediation report (--fix, --json)
│   │   ├── doctor_wire.py                 # Auto-wire provider settings + stale-deny re-export
│   │   ├── handoff.py                     # CLI handoff (placeholder)
│   │   ├── help_chat.py                   # README-backed Q&A (reads via readme_map handler)
│   │   ├── init_flow.py                   # 10-stage guided setup
│   │   ├── install.py                     # aipass install — one-command bootstrap (clone + setup + init)
│   │   └── profile.py                     # User profile read/write
│   ├── handlers/
│   │   ├── cross_os/                      # Cross-OS pre-flight: gap_registry, preflight, run_record
│   │   ├── handoff_platform/              # Platform-specific handoff detection
│   │   ├── init/                          # bootstrap.py, scaffold_content.py
│   │   ├── json/                          # JSON read/write utilities
│   │   ├── ping_sweep/                    # Branch reachability verification
│   │   ├── provider_reconcile.py           # Stale deny-rule detection + fix
│   │   ├── readme_map/                    # Live file reads + branch routing
│   │   ├── structure_scan/                # Agent placement + pollution detection
│   │   ├── system_detect/                 # OS, shell, Python, RAM, CPU
│   │   └── ui/                            # Progress bars, menus, banners
│   └── plugins/
├── tests/                                 # 609 passing
├── requirements.project.txt               # Project-specific Python dependencies
├── .trinity/                              # Identity + session history + observations
└── README.md
```

## Commands

| Command | Description |
|---------|-------------|
| `aipass` | Help banner |
| `aipass help [Q]` | README-backed Q&A with branch routing |
| `aipass doctor` | System health — structure, registry, hooks, pytest |
| `aipass doctor --fix` | Remediation report with `drone @spawn repair` commands |
| `aipass doctor --json` | JSON output for structure scan results |
| `aipass doctor --cross-os` | Cross-OS pre-flight (Layer-3-lite, machine) — OS-gap cross-ref + routing/versions/hookstatus |
| `aipass doctor --cross-os --e2e` | ...also runs the real Layer-2 e2e wiring suite (heavy, opt-in) |
| `aipass doctor --cross-os --record [PATH]` | Write a machine-filled Run Record for the human Layer-3 acceptance pass |
| `aipass init` | 10-stage guided setup (resumable) |
| `aipass install` | One-command bootstrap — clone + setup.sh + hooks, then hand off to init (`--no-init`/`--with-init`/`--path`/`--here`) |
| `aipass profile` | Show/edit user profile |
| `aipass --version` | Version |

## Integration Points

### Depends On

- `@drone` — routing, command dispatch
- `@seedgo` — standards audit
- `@spawn` — first agent creation + structural repair
- `@flow` — plan lifecycle (open/close)
- `@ai_mail` — test emails
- `@prax` — health signals, logging
- `pytest` — test execution

### Provides To

Humans only. Nothing in AIPass depends on this branch.

## Tests

609 passing — `pytest src/aipass/aipass/tests/`

## Known Issues

- `aipass.py` line 23: `from aipass.prax import logger` fails outside package context (ModuleNotFoundError). Works via drone routing only.

## Last Updated

Last Updated: 2026-07-05
