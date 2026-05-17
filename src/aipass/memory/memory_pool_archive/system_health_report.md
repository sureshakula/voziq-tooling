# AIPass System Health Report
Generated: 2026-03-19 22:54

---

## 1. Dead Code (14 unused files)


Dead Code Scanner
Scanning 15 branches

@ai_mail (3 modules, 31 handlers)
  x handlers/monitoring/errors.py -- 0 references
  > 33/34 files referenced

@api (4 modules, 14 handlers)
  x handlers/openrouter/provision.py -- 0 references
  > 17/18 files referenced

@backup (4 modules, 24 handlers)
  x handlers/diff/vscode_integration.py -- 0 references
  > 27/28 files referenced

@cli (3 modules, 2 handlers)
  > All 5 files referenced

@commons (22 modules, 35 handlers)
  > All 57 files referenced

@daemon (6 modules, 8 handlers)
  > All 14 files referenced

@devpulse -- no apps/ directory
@drone (9 modules, 16 handlers)
  > All 25 files referenced

@flow (8 modules, 35 handlers)
  x handlers/plan/file_ops.py -- 0 references
  x handlers/plan/update_registry.py -- 0 references
  > 41/43 files referenced

@memory (5 modules, 29 handlers)
  x handlers/learnings/manager.py -- 0 references
  x handlers/schema/normalize.py -- 0 references
  x handlers/search/vector_search.py -- 0 references
  > 31/34 files referenced

@prax (6 modules, 36 handlers)
  > All 42 files referenced

@seedgo (5 modules, 66 handlers)
  x handlers/config/aipass_bypass.py -- 0 references
  x handlers/config/aipass_ignore.py -- 0 references
  x handlers/diagnostics/python_diognostics.py -- 0 references
  x handlers/diagnostics/typscript_diognostics.py -- 0 references
  x handlers/file/file_handler.py -- 0 references
  x handlers/mock_standard_1/bypass_config/bypass.config.py -- 0 references
  > 65/71 files referenced

@skills (5 modules, 8 handlers)
  > All 13 files referenced

@spawn (6 modules, 15 handlers)
  > All 21 files referenced

@trigger (5 modules, 17 handlers)
  > All 22 files referenced

TOTAL: 14 unused across 14 branches

---

## 2. Local Prompts (5 stubs need enrichment)


Local Prompt Status
==================================================

RICH (50+ lines, 4+ sections):
  v daemon            56 lines   4 sections
  v devpulse          79 lines   8 sections
  v flow              67 lines   6 sections
  v seedgo            56 lines   4 sections
  v skills            58 lines   5 sections
  v trigger           53 lines   7 sections

BASIC (15-49 lines):
  ~ api               15 lines   2 sections
  ~ commons           48 lines   6 sections
  ~ memory            37 lines   5 sections
  ~ spawn             20 lines   4 sections

STUB (<15 lines):
  x ai_mail           14 lines   1 section 
  x backup            14 lines   1 section 
  x cli               14 lines   1 section 
  x drone             14 lines   1 section 
  x prax              14 lines   1 section 

==================================================
SUMMARY: 6 rich, 4 basic, 5 stub

==================================================
Section Breakdown
==================================================

@ai_mail (14 lines, STUB)
  v Status
    470 bytes

@api (15 lines, BASIC)
  v Identity
  v Key Breadcrumbs
    1192 bytes

@backup (14 lines, STUB)
  v Status
    499 bytes

@cli (14 lines, STUB)
  v Status
    499 bytes

@commons (48 lines, BASIC)
  v Commands
  v Architecture
  v Integration Points
  v Critical Files
  v Role
  v Key Details
    2328 bytes

@daemon (56 lines, RICH)
  v Commands
  v Memory & Tracking
  v Apps Layout
  v Known Issues
    2788 bytes

@devpulse (79 lines, RICH)
  v Identity
  v How You Work
  v Dispatch Table
  v Commands
  v Branches
  v Working Habits
  v Autonomous Monitoring
  v Memory & Tracking
  v Has dispatch table (@branch refs)
    4710 bytes

@drone (14 lines, STUB)
  v Status
    503 bytes

@flow (67 lines, RICH)
  v Commands
  v Architecture
  v Integration Points
  v Conventions
  v Critical Files
  v Plan Type System
    3461 bytes

@memory (37 lines, BASIC)
  v Identity
  v Commands
  v Architecture
  v Memory & Tracking
  v Known Issues
    1591 bytes

@prax (14 lines, STUB)
  v Status
    501 bytes

@seedgo (56 lines, RICH)
  v Commands
  v Apps Layout (extra layer vs standard branch)
  v How I Work — Standards Reasoning
  v Quick Reference
    3166 bytes

@skills (58 lines, RICH)
  v Commands
  v Memory & Tracking
  v Apps Layout
  v Search Paths (first match wins)
  v Three Skill Tiers
    2706 bytes

@spawn (20 lines, BASIC)
  v Commands
  v Architecture
  v Role
  v Principles
    745 bytes

@trigger (53 lines, RICH)
  v Dispatch Table
  v Commands
  v Architecture
  v Integration Points
  v Critical Files
  v Role
  v Rules
    2610 bytes


---

## 3. Commands (173 discovered)


@ai_mail (14 commands)
  - close
  - contacts
  - dispatch
  - email
  - inbox
  - ping
  - read
  - registry
  - reply
  - send
  - sent
  - status
  - thresholds
  - view

@api (12 commands)
  - call
  - cleanup
  - google
  - init
  - models
  - reauth
  - session
  - stats
  - status
  - test
  - track
  - validate

@backup (1 command)
  - reauth

@cli (5 commands)
  - aipass
  - demo
  - display
  - show
  - templates

@commons (51 commands)
  - activity
  - artifacts
  - capsule
  - capsules
  - catchup
  - collab
  - comment
  - craft
  - database
  - decorate
  - delete
  - digest
  - drop
  - enter
  - event
  - explore
  - feed
  - find
  - gift
  - inspect
  - leaderboard
  - leaderboards
  - log
  - look
  - mint
  - mute
  - open
  - pin
  - pinned
  - post
  - preferences
  - profile
  - prompt
  - react
  - reactions
  - room
  - search
  - secrets
  - sign
  - thread
  - track
  - trade
  - trending
  - unpin
  - unreact
  - visitors
  - vote
  - watch
  - welcome
  - who
  - whoami

@daemon (5 commands)
  - actions
  - activity
  - activity_report
  - schedule
  - update

@drone (24 commands)
  - activate
  - add
  - branches
  - check
  - exists
  - info
  - list
  - load
  - lock
  - lookup
  - path
  - pr
  - remove
  - reset
  - resolve
  - route
  - route_all
  - scan
  - set
  - status
  - sync
  - system
  - systems
  - unlock

@flow (11 commands)
  - aggregate
  - close
  - create
  - list
  - post_close
  - register
  - registry
  - restore
  - scan
  - templates
  - unregister

@memory (13 commands)
  - analyze
  - bootstrap
  - check
  - demo
  - extract
  - fragments
  - rollover
  - search
  - status
  - symbolic
  - templates
  - verify
  - watch

@prax (4 commands)
  - dashboard
  - log-audit
  - monitor
  - status

@seedgo (8 commands)
  - audit
  - checklist
  - diagnostics
  - diagnostics_audit
  - readme
  - readme_update
  - standards_audit
  - standards_query

@skills (6 commands)
  - create
  - discover
  - info
  - list
  - run
  - validate

@spawn (4 commands)
  - create
  - delete
  - passport
  - update

@trigger (15 commands)
  - branch_log_events
  - core
  - errors
  - fire
  - list
  - log_events
  - medic
  - mute
  - off
  - on
  - reset
  - start
  - status
  - stop
  - unmute

DISCOVERED: 173 commands across 14 branches

---

## 4. Test Coverage (26% module coverage)


@ai_mail (49 tests, 2 files)
  tests/test_send_identity.py              -- 36 tests  -> email, users
  tests/test_user_paths.py                 -- 13 tests  -> users
  UNTESTED: branch_ping, central_writer, dispatch, json, json_utils, monitoring, notify, registry

@api (0 tests, 0 files)
  (no test files found)

@backup (0 tests, 1 file)
  tests/test_pattern_scan.py               --  0 tests  -> config, operations
  UNTESTED: backup_core, config, diff, google_drive_sync, integrations, json, models, operations, reauth_drive, reporting, utils

@cli (0 tests, 0 files)
  (no test files found)

@commons (82 tests, 2 files)
  tests/test_commons.py                    -- 72 tests  -> curation, database, notifications, profiles, search, welcome
  tests/test_lifecycle.py                  -- 10 tests  -> database, search
  UNTESTED: activity, artifact, artifacts, capsule, catchup, central, comment, comments, commons_identity, dashboard, digest, engagement, explore, feed, identity, json, leaderboard, notification, post, posts, profile, reaction, room, rooms, social, space, trade

@daemon (31 tests, 1 file)
  tests/test_actions_registry.py           -- 31 tests  -> actions
  UNTESTED: activity_report, json, monitoring, schedule, scheduler_ops, update, wakeup_ops

@devpulse (0 tests, 0 files)
  (no test files found)

@drone (335 tests, 9 files)
  tests/test_activation.py                 -- 38 tests  -> command_registry, executor
  tests/test_commands.py                   -- 35 tests  -> command_registry, commands
  tests/test_discovery.py                  -- 40 tests  -> discovery, discovery_handler, exceptions, module_registry_handler
  tests/test_executor.py                   -- 26 tests  -> exceptions, executor
  tests/test_git_module.py                 -- 46 tests  -> git, git_module, module_registry_handler
  tests/test_registry_handler.py           -- 33 tests  -> exceptions, registry_handler
  tests/test_resolver.py                   -- 52 tests  -> exceptions, registry_handler, resolver
  tests/test_router.py                     -- 37 tests  -> exceptions, executor, router, router_handler
  tests/test_scan.py                       -- 28 tests  -> scan, scanning
  UNTESTED: config, json, module_registry, registry

@flow (0 tests, 0 files)
  (no test files found)

@memory (0 tests, 0 files)
  (no test files found)

@prax (0 tests, 0 files)
  (no test files found)

@seedgo (0 tests, 0 files)
  (no test files found)

@skills (123 tests, 8 files)
  tests/test_cli_routing.py                -- 20 tests  -> ?
  tests/test_discovery.py                  -- 32 tests  -> discovery_handler
  tests/test_lifecycle.py                  -- 12 tests  -> creator, discovery, loader_handler, runner, template
  tests/test_loader.py                     --  7 tests  -> loader
  tests/test_registry.py                   -- 14 tests  -> registry
  tests/test_runner.py                     -- 13 tests  -> runner
  tests/test_runner_handler.py             -- 14 tests  -> runner_handler
  tests/test_validator.py                  -- 11 tests  -> validator
  UNTESTED: creator_handler, json

@spawn (113 tests, 5 files)
  tests/test_citizen_classes.py            -- 28 tests  -> class_registry, core, passport_ops, update, update_ops
  tests/test_handlers.py                   -- 36 tests  -> change_detection, json_ops, meta_ops, reconcile
  tests/test_lifecycle.py                  -- 22 tests  -> delete, delete_ops, sync_registry, sync_registry_ops, sync_templates, sync_templates_ops
  tests/test_spawn.py                      -- 13 tests  -> metadata, placeholders, registry
  tests/test_update.py                     -- 14 tests  -> meta_ops, update, update_ops
  UNTESTED: file_ops, json, passport

@trigger (0 tests, 0 files)
  (no test files found)


Test Coverage Report
═══════════════════════════════════════════════════════

TESTED:
  ✓ drone            335 tests    9 files   15/19 modules covered (79%)
  ✓ skills           123 tests    8 files   10/12 modules covered (83%)
  ✓ spawn            113 tests    5 files   18/21 modules covered (86%)

PARTIAL:
  ◐ ai_mail           49 tests    2 files   2/10 modules covered (20%)
  ◐ commons           82 tests    2 files   6/33 modules covered (18%)
  ◐ daemon            31 tests    1 file    1/8 modules covered (12%)

NO TESTS:
  ✗ api                0 tests    0 files   0/10 modules covered (0%)
  ✗ backup             0 tests    1 file    0/11 modules covered (0%)
  ✗ cli                0 tests    0 files   0/5 modules covered (0%)
  ✗ devpulse           0 tests    0 files   0/0 modules covered (0%)
  ✗ flow               0 tests    0 files   0/16 modules covered (0%)
  ✗ memory             0 tests    0 files   0/16 modules covered (0%)
  ✗ prax               0 tests    0 files   0/14 modules covered (0%)
  ✗ seedgo             0 tests    0 files   0/14 modules covered (0%)
  ✗ trigger            0 tests    0 files   0/12 modules covered (0%)

═══════════════════════════════════════════════════════
SUMMARY: 733 tests across 15 branches
         3 branches tested, 3 partial, 9 untested
         Coverage: 52/201 modules (26%)

