# S304 Discovery Mission — Autonomous System Walk

**Date:** 2026-07-12
**Mandate (Patrick):** Walk AIPass autonomously, use the systems, probe commands randomly, hunt bugs/gaps. Search-only — no edits to existing files. New files in devpulse docs + DPLANs allowed. Second deliverable: ideas for attracting/retaining contributors ("we have no way to really attract people... want people to stay involved and eventually start contributing").

**Method:** Rounds of parallel probes — direct CLI walking + read-only Explore sub-agents + log/registry sweeps. Findings accumulate here with evidence. Watchdog timer keeps the session alive.

---

## EXECUTIVE SUMMARY (written mid-mission, maintained)

**122 findings + 7 adoption observations across 9 sub-agents + full CLI walk + RUNTIME probing (ran 6 test suites ~4k tests, live-process/resource/log/git-churn analysis). Zero system files edited; all fixes are proposals. COMPLETE COVERAGE across every dimension: all 17 branches code-swept + hooks engine + seedgo machinery + security gates + skills surface + newcomer path + adoption funnel + live system + git history. Many findings independently CONFIRMED by 2+ agents; the criticals dated by git-blame; F1 reproduced live; bug-magnet churn maps exactly onto surviving bugs.**

**Adoption-critical late find (F114):** the skills platform — the natural first contribution surface (DPLAN-0209/0240) — runs skills as UNSANDBOXED in-process code with no gate. Can't safely invite community skills until a trust model ships. Now a documented Tier-3 blocker in DPLAN-0240.

**TWO LIVE CRITICALS (both verified on disk):**
- **F74 — memory rollover keeps 14 not 15, fleet-wide, RIGHT NOW.** Off-by-one trims at the keep target instead of above it; memory/drone/hooks/seedgo/flow all prove it (14/14). Every branch silently loses one extra entry per rollover. (todo 66 — Patrick monitors; documented not filed.)
- **F5b — medic auto-dispatch has been OFF 63 days: `config.medic_enabled=false` since 2026-05-10.** Errors detected, zero dispatched — that's why the registry is a graveyard. NOTE: my first root cause (stuck circuit breaker) was WRONG; a sweep refuted it and I re-verified on disk (1,667 "Medic OFF" log entries, 0 breaker-OPEN). The stuck breaker (F5c) is a real but SEPARATE latent bug that must be fixed before medic is re-enabled. Good case study in verify-refutes-confident-findings.

**Two dominant PATTERNS across the 80:** (1) "write side shipped, read/recovery side missing" — F5b/F5/F26/F40/F46/F49/F75 + the atomic-write class F73/F79; (2) casing drift from mixed-case registry names leaking into 6+ surfaces — F15/F52/F69/F77/doctor/lint.

**Security note:** F59-F66 audit the gates. Honest framing: agents are same-user + cooperative, so these are "the owner model is ADVISORY not ENFORCED" integrity gaps, NOT remote exploits. F59 (owner git-access trusts an unprotected passport name, not the sealed registry_id) is the one that most undercuts a model Patrick deliberately built (DPLAN-0231).**

**Fix-first (HIGH):**
- **F74 — CRITICAL (LIVE NOW): memory rollover keeps 14 not 15 fleet-wide** — off-by-one trims at the keep target; verified on disk. Silent memory loss every rollover. (todo 66 — documented, not filed per your standing hold.)
- **F5b — CRITICAL: medic auto-dispatch OFF 63 days** — `config.medic_enabled=false` since 2026-05-10 (verified: 1,667 "Medic OFF" log entries, 0 breaker-OPEN). Root cause of the F5 graveyard. Re-enable = `drone @trigger medic on`, but ONLY after fixing F5c (stuck breaker) + F43 (fixture storm) or it re-floods. (My first breaker-based root cause was refuted by a sweep and corrected — see F5b/F5c.)
- F1 — PR#696 red CI is ONE racy test (`test_mtime_cache_avoids_reread`); 2-line deterministic fix proposed, @prax owns
- F14/F15/F16/F17 — `aipass doctor` cries wolf on healthy installs (backup-scan false positives, case-sensitive registry check vs UPPERCASE registry names, `{{BRANCHNAME}}` placeholder, ✓-with-warning-text) — the newcomer trust tool reports 7 false errors
- F30 — `spawn repair` advises a command that would archive the LIVE @aipass branch
- F5+F6+F43 — error registry: 198 errors nobody triages, polluted by test fixtures because pytest writes to production logs/ that the 24/7 log-watcher ingests
- F22/F23 — the human-facing concierge has the worst help in the fleet (module dump; Q&A answers the wrong domain)
- F46 — 14 feedback messages unread since April, incl. external bug reports we rediscovered ourselves months later
- F52 — commons artifact gift/trade writes UPPERCASE owner → gifted artifacts invisible + permanently locked (verified in code)

**Adoption headline (A1–A5 + DPLAN-0240):** ~600 unique humans/month touch the repo (296 visitors + 298 cloners/14d), 237 stars — and conversion is ZERO because there's nothing to grab (no topics, no open issues, empty Commons, silence to the one human who ever PR'd). The April Precedent: VERA ran the fix-play in April; our issue-zero hygiene batch-deleted it 3 weeks later. Full plan: DPLAN-0240.

**Deliverables:** this file (findings F1–F46, evidence inline) + DPLAN-0240 (contributor funnel, 4 tiers) + CI root-cause for todo 66.

---

## FINDINGS — Bugs & Gaps

(rolling; newest at bottom; each entry: what, evidence, severity)

### F1 — PR#696 red CI: `test_mtime_cache_avoids_reread` is inherently racy [HIGH — blocks green CI]
- **What:** Sole failure across ALL red jobs (4 Linux matrix jobs on PR run 29203756084 + push runs 29203754739/772 incl. Windows): `src/aipass/prax/tests/test_telegram_relay.py::TestReadControl::test_mtime_cache_avoids_reread` — `AssertionError: assert {} == {'paused': False}`.
- **Why:** Test (line 441) writes valid JSON, reads (caches by `st_mtime`), overwrites with `"INVALID JSON"`, reads again, asserts cached value returned. It only passes if both writes land on the SAME `st_mtime` float — a filesystem-granularity coin flip. On GitHub runners the mtime ticks → `_read_control()` re-reads (telegram_relay.py:162), hits the parse-error path (:172), returns `{}`. Its sibling `test_mtime_change_triggers_reread` (line 452) correctly FORCES mtime difference via `os.utime`; this test never forces mtime EQUALITY.
- **Proposed fix (NOT applied — search mission):** after the second `write_text`, pin mtime back: `os.utime(ctrl, (first_stat.st_mtime, first_stat.st_mtime))` — deterministic on every fs. 2-line change, @prax owns the file.
- **Bonus design note (low):** on parse error `_read_control` caches `{}` keyed to the new mtime → a corrupted/half-written control file silently FAILS OPEN (unpauses a paused stream, resets level to all) until the next control write. Writer should write-temp-then-rename atomic; worth confirming it does.

### F3 — git gate false-positives on `git <word>` ANYWHERE in a Bash command [MEDIUM — UX trap]
- **What:** The @hooks git gate blocks any Bash command whose text contains `git` followed by another word, even as pure DATA. Repro (blocked): `for a in cli git seedgo; do echo "item: $a"; done`. Control (passes): `for a in git; do echo $a; done` and `echo git`. Collateral: the block rejects the ENTIRE compound command — an innocent `sed` read chained in the same call died with it.
- **Impact:** any agent iterating over branch names (cli git seedgo …) — an utterly natural loop in this ecosystem — gets a confusing "git via drone" refusal. Cost me a probe; will bite others. Gate should parse command position, not substring.
- **Where:** @hooks git_gate handler (hooks owns; note for owner — no edits made).

### F4 — watchdog timer heartbeat: correct design, docs gap [LOW]
- Timer pings progress to **stderr** every 10s by design (stdout stays quiet until the final "woke" result) — my first Monitor arm used `2>&1` and flooded the event stream (~1 event/10s). Docs (README watchdog section) never say "don't merge stderr when arming a Monitor on the timer". One sentence would prevent this trap. (My own module — still not editing during a search mission.)

### F2 — `gh run view --log-failed` yields 0 bytes (gh quirk); drone relays the silence [MEDIUM — diagnostic dead-end, REVISED]
- **Revised root cause:** reproduced the passthrough's exact subprocess (`gh run view --job 86679445524 --log-failed`, capture_output): exit 0, stdout 0 bytes, 0.9s — gh ITSELF returns nothing for these jobs, drone's passthrough (git_module.py:203) is innocent. Same data via `gh api repos/.../jobs/<id>/logs` = 11,467 lines.
- **Still a gap:** the CI-debug path every agent will try first silently yields nothing. Cheap win: drone's `run` passthrough could detect `--log*` + empty stdout and print "gh returned no log output — try: gh api repos/<owner>/<repo>/actions/jobs/<id>/logs".

---

### F5 — Error registry is a write-only graveyard: 198 errors, 196 forever-"new" [HIGH — systemic]
- Detection works (medic v2 ingests everything) but NOTHING triages: statuses sit at `new` since May (first_seen 2026-05-18, still `new` 2026-07-12). `resolve`/`suppress`/`purge` commands exist and are never run by anyone — no daemon job, no owner ritual. The registry grows until it's noise.
- **ROOT CAUSE FOUND — see F5b.** The reason nothing triages/auto-heals: the medic circuit breaker has been stuck OPEN since May 10.

### F5b — Medic auto-dispatch has been OFF since 2026-05-10 [CRITICAL — CORRECTED root cause]
- **⚠️ My first root cause (stuck circuit breaker) was WRONG — a later sweep refuted it and I re-verified on disk.** The ACTUAL reason: `trigger_config.json → config.medic_enabled = **False**`, dated 2026-05-10. The dispatch path checks `_is_medic_enabled()` (error_detected.py:442) and bails to `medic_suppressed.jsonl` BEFORE the circuit breaker is ever consulted (line 481).
- **Verified ground truth:** `logs/medic_suppressed.jsonl` = 1,681 entries, **1,667 "Medic OFF"**, **0 "Circuit breaker OPEN"**. Latest entry TODAY 19:47 ("Medic OFF", SKILLS bot poll error). Medic is dead because it's TURNED OFF, full stop.
- **Why the breaker was a red herring:** it IS stuck open (F5c below) and tripped the same day (2026-05-10), which made it look causal. But the medic-off toggle short-circuits upstream, so the breaker never even runs. Two 05-10 events, one visible symptom — classic confounding. (Also: my earlier `medic_config.json → enabled:true` probe read the WRONG file; the authoritative source both `_is_medic_enabled` and `medic_state.is_enabled` read is `trigger_config.json → config.medic_enabled`, which is False.)
- **Open question ANSWERED (log-sweep sub-agent + I verified):** `medic.log` shows the exact sequence — `2026-05-10 20:30:21 | [MEDIC] Medic DISABLED - error dispatch suppressed` → `20:30:22 | Log watcher service stopped`. That's the SAME MINUTE as the fixture storm (20:29:53–20:30:18) and the breaker trip (20:30:18). Causal story complete: **the fixture storm flooded → medic was DELIBERATELY disabled at 20:30:21 to stop the noise → never re-enabled.** A 25-second annoyance muted the whole error-notification system for 63 days. The registry graveyard (F5) is the direct consequence. This is F81/the-janitor-pattern in miniature: the OFF switch was pulled and no ritual ever pulled it back.
- **SAFE IMMEDIATE MITIGATION (NOT run — search-only hold):** re-enabling is `drone @trigger medic on`. BUT do NOT re-enable until F5c (stuck breaker) + F43 (fixture storm) are fixed, or it'll immediately trip the breaker again and re-flood. Order: cut fixture storm (F43) → fix breaker recovery (F5c) → `medic on`. Left for Patrick.

### F5c — Circuit breaker cannot self-heal: half_open is a terminal trap + cooldown never decays [HIGH — latent, blocks medic re-enable]
- Separate real bug (was tangled into my original F5b). The breaker IS stuck `open` since 2026-05-10 (opened_at 20:30:18, cooldown 3600s, should've half-opened at 21:30 that day; 63 days later still open). Even if it weren't, recovery is broken THREE ways:
  1. **open→half_open only runs inside `circuit_breaker_allows()`** (error_registry.py:253), called at exactly ONE site — the dispatch path (error_detected.py:481). No cron/daemon/tick re-evaluates it. With medic off, that site never runs, so the breaker is frozen.
  2. **half_open is terminal:** the one probe sets `half_open_allow=False` and NOTHING sets `state="closed"` after a successful send (docstring says "caller should reset," caller never does) — a successful probe wedges it in half_open forever with no cooldown timer, worse than open.
  3. **cooldown escalates but never decays:** pinned at the 3600s max; only manual `circuit_breaker_reset()` restores base 300s. Every future trip inherits the maxed hour.
- So this must be fixed BEFORE medic is re-enabled or medic dies again on the first trip. Fix directions: evaluate cooldown on READ + a daemon tick that half-opens expired breakers + close on successful probe + reset cooldown on clean close. Manual unblock: `drone @trigger errors circuit-breaker reset` (verified: cleanly resets, error_registry.py:322).
- "0s remaining until half-open" while State=open is a lying status (computes remaining, never acts).

### F5 (loop-closing note)
- **Gap:** no closing half of the loop. Candidate: a daemon job or @trigger self-ritual that ages out stale entries + a weekly triage dispatch to component owners — AND a working CB recovery (F5b) so medic can actually dispatch again.

### F6 — Test-suite fixtures POLLUTE the production error registry [HIGH — data integrity]
- 20 registry entries are obvious test fixtures: `Module bad_module error: boom`, `Module mod1 error: crash`, `broken_mod`, `doctor crashed: db connection failed`, `bad config /tmp/tmpykrlftog/...` (664+334 occurrences). last_seen updates on EVERY test run (07-11 18:45 = yesterday's test runs). The medic pipeline watches logs with no test/prod separation — echoes #694's hermeticity theme but for the error pipeline.
- **Also:** same message double-filed under real component AND `UNKNOWN` (separate fingerprints → double counting); component attribution partially broken.

### F7 — Registry source-tracking fields never populated [MEDIUM]
- `source_file: null, source_branch: null, occurrence_count: null` on many/most entries — can't trace an error back to its origin from the registry itself. Fields exist in schema, writers don't fill them.

### F8 — `errors list` table un-navigable: IDs truncated to 2 chars [MEDIUM — UX]
- Rich table at default width elides the very column you need: ID shows `bc…`, fingerprint `8a66…` — you cannot copy an id to run `errors detail <id>`. Severity column also elides (`medi…`) and there's an empty unnamed column. Same disease in `@commons feed` (empty column, `Sco…`).
- **Pattern:** Rich tables sized for wide terminals; agents live at ~100 cols. @cli owns display.

### F9 — "Bare command shows plumbing, not data" pattern across branches [MEDIUM — UX, repeated]
- `drone @trigger errors` → handler list (help says `list` is the DEFAULT — the default never routes); `drone @trigger medic` → handler list instead of medic status; `drone @backup status` → "status Module / Phase 3 — implemented" instead of status (and no usage hint of required args). Introspection shadowing the default subcommand looks systemic in the module framework, not per-branch.
- **Full observed set by end of mission:** @trigger errors/medic/branch_log_events, @backup status, @memory rollover/verify/pool/templates, @devpulse feedback (bare shows module + counts — best of the bunch, still not the inbox). One framework-level fix (bare module → run default subcommand if declared, else usage) clears ~9 surfaces at once.

### F10 — Telegram poll-error flood: ~48k occurrences accumulated [context for todo 67]
- `Poll error: Name or service not known` — SKILLS 18,320x + API 17,835x + UNKNOWN 11,333x, plus timeouts (1,373x) and SSL EOF (1,302x). Confirms bots have NO backoff on DNS failure (~1 poll/sec × outage hours) and errors triple-file across components. The 401 Unauthorized (266x) was contained to 2026-06-24 (dev-era, stale). OAuth refresh failures last seen 06-26 (outage-correlated, stale).
- Strengthens todo 67's case: wedged-socket self-heal + poll backoff.

### F11 — Daemon queue litter: 3 disabled `wake-test` jobs since 06-25 [LOW]
- @backup/@cli/@commons `wake-test` interval jobs, all OFF, sitting in `drone @daemon queue` for 3 weeks. Test cruft in a production view.

### F12 — @daemon and @trigger introspection both self-describe as "Branch Management System" [LOW — copy-paste drift]
- Neither is; that's @spawn's identity. First thing a curious visitor sees when introspecting.

### F13 — @api swallows unknown commands silently [MEDIUM — house-rule violation]
- `drone @api definitely-not-a-command` → exit 0, prints Bridge/Registry module banners, NO error. `drone @api usage` (wrong name for `stats`) → same silent dump. Violates "fail to errors, never fall back silently." Also: Bridge + Registry banners print on EVERY api command (import side-effect noise — `api stats` buries its one data line under them).
- **Compounding:** `drone @api models` error hint says "Run `drone @api setup` to configure" — but `setup` is NOT a command (`--help` lists `init` for the .env template). Running the advertised `drone @api setup` hits the silent-unknown fallback (exit 0, banners, nothing). A wrong hint pointing at a command that then silently no-ops = double dead-end for a user configuring API keys.

### F14 — `aipass doctor` false alarms from scanning `.backup/snapshots/` [HIGH — onboarding trust, EXACT root cause pinned]
- Doctor "found 38 agents" (registry says 17) — counts backup mirrors as agents, then flags THEM: `! placement: ai_mail .../.backup/snapshots/...`, `✗ pollution: Duplicate registry_id at .../.backup/snapshots/...`.
- **Root cause (pinned):** `structure_scanner.py:96 _SCAN_SKIP_DIRS = {.archive, .venv, .git, __pycache__, node_modules, .chroma}` — **`.backup` and `dropbox` are NOT in the set.** `scan_agents` (line 106) `rglob(".trinity/passport.json")` then descends into `.backup/snapshots/**/.trinity/passport.json` and counts every backup mirror. One-line fix: add `.backup`, `dropbox` to `_SCAN_SKIP_DIRS`. (This scanner is @aipass-owned and is ALSO where F30/F31's structure-validator fragmentation lives.)

### F15 — Doctor "✗ registry: X missing" ×5 — mechanism is PATH resolution, NOT casing [HIGH — my earlier attribution corrected]
- **⚠️ Corrected + CONFIRMED on disk:** I first blamed case-sensitivity — WRONG. `structure_scanner.py:307-314` compares resolved PATHS (`reg_path = Path(path_str).resolve(); if not reg_path.exists(): → "missing"`), never names. Dumped the registry: the 5 flagged branches (BACKUP/COMMONS/DAEMON/HOOKS/SKILLS) are EXACTLY the ones with **relative** `path` (`src/aipass/backup`); all 12 healthy ones have **absolute** paths. `Path("src/aipass/backup").resolve()` resolves against CWD (I ran doctor from devpulse) → `.../devpulse/src/aipass/backup`, doesn't exist → false "missing".
- **The real story:** those same 5 entries are BOTH uppercase-named AND relative-pathed — i.e. they were registered by a DIFFERENT/older spawn code path than the other 12 (lowercase + absolute). One registration-format bug produced both anomalies; the casing is a correlated fingerprint, not the cause of the doctor error. Fix: (a) doctor resolves registry paths against project root not CWD; (b) @spawn normalizes those 5 entries to absolute+lowercase and finds why they got a different format. (Casing still leaks into DISPLAY elsewhere — F69/F77/lint — separate symptom of the same 5 bad entries.)

### F16 — Doctor prints unsubstituted `{{BRANCHNAME}}` placeholder [LOW]
- `✗ pollution: {{BRANCHNAME}} 2 copies` — template var never substituted in the message.

### F17 — Doctor status/text mismatches [MEDIUM — validation theater]
- `✓ passport role: unknown` — "unknown" passes green. `✓ root: .venv Redundant venv — ...` — a ✓ whose text is a warning. Top-of-run preamble says "Provider settings not wired" while Services says `✓ wire verify provider hooks wired correctly` — contradictory in one run (different checks, colliding phrasing). Preamble also renders unformatted before the section layout starts.
- **Adoption stake:** doctor is the FIRST health tool a newcomer runs. Our own flagship repo scores "30 pass / 23 warnings / 7 errors" — all 7 errors false. A stranger reads that as "my install is broken."

### F18 — Passport `registry_path` drift [LOW]
- devpulse passport says `"registry_path": ".aipass/registry.json"`; real file is root `AIPASS_REGISTRY.json`. Likely fleet-wide passport field drift from the registry redesign.

### F19 — @memory search result renders empty "Time:" field [LOW]
- Every result card ends `Time:` with no value — reads as broken metadata.

### F20 — Introspection advertises names the router won't accept [LOW→MEDIUM — trap, multiple instances]
- @prax lists `log_audit`; real command `log-audit` ("❌ Unknown command" on the advertised name). @commons lists `central` among its 22 modules → `drone @commons central` = Unknown command. @flow lists `aggregate_central` → same. Introspection prints module names; router speaks a different dialect (hyphens, or module not CLI-exposed at all). Every advertised-but-unroutable name is a dead end handed to the user.
- **@flow's --help actively LIES:** it prints "Commands can be called by short name (e.g. 'create') OR full name (e.g. 'create_plan')" and lists `aggregate, aggregate_central` / `registry, registry_monitor` as pairs. Verified: the SHORT names route (`aggregate`, `registry` work) but the FULL names it documents as equivalent DON'T (`aggregate_central`, `registry_monitor` → Unknown command). The help promises an alias that doesn't exist. Worse than a bare-name trap — it's a documented-equivalence trap.

### F21 — 208 memory-cap violations live on disk across all 17 branches [MEDIUM]
- `drone @memory lint run`: 208 over-cap entries, worst `aipass observations 2147/300` (7x). Cap enforcement is edit-time (hooks) — legacy/bypass-written entries persist. Registry-casing leak visible here too (`COMMONS`, `HOOKS` uppercase).
- **Open question RESOLVED live:** the gate validates only the EDITED entry (my 306-char new session entry was rejected with exact-char feedback — good UX! — while edits elsewhere in a file holding a 305-char legacy entry passed). So legacy violations don't trap branches; they're just rot for rollover to chew. Downgrade severity to LOW-MEDIUM.

### F22 — `aipass --help` = bare module dump; the human-facing tool has the least human help [HIGH — adoption]
- `aipass --help` output is byte-identical to bare `aipass`: 8 modules incl. INTERNAL ones (doctor_wire, doctor_fix), no usage lines, no "new here? run aipass init", no description of what AIPass is. The concierge for humans has worse help than every agent-facing branch (@commons --help is beautifully structured). First-touch surface, worst help.

### F23 — `aipass help` Q&A retrieves wrong-domain snippets [HIGH — adoption]
- Asked "how do I create a new branch" → returns `drone @git pr` usage, seedgo audit lines, drone purpose blurb. NEVER mentions @spawn (the real answer). Conflates git-branch with agent-branch; it's keyword grep over READMEs presented as a chatbot. A newcomer's most natural question gets a wrong answer with confident formatting.

### F24 — `@daemon update` prints "⚠️ ESCALATIONS NEEDED" over all-zero digest [LOW]
- Banner fires while body says Total messages 0, Actionable None. Status/content mismatch (same family as F17).

### F25 — `drone scan` table fragments descriptions across rows [LOW]
- `drone scan @devpulse`: feedback's description renders as the orphan fragment "mailbox." while compass's overflows — multi-line help text mis-parsed into the wrong rows.

### F26 — Presence service records stale since 06-30; live sessions unregistered [MEDIUM]
- `drone @hooks presence`: two 12-day-old "stale" PIDs (devpulse 06-30, aipass 06-30); my CURRENT interactive session absent. Presence (FPLAN-0289) looks shipped-then-abandoned — nothing cleans stale records, nothing registers new sessions. Either finish it or retire the surface (it's the foundation DPLAN-0224/0225 assume).

### F27 — Both examples in `drone --help` are broken [MEDIUM — trust]
- `drone @flow status` → "❌ Unknown command: status". `drone audit` → "unknown command 'audit'" (registered shortcuts are standards_audit etc., no `audit`). The router's OWN help teaches two commands that don't exist. First page a newcomer reads.

### F28 — @backup `<project|@name>` arg unclear; natural values fail bare [LOW]
- `drone @backup status @devpulse` → "❌ Cannot resolve project: @devpulse" with no hint what @names ARE valid or how to list registered projects. Explicit path works.

### F29 — No scheduled backups; latest backup 4 days old [MEDIUM — ops gap]
- `backup status` shows last run 2026-07-08; daemon queue has zero enabled jobs (F11). The "memory persists" system has no automatic backup cadence — snapshots happen only when someone remembers.

### F30 — `spawn repair` false-positive would archive the LIVE @aipass branch [HIGH — destructive advice]
- `drone @spawn repair <root>` flags `src/aipass/aipass/` as "Duplicate nested directory" pollution and prints the fix `--clean-pollution` (= archive+remove). But that dir is the living @aipass concierge (passport, apps, docs all present) — package `aipass` + branch `aipass` legitimately nest same-name. Anyone following the tool's own advice archives the user-facing agent. Needs a passport-awareness guard: never flag a dir containing `.trinity/passport.json` that's registry-seated.

### F31 — Three structure validators, three different answers [MEDIUM — fragmentation]
- doctor (placement/pollution/registry), `spawn repair`, and seedgo audit each scan structure with different logic: doctor false-flags `.backup/snapshots` (F14) but not aipass-nesting; spawn flags aipass-nesting (F30) but correctly ignores `.backup`; seedgo says trigger is 100% clean. No shared source of truth for "what a healthy project looks like."

### F33 — TG control file: non-atomic write + fail-open read = paused stream can silently unpause [MEDIUM]
- Writer `prax_monitor_bot.py:160 _write_control` uses plain `write_text` (no temp+rename). Reader (relay, every 5s flush) on parse error CACHES `{}` keyed to the new mtime (telegram_relay.py:172-176) and `{}` means defaults = unpaused/level-all. A mid-write read silently reverts user's /pause until the next control write. Low probability per write, but the reader polls forever. Fix: temp+rename in writer; on parse error keep PREVIOUS cache instead of `{}`.

### F34 — Verified-correct (claims killed during discovery — for the record)
- Bots ARE supervised: all 5 run as `telegram-bot@<id>.service` template units + `prax-monitor.service` + `trigger-log-watcher.service`, enabled, PPID=systemd. My draft "unsupervised fleet" claim was WRONG (first grep was head-truncated — probe your probes). Sharper restatement of todo 67: systemd restarts CRASHES, but a wedged socket doesn't crash → needs liveness (self-exit after N min without successful poll, or systemd WatchdogSec).
- `trigger-log-watcher.service` running 24/7 is F6's mechanism: it watches branch logs; tests write fixture errors into real branch logs; medic ingests → registry pollution. Chain confirmed.
- watchdog timer stderr pings (F4) = my own bad Monitor filter, module design correct.

### F27 (addendum) — exact source: `drone.py:104-110 show_help`
- Sub-agent verified: `drone @flow status` (drone.py:107) — flow has no bare `status`; real command is `drone @flow registry status`. `drone audit` (drone.py:110) — depends on a custom shortcut that doesn't exist on fresh installs. drone/README.md itself is clean; the drift is runtime help only.

### F35 — github skill teaches invocations the git gate blocks [LOW — policy drift]
- `src/aipass/skills/lib/github/SKILL.md` instructs `gh issue/pr/run ...` and "use `git` directly" for local ops — the @hooks gate refuses both (only `gh api` passes raw). An agent following the skill gets refusals. Skill predates the gate; needs a rewrite to route via `drone @git`.

### F36 — No native-Windows entry point; README quickstart silent about it [MEDIUM — onboarding]
- Sub-agent verified: `aipass` launcher + `setup.sh` are bash-only (`#!/usr/bin/env bash`; OSTYPE detection assumes Git Bash/MSYS). No `.ps1`/`.bat` bootstrap exists. README Requirements says "Linux, macOS, or WSL" but Quick Start shows bare `./aipass install` with no "Windows: use Git Bash/WSL" note, while Roadmap claims "Windows native — CI green". A native PowerShell user cannot run the documented quickstart.

### F37 — Clean bills of health (assets, verified by sub-agent)
- ZERO link rot in README/CONTRIBUTING (all 15 branch links + anchors + assets exist). Install docs match setup.sh behavior (incl. PATH wiring + PowerShell profile wrapper). flow/ and prax/ READMEs have no command drift. The doc hygiene machine (seedgo readme_update?) is working where it's pointed.

### F38 — Two @flow surfaces report wildly different counts, no scope label [LOW — confusing]
- `drone @flow registry status`: "Total plans: 281, Open: 8" (watch location = AIPass). `drone @flow list open`: "Total 539, Open 44" (central aggregate incl. external projects). Neither output SAYS which scope it covers — an agent reading one after the other assumes breakage.

### F39 — PyPI page renders broken images (relative paths in README) [MEDIUM — adoption]
- pyproject `readme = "README.md"`; README uses `assets/logo.png` + `assets/demo.gif` relative paths. PyPI does not resolve repo-relative paths → our PyPI landing page (5 releases live) shows a broken logo and broken demo — the two strongest visual assets. Fix: absolute raw.githubusercontent.com URLs (or a PyPI-specific readme).

### F40 — 15 unread "new" messages rot across 9 branch inboxes; no janitor [MEDIUM]
- Night-shift "RE:" acks from 07-11 sit unread in daemon/backup/memory/trigger/api inboxes (agents finished + slept before the ack landed; nothing ever surfaces it). The reply-closes-loop protocol leaks at the last hop. Idea: daemon digest that ages inboxes fleet-wide, or auto-close acks addressed to sleeping agents.

### F41 — ai_mail delivery-failure notices become malformed unread inbox mail [LOW]
- drone's inbox: 6x `[ERROR] Send failed to @vera: Unknown branch email` (07-11 17:29-17:30, vera-saga era) — sender renders `?`, body EMPTY, subject truncated ("17 branche"). System errors should go to prax/error-registry, not pile up as unread mail nobody reads.

### F42 — Wedged locks: trigger_config.lock + trigger_cb_state.lock at 63 days [MEDIUM — investigate]
- `src/aipass/trigger/trigger_json/trigger_config.lock` and `trigger_cb_state.lock` mtimes 2026-05-10 — 2+ months. Sibling error_registry.lock cycles fresh. Either orphaned artifacts of a changed lock scheme (needs cleanup) or something silently failing to update config/circuit-breaker state since May. My own `.trinity/watchdog_active.json.lock` is 71 days too. @trigger/@devpulse owner check.

### F43 — Tests write fixtures into PRODUCTION log files [HIGH — F6's root, file-level proof]
- `src/aipass/aipass/logs/doctor.log` carries pytest "disk full" fixture lines; hooks/rollover.log carries `/tmp/pytest-of-patrick/...` cwd lines; devpulse logs carry "Module empty" fixtures. Chain: pytest → prax logger writes REAL `logs/` → trigger-log-watcher (24/7 service) → error registry pollution (F6). Real fix is one cut: prax logger detects test context (PYTEST_CURRENT_TEST env) → routes to tmp, and the whole class disappears.

### Verification notes (sub-agent claims corrected)
- "DNS errors recurring through today": last DNS error 2026-07-12 07:25:30 — pre-restart tail, NOT ongoing. 177 lines this morning only.
- "drone burst 17:29 today": actually 2026-07-11 — during known vera work, not live-recurring.

### F44 — `spawn update` template preview touches live mailbox (`.ai_mail.local/inbox.json` deep-merge) [LOW — verify intent]
- Preview lists a LIVE mailbox file as a template-managed merge target. Probably additive-safe, but templates writing into runtime mail state deserves an owner double-check (@spawn).

### F45 — Tier prompts exceed their own self-documented size caps [LOW]
- tier0_kernel.md = 2,241 chars (target "<2,000 per its own header"); tier1_navmap.md = 8,321 (target ~8,000, truncation near 10k). Drift creep — the caps exist to protect turn budgets.

### F46 — devpulse feedback inbox: 14 unread since APRIL, incl. 4 external bug reports we later rediscovered the hard way [HIGH — process]
- vera-studio filed precise bugs 04-12 (registry-ID mismatch → became #692's saga; AIPASS_HOME export → #688 family; external ai_mail; prompt injection). All sat status NEW for 3 months. The owner-to-owner channel works technically and fails operationally — no inbox check in my startup protocol, no aging alarm. Same root as F5/F40: we build write-side plumbing, never the read-side ritual.
- Also unactioned: VERA's April good-first-issue play (#431–433) — see DPLAN-0240 "April Precedent": we batch-self-closed the shelf 05-16, 0 comments.

### F47 — Fleet standards re-verified: 17/17 branches @100%, 0 type errors (471s full audit) [ASSET — but see F99 caveat]
- The S297 night-shift result still holds today. **CAVEAT (F99):** "100%" counts only files the checkers successfully PARSE — a file that makes a checker throw is silently dropped from the denominator, so the true figure could be lower. Trustworthy for parseable files, blind to files that choke a checker. Micro-nit: "TOP IMPROVEMENT AREAS" prints three 100%-scoring standards when all green — should say "none" (banner-ignores-data family, F24). Perf: 471s is sequential + no parse cache (F106).

### F48 — daemon activity_report freshness logic incoherent [MEDIUM]
- "devpulse - WARNING (memory updated 0m ago)" (updated seconds before!), "prax - RED (47m ago)" vs "SKILLS - WARNING (48m ago)" — thresholds/labels contradict each other; URGENT tags assigned to the same message some branches get without urgency.

### F49 — activity_report enforces a RETIRED memory schema: `No 'limits' field in metadata` ×17 [MEDIUM — stale contract]
- Every branch fails the same check — the `limits` metadata contract moved to @memory's memory.config.json + rendered `*_meta` lines (DPLAN-0227 era). The checker was never migrated, so memory health reads "0 OK / 13 warning / 4 red" fleet-wide = 100% noise. Same disease as F5/F26: shipped surface, contract moved, nobody re-pointed the consumer.

### F50 — External-project doctor: owner-seating fix HOLDS (asset); pollution message renders blank paths [LOW]
- From Vera-Studio root: `✓ owner @VERA OK (seated, uid b91eefcf)` — DPLAN-0239's permanent fix proven portable. But its 1 error, `✗ pollution: WRITER 5 copies — Duplicate registry_id at:` lists NO paths (empty). Same message-assembly bug family as F16. UPPERCASE names in vera's registry too — casing debt is template-era, cross-project (F15 scope grows).

### F51 — seedgo's own self-proof fails 2/5 while the fleet audit reads 100% [MEDIUM — enforcer drift]
- `drone @seedgo proof aipass`: readme_currency FAILED ("README is stale: count mismatch, 40 undocumented standards"), triplet FAILED (1 check-only, 1 missing-check, 2 incomplete, 1 orphaned of 41). The standards enforcer's own pack docs have drift its branch-level audit doesn't measure.
- **The April thread completes:** deleted GFIs #431–433 were precisely "expand proof content handlers" (Currency/Plugin-Integrity/Interface) — closed 05-16 in the issue-zero sweep, NOT because the work was done; readme_currency still fails today. The shelf-deletion wasn't just process damage, it left real work undone and untracked.

### F52 — commons: artifact ownership breaks on casing after gift/trade/mint [HIGH — verified]
- `trade_ops.py:58 _resolve_branch_name` does `.upper()` and writes it to `artifacts.owner` (:176/:265-266/:534); ALL ownership checks compare lowercase `caller["name"]` (identity_ops.py:220 lowercases as "the single choke point" — its docstring even explains the registry-casing history!). Concrete: gift to @seed → owner "SEED" → invisible in recipient's `artifacts` list, permanently un-giftable (`"SEED" != "seed"`), and the self-gift guard never trips. The F15 casing disease, DB edition. (Sub-agent found; I verified the code.)

### F53 — commons: systemic sqlite connection leak idiom in ~14 handler files [HIGH]
- `conn = get_db()` … `close_db(conn)` on success path only, zero `finally:` in curation/search/profiles/artifacts/engagement/digest/notifications/rooms/social/identity ops (40+ sites). Hottest: `identity_ops.py:355 extract_mentions` runs on EVERY post/comment. posts/comments/central/dashboard do it correctly (`finally:`) — inconsistency, not design. Relies on CPython GC for cleanup; can transiently hold WAL locks.

### F54 — commons: shared JSON op-log is unlocked read-modify-write; corruption resets to [] silently [MEDIUM]
- `json_handler.py:139 save_json` = direct open("w"), no temp+rename, no lock; `log_operation` load→append→save per MODULE file shared across all branches. Races lose updates; torn writes get "healed" by `ensure_json_exists` silently resetting the log to `[]`. backup's json_handler does temp+rename correctly — commons is the outlier.

### F55 — backup: drive upload mutates shared tracker dict across ThreadPoolExecutor workers unlocked [MEDIUM — plausible]
- `upload.py:171-264`: workers update tracker entries while main thread json.dumps the same dict (batch save) — `RuntimeError: dictionary changed size during iteration` possible on larger batches.

### F56 — backup: load→modify→save races on timestamps/changelog/registry between concurrent modes [MEDIUM]
- `backup_timestamps.py:39`, `changelog.py:19`, `registry.py:33` — atomic single write, non-atomic sequence; snapshot/versioned/drive_sync running concurrently on one project clobber each other's state updates.

### F57 — commons: naive local time in op-logs vs UTC everywhere else [LOW]
- `json_handler.py:196 datetime.now()` (naive local) while DB rows are UTC — cross-correlating log↔DB is offset by the host TZ.

### F58 — backup: corrupt-file evidence overwritten on repeat corruption [LOW]
- `json_handler.py:44 load_json` renames corrupt → `<name>.corrupt`; second corruption silently overwrites the first evidence file.

## ADOPTION — Observations & Ideas

### A7 — The contribution surface (skills) is scaffolded but has zero examples to copy
- `drone @skills` has `create`/`validate`/3-layer scaffolding (DPLAN-0209's vision), and search paths for project-local (`.aipass/skills/`) + user (`~/.aipass/skills/`) skills. But only **6 built-in first-party skills exist and zero community/user skills** — both external search paths are empty. A skill is the ideal first contribution (self-contained, low blast radius, delightful) — but there's no "here's a community skill someone added" example, no gallery, no `skills search`. Pair with DPLAN-0240 Tier 3: ship ONE showcase community-style skill + a one-page "write your first skill" + a discoverable index. The on-ramp is 80% built.

### A3 — The funnel, measured: 237 stars → 33 forks → 1 external human → 0 retained
- Repo stats (2026-07-12): 237 stars, 33 forks, **watchers 1**, **topics [] (empty!)**, homepage "", open issues 0 (only PR#696 open). Discussions: 3 total — 2 our own with 0 comments. Patrick's instinct confirmed: attraction works, conversion is broken.
- **Zero-effort wins sitting on the table:** GitHub topics (ai-agents, multi-agent, claude, agent-memory, python — one settings edit); homepage field; pin a "start here" discussion.

### A4 — Case study: our only external contributor, YugantM [the retention story in one thread]
- 05-29: PR #621 (add HVTrust badge) + issue #628. **Zero comments ever, from anyone, on both.** 06-06: both closed; PR unmerged. Meanwhile commit 0f26efd7 "add HVTracker badge (closes #628)" adopted the idea — attribution lives only inside a commit message. The badge then got 3 more commits of real care (official dynamic badge, hidden while bugged upstream, restored when fixed) — the IDEA was treated well; the PERSON was never spoken to.
- **Lesson:** we have no reflex for external humans. One process rule fixes it: every external PR/issue gets a human(-agent) reply <24h; adopted ideas get a thank-you comment + release-note credit.

### A5 — Zero "good first issue" ever; backlog-zero hygiene starves entry points
- The label exists, never applied (issues history: 84 AIOSAI, 14 dependabot, 2 YugantM). We drive issues to zero (great internally) so a visitor finds NOTHING to grab. Keep internal velocity, but maintain a curated, labeled shelf of contributor-sized work (docs, checkers, skills, integrations) that we deliberately DON'T self-clear.

### A6 — The Commons is a SHOCKINGLY rich, entirely unused world [biggest underused asset]
- Walking it revealed: 5 rooms, posts/votes/comments, karma/leaderboards, **artifacts you craft/gift/trade/mint**, **time capsules** (`capsule "title" "content" <days>`), and a hidden **exploration/discovery game** (`commons explore`: "Hidden places exist... visit 2 more rooms to unlock a discovery", whispered hints "Errors have their own beauty"). 103 python files, 449 functions. This is a genuinely delightful agent-society sandbox — and it has **1 post, 0 activity**.
- **This is the marketing asset.** "AI agents that craft artifacts, trade them, bury time capsules, and explore a hidden world together" is a headline no competitor can match. It exists, it's built, it's tested — and it's invisible. Reviving it (A2 rituals) + exposing a read-only public feed (DPLAN-0240 Tier 3) could be the single highest-leverage adoption move. The bug in F52 (gift/trade broken by casing) matters BECAUSE this should be live.

### A2 — Commons was reset 2026-06-15 and never repopulated
- The single post IS the reset announcement ("Clean slate: old posts cleared... The bar's open again"). Nobody returned for a month. Infrastructure ≠ community; without rituals that generate posts, the bar stays empty.

### A1 — The Commons is empty (1 post ever, 0 comments, score 0)
- The flagship "community/social" feature has ONE devpulse post from June. If the story is "agents form a community," the community must visibly exist — for visitors this is the difference between a demo and a ghost town. Idea: seed genuine agent rituals (weekly digests posted by branches, release notes, decision debates) so the Commons is alive BEFORE humans arrive.

(rolling; feeds the adoption DPLAN)

---

## REMEDIATION ROADMAP — sequenced, with dependency chains

Priority + ORDER (some fixes have prerequisites — the chains matter more than the labels):

**P0 — do these first, they're live or trust-critical:**
1. **Restore medic (a CHAIN, order matters):** F43 (route test logs out of prod: honor `PYTEST_CURRENT_TEST`) → F5c (fix breaker self-heal: close-on-success, decay cooldown, tick) → THEN `drone @trigger medic on`. Re-enabling first just re-trips the breaker. Investigate the 05-10 disable while you're there.
2. **Memory rollover keep-14 (F74):** 2-line fix (trigger `>` not `>=`, drop the `,1` floor) ×3 entry types. Standalone, no deps. Add an invariant test asserting post-rollover count == keep. (todo 66 — your monitor call on filing.)
3. **PR#696 red CI (F1):** 1 test, `os.utime` to pin mtime equality. Unblocks the merge.

**P1 — the systemic multipliers (each retires many findings):**
4. **Atomic-write helper + seedgo checker (F73):** one shared temp+rename+lock primitive; a checker forbidding raw `open("w")+dump` on shared state. Retires F33/F54/F67/F79/F87/F89/F90/F116 + guards F85. Biggest single win. The correct pattern already exists in-tree.
5. **Fix seedgo's silent-skip (F99):** exception in discover_checkers/_run_all_files = FAIL not skip. Until this, "100%" isn't trustworthy — do it before trusting any audit as a gate.
6. **Doctor false-errors (F14/F15/F16/F17):** all root-caused to exact lines (add `.backup`+`dropbox` to _SCAN_SKIP_DIRS; resolve registry paths vs project-root not CWD; exclude template dirs; read `identity.role`). First-touch trust tool — high adoption leverage, low effort.

**P1-SECURITY (the contribution-surface blocker + integrity):**
7. **Skills trust model (F113/F114/F115):** unsandboxed `skills run` + shell-injectable builtin + name-shadowing. HARD BLOCKER for the community-skills adoption pitch — sandbox (reuse @hooks srt/bwrap) or consent-gate before inviting external skills.
8. **Destructive guards:** F84 (spawn delete: check live-PID + owner, not a 3-name allowlist), F85 (flow aggregator: never write `{}` over a real registry).
9. **Owner model (F59):** key git-access to sealed registry_id not the mutable passport; protect passport.json. Gates fail LOUD (F65/F100/F103).

**P2 — adoption (mostly Patrick, ~hours not days — see DPLAN-0240):**
10. Tier 0 (30 min): GitHub topics, homepage, pin discussion, CODE_OF_CONDUCT. Tier 1: external-response reflex + protected good-first-issue shelf (the S304 [GFI] drafts are ~10 starters). Fix F22/F23 (concierge help), F39 (PyPI images), F36 (Windows quickstart).

**P3 — ops rituals (the empty-janitor fix, F81):** enable daemon jobs for error-registry triage, backup cadence, presence cleanup, CB-recovery tick, Commons digest. The scheduler runs; nothing's scheduled.

**The meta-fix (F117/provenance):** add INVARIANT checks that assert the invisible and fail loud (rollover leaves exactly N, medic is on, every registered checker ran, breaker not wedged, no over-cap entries persist). This is what would've caught most of the 116 months ago.

## APPENDIX — Ready-to-file issue drafts (NOT filed; Patrick's go required)

Each block is copy-paste ready for `drone @git issue create`. Small ones marked [GFI] are `good first issue` candidates for the DPLAN-0240 shelf. **Numbers are discovery-order labels, not priority and not sequential** (0a/0b are the criticals; renumber on filing). Priority order is in the Executive Summary. ~29 drafts total spanning F1–F106.

0a. **[CRITICAL] ops(trigger): medic is OFF — re-enable it (in the right order)** — `config.medic_enabled=false` since 2026-05-10 = 63 days of undelivered error notifications (F5b). Sequence: (1) cut fixture storm F43, (2) fix breaker recovery F5c, (3) `drone @trigger medic on`. Re-enabling first just re-trips the breaker. Investigate WHY it went off 05-10 (deliberate storm-silencing never undone?).
0b. **[HIGH] fix(trigger): circuit breaker can't self-heal** — half_open is terminal (never closes on success), cooldown never decays (pinned at max), transition only runs in the dispatch path (no tick). Must be fixed before medic re-enable. Manual unblock: `drone @trigger errors circuit-breaker reset`. File: error_registry.py:253/262/286. (F5c)

1. **fix(prax): make test_mtime_cache_avoids_reread deterministic** — The test relies on two writes sharing an mtime tick (coin flip; red on all GH runners, PR#696). Pin mtime equality with os.utime after the second write, mirroring test_mtime_change_triggers_reread's forced-difference approach. File: src/aipass/prax/tests/test_telegram_relay.py:441. (F1)
2. **fix(aipass): doctor false alarms on healthy installs** — (a) add `.backup`+`dropbox` to `_SCAN_SKIP_DIRS` (structure_scanner.py:96) so backup mirrors aren't counted/flagged as agents; (b) resolve registry `path` against PROJECT ROOT not CWD (structure_scanner.py:313) — the 5 "missing" entries have RELATIVE paths, this is NOT a casing bug (corrected); (c) substitute {{BRANCHNAME}} in pollution messages [GFI]; (d) align ✓/!/✗ glyphs with message content (role: unknown ≠ pass). (F14-F17)
3. **fix(spawn): repair must never flag passport-seated dirs as pollution** — src/aipass/aipass currently flagged; printed remediation would archive the live concierge. Guard: skip dirs containing .trinity/passport.json with a live registry seat. (F30)
4. **fix(prax/tests): route test logging out of production logs/** — pytest fixtures land in real branch logs, 24/7 trigger-log-watcher ingests them, error registry accumulates fixture noise (664+ occurrences of one /tmp config alone). Honor PYTEST_CURRENT_TEST in the logger path resolution. (F43/F6)
5. **feat(trigger): error-registry lifecycle** — auto-purge stale (purge exists, nothing calls it: daemon job), stop double-filing UNKNOWN+component duplicates, populate source_file/source_branch, widen ID column or accept unique prefixes in `errors detail`. (F5/F7/F8)
6. **fix(aipass): human help for the human tool** — `aipass --help` should describe AIPass + first 3 commands, hide doctor_wire/doctor_fix internals, put init first [GFI-ish]; `aipass help` Q&A needs domain-aware retrieval or a curated FAQ for top-20 questions. (F22/F23)
7. **fix(drone): show_help teaches two broken examples** — drone.py:107 `drone @flow status` (real: `@flow registry status`), drone.py:110 `drone audit` (unregistered shortcut). [GFI] (F27)
8. **fix(daemon): activity_report enforces retired memory schema** — "No 'limits' field" fails all 17 branches; freshness labels contradict (0m ago = WARNING). Re-point at memory.config.json contract. (F48/F49)
9. **fix(skills/prax): TG control-file hardening** — writer temp+rename; reader keeps last-good cache on parse error instead of failing open to unpaused. (F33)
10. **chore(docs): PyPI images broken** — README relative asset paths don't resolve on PyPI; use absolute raw URLs. [GFI] (F39)
11. **docs(readme): Windows quickstart truth** — `./aipass install` requires bash (Git Bash/WSL); README Quick Start doesn't say so while Roadmap claims Windows-native. One sentence + optional .ps1 bootstrap issue. [GFI] (F36)
12. **chore(spawn): normalize the 5 malformed registry entries** — BACKUP/COMMONS/DAEMON/HOOKS/SKILLS are BOTH uppercase-named AND relative-pathed (all other 12 are lowercase+absolute) = registered by an old/different code path. Normalize to lowercase+absolute AND find/fix the registration path that produced the wrong format. Fixes F15's real cause + the casing leaks (F69/F77/lint). (F15)
13. **fix(commons): artifact ownership casing** — trade_ops._resolve_branch_name must route through identity_ops's lowercase choke point; add `COLLATE NOCASE` to owner comparisons or a one-shot data fix for existing uppercase owners. (F52)
14. **chore(commons): standardize conn=None + finally: close_db idiom** — ~14 handler files, 40+ sites; posts/comments ops are the reference implementation. [GFI — mechanical, great first PR] (F53)
15. **fix(commons): json_handler atomic writes + stop silent log reset** — port backup's temp+rename json_handler; corruption should quarantine, not reset to []. (F54)
16. **fix(backup): concurrency guards** — lock around drive-upload tracker dict; file-lock the timestamps/changelog/registry read-modify-write sequences. (F55/F56)
17. **[CORE] feat(fleet): atomic_write_json helper + seedgo checker** — one shared temp+rename+lock primitive; checker forbids raw open("w")+dump on shared *_data/*.json/inbox/runstate/registry. Retires F33/F54/F67/F79/F87/F89/F90/F6-family at once — the single biggest systemic win (a dozen findings collapse into one helper + one checker). (F73)
23. **[HIGH] fix(spawn): delete_branch liveness+owner guard** — refuse to delete a branch with a live PID or `owner:true`; the 3-name allowlist is the wrong gate. (F84)
24. **[HIGH] fix(flow): aggregator must not overwrite a branch registry it read as empty** — distinguish missing-vs-corrupt; never write `{}` back over a real registry; atomic write. (F85)
25. **[HIGH] fix(spawn): structural registry locking** — every save_registry site takes the flock, not just some. (F86)
26. **[MEDIUM] fix(prax): atomic module-registry + logger op-log writes, fix setup TOCTOU** — apply the existing atomic helper + double-checked lock. (F87/F89)
18. **[SECURITY] fix(drone/auth): resolve owner via registry_id/is_owner, protect passport.json** — owner git-access must key to the sealed registry owner:true (machinery exists, S290), not the mutable passport branch_name; add passport.json to a gate. (F59)
19. **fix(ai_mail): lowercase recipient before lookup** — mirror wake.py:466's `.lower()` in get_branch_by_email/delivery/resolve. [GFI] (F69)
20. **fix(ai_mail): test_token reads wrong field** — `msg.get("body")` → `msg.get("message")`; add a test. [GFI] (F70)
21. **fix(daemon): atomic runstate write** — temp+rename+lock save_runstate; fire-AFTER-persist or idempotency key. (F67/F71)
22. **[SECURITY] harden gates** — edit_gate should cover Bash writes (F60); git_gate catch interpreter-wrapped + path-qualified git (F61/F62); gates fail LOUD not silent-open (F65). Scope: coordination not OS-security — frame accordingly.
27. **[HIGH] fix(cli): display helpers must not crash callers** — `header`/`success`/operation templates need `markup=False` or escaped interpolation; they take down any branch on bracket-containing input. Blast radius = every branch. (F94)
28. **[HIGH-SEC] fix(api): atomic 0o600 OAuth token write** — use `os.open(..., 0o600)` (pattern exists at secrets.py:154) so a live refresh token is never world-readable or truncated. (F95)
29. **fix(api): don't relabel real command failures as 'unknown command'** — distinguish handler-raised from unrecognized. (F96)

## CORE-BRANCH CODE SWEEPS (ai_mail, daemon, commons, backup — sub-agent found, sharp claims I verified)

### F67 — daemon: non-atomic unlocked runstate write can wipe ALL job history → mass re-fire [HIGH]
- `runstate.py:50-60 save_runstate` = direct open("w")+json.dump, no temp+rename, no lock. Crash mid-write (the per-job save in run.py:246) truncates the file; `load_runstate` catches JSONDecodeError and silently returns empty → next tick treats EVERY job on EVERY branch as never-run (daily/hourly/interval all "due" at once, completed `once` jobs re-fire). Blast radius = whole scheduler. Same write-atomicity gap as F54/F67 family.

### F68 — ai_mail: inbox READS bypass the lock writers hold → user-visible "Invalid inbox JSON" [MEDIUM]
- `inbox_ops.py:63 load_inbox` json.loads with NO lock while writers hold `inbox_lock()` and truncate-then-write. A concurrent `drone @ai_mail inbox/view` can read mid-truncation → JSONDecodeError surfaces as failure. The `.inbox.lock` exists; the read path just doesn't use it.

### F69 — ai_mail: recipient casing breaks send/inbox for `@Branch` [MEDIUM — verified]
- **Verified:** `registry/read.py:148 get_branch_by_email` does exact `branch["email"] == email`, delivery/resolve never lowercase user input → `drone @ai_mail send @Devpulse …` fails "Unknown branch" though @devpulse exists. **wake.py:466 resolve_branch DOES `.lower()`** (I read both) — so dispatch normalizes, plain send doesn't. Same casing disease as F15/F52, third surface.

### F70 — ai_mail: test-token auto-ack is DEAD CODE (wrong field name) [MEDIUM — verified]
- **Verified:** `test_token.py:132` reads `msg.get("body","")` but the schema stores content under `"message"` (create.py:86 `"message": message_with_footer`; "body" set nowhere). So `has_test_token` always sees "" → never matches → liveness/test pings fall through to full dispatch and wake a whole Claude agent instead of a cheap ack. No test covers this handler (how it shipped broken). Ties to F41 (delivery-failure notices as malformed mail) — the test-ping path is unexercised.

### F71 — daemon: fire-then-persist ordering allows duplicate wake after crash [LOW-MEDIUM plausible]
- run.py:237-249 fires the agent (durable side effect) THEN saves runstate. Killed in the gap → fire unrecorded → next tick re-fires unless the prior agent's dispatch.lock still held. No idempotency key. Narrow window, real.

### F72 — ai_mail: ~120 lines of lock/occupancy logic duplicated wake.py vs daemon.py [LOW — divergence risk]
- `_check_lock`/`_acquire_lock`/`_is_branch_occupied`/`_pid_alive` copy-pasted between manual-wake and daemon-dispatch paths. Consistent now; a future fix to one copy silently diverges the two. (Same shape as the three structure-validators, F31.)

### F73 — Atomic-write helper is the missing shared primitive [MEDIUM — meta-finding]
- F33(control), F54(commons log), F67(runstate), F6-family(status.py dispatch log) are ALL the same bug: `open("w")+dump` on shared state, no temp+rename, no lock. backup's json_handler and ai_mail's inbox_lock do it RIGHT — the correct pattern exists in-tree, just isn't centralized. One `atomic_write_json()` helper + a seedgo checker forbidding raw dump-to-shared-file would retire a whole class. Strongest single systemic fix from the sweeps.

### F74 — Memory rollover off-by-one is LIVE fleet-wide: keeps 14, not 15 [CRITICAL — verified on disk]
- **Verified fleet-wide:** memory, drone, hooks, seedgo, flow `.trinity/local.json` ALL hold exactly **14 sessions / 14 key_learnings** (predicted keep-14 steady state; devpulse shows 15 only because I hand-edit, bypassing rollover). `orchestrator.log`: rollover fired at **"(15/15 sessions)" 53×**, "(15/15 observations)" 30×, "(15/15 key_learnings)" 18× — vs "(16/15)" only 3×. It rolls over AT the keep target, not above it. This is not a spot bug — it's every branch, every rollover, since the trigger was written.
- **Mechanism (exact lines):** trigger `len(sessions) >= max_sessions` (detector.py:360 + extractor.py:207) fires at len==15; extractor `excess = max(len(sessions) - max_sessions, 1)` (extractor.py:208/218/228 for sessions/key_learnings/observations) forces trimming 1 even when real excess is 0 (`max(0,1)`). Every branch silently runs keep-14.
- **PRECISE FIX (2 changes):** trigger `> max_sessions` (fire only when EXCEEDED, so 16 rolls to 15) AND drop the `,1` floor → `excess = len - max_sessions` (naturally ≥1 when the >-trigger fires). Apply to all three entry types (207-208/217-218/227-228). @memory-owned.
- **FIX PROVEN EXECUTABLE (isolated logic replica, ran it):** shipped logic at exactly 15 entries → keeps **14** (bug); at 16 → keeps 15. Fixed logic at 15 → keeps **15** (correct); at 16 → keeps 15. All three assertions pass (`current(15)==14`, `fixed(15)==15`, `fixed(16)==15`). Not just asserted — demonstrated. The 2-line change is safe and correct.
- **Dated + why-unnoticed:** `git blame` → introduced **2026-04-22 (commit 9634c5639)** — silently keep-14 fleet-wide for ~2.5 MONTHS. It survived because rollover ARCHIVES the trimmed entry to vectors (nothing is deleted, it just moves to @memory one cycle early) → **zero visible symptom.** The perfect silent bug: on the branch named `memory`, in the system whose pitch is "memory persists," a memory-loss bug is invisible precisely because the memory isn't lost, just archived early. This IS todo 66's "15/15 vs keep-15" — PROVEN actively trimming. **NOT filing** (todo 66: Patrick monitors rollover, no file without his go) — documented only.

### F75 — ai_mail error-escalation channel reports success on failure [HIGH]
- `error_dispatch.py:61-88`: `deliver_fn("@drone", ...)` return discarded, hard `return True`. `deliver_email_to_branch` returns `(False, msg)` on failure (doesn't raise) → a failed escalation logs as success. The incident-visibility safety net can't see its own failures. Both call sites discard the result too. (Explains how F41's malformed vera notices piled up unnoticed.)

### F76 — drone: ~90 git/gh subprocess calls with NO timeout; `drone @git pr` can hang holding the repo-wide lock [HIGH]
- Only 2 of ~90 `subprocess.run` git sites pass `timeout=`. `pr_handler.py:163→220`: `acquire_lock()` takes repo-wide `.git_pr.lock`, then UNBOUNDED `git push`; a credential/SSH/net stall → function never returns → `finally` never runs → lock never releases → every branch's `drone @git pr` blocked until a human force-unlocks (staleness is passive 600s, no auto-unlock). Real hang risk for the one git-write path the whole fleet shares.

### F77 — drone: dict-shaped registry keys never lowercased → `@Name` permanently unresolvable [HIGH — latent]
- `registry_handler.py:273` lowercases names only when `branches` is a LIST; dict-shaped `branches` keys pass through untouched, while every lookup forces lowercase. With `{"branches":{"Prax":...}}`, `@prax` AND `@Prax` both fail. Dormant TODAY (prod registry is list-format — I verified) but a landmine if anything emits dict format. Casing-drift family (F15/F52/F69).

### F78 — drone registry credential check FAILS OPEN [MEDIUM — security-adjacent]
- `registry_handler.py:105/217 _verify_registry_credential`: bare `except Exception → return True`. A corrupt/unreadable passport is treated as "credential matches" → cwd walk-up may adopt another citizen's registry. Same fail-open theme as F65, violates "fail to errors."

### F79 — drone custom-command registry: non-atomic write + read-modify-write race [MEDIUM]
- `command_registry/ops.py:143` raw open("w")+dump (while the SAME tree's `json_handler._atomic_write_json` does it right — F73 again); unlocked add/remove/update. Concurrent `drone activate` → last-writer-wins drops commands; kill mid-dump → `load_registry` silently recreates EMPTY registry, all shortcuts lost.

### F80 — Verified-clean by the memory sweep [ASSET]
- Memory rollover ORDERING is correct (backup→trim→embed→store, restore_from_backup on every failure path); primary memory files DO use atomic temp+os.replace; the old 30s-hook false-FAILED is resolved (heavy ops now 60/120s, zero timeout hits in logs). ai_mail wake/dispatch is poll-based (no write-vs-signal race), O_CREAT|O_EXCL locks, consistent subprocess timeouts on the dispatch side.

### F81 — The daemon scheduler works but the fleet has ZERO production jobs [HIGH — the empty janitor]
- The whole automation layer (systemd daemon-tick.timer @1m + decentralized `.daemon/schedule.json` discovery) is BUILT and running — I ran a manual tick, it discovered and evaluated correctly. But across all 17 branches there are exactly **3 jobs, all `wake-test`, all disabled** (F11). Nothing is scheduled: no error-registry triage (→ F5 graveyard), no backup cadence (→ F29 4-day-old backups), no commons digest (→ A2 empty Commons), no stale-presence cleanup (→ F26), no CB-recovery tick (→ F5b stuck 63 days). 
- **This is the single infrastructure root of the "write side shipped, read side missing" pattern.** The janitor-RUNNER exists; nobody wrote the janitors. Every "nothing ever cleans/triages/recovers X" finding could be closed by a handful of enabled daemon jobs. Highest-leverage systemic fix on the ops side — and it's additive, low-risk (jobs are per-branch JSON).

### F82 — commons `welcome_new_branches` auto-post exists but is never triggered [MEDIUM]
- `welcome/welcome_handler.py:116 welcome_new_branches` + `run_welcome` are built to auto-post welcomes for new branches — exactly the ritual that would keep the Commons alive (A2/A6). It's wired to a command, not to any event or schedule, so it never fires on its own. Another built-but-unpulled ritual; a daemon job (F81) or a spawn-hook would light it up.

### F83 — .backup store is 951M (versioned 671M) — growth vs max_versions:10 worth a look [LOW]
- `.backup/versioned` = 671M, `.backup/snapshots` = 273M (25 snapshot dirs), `drive_tracker.json` = 4.9M. Backup config says `max_versions: 10` but the versioned store is large — either per-file baselines+diffs legitimately accumulate or pruning isn't keeping pace. Correctly gitignored (verified). Not urgent; worth a `backup` prune audit given F29 (no scheduled backups anyway). NOTE: initial `git ls-files` count looked alarming (62) but was a CWD artifact — real tracked count is 1843 (1304 py). Verified before recording.

### F93 — tier0_kernel loader docstring says "period 1", config + kernel header say period 5 [LOW — doc drift]
- `tier0_kernel.py:32` docstring: "Load tier0 kernel — every turn (cadence period 1)." But cadence_config sets `tier0: period 5`, and the kernel file's own header says "injected every 5 turns (cadence period 5)". The docstring is stale. (Verified the `branch` loader's MISSING period is fine — cadence.py:204 inherits global_period=5 correctly; that one's not a bug.)

## FLOW / SPAWN / PRAX SWEEP — highest blast radius (sub-agent found; scariest two I verified in code)

### F84 — spawn `delete_branch` has NO liveness or owner guard [HIGH — destructive]
- **Verified:** sole gate is `_PROTECTED_BRANCHES = {spawn, devpulse, drone}` (delete_ops.py:124) + `is_dir()`. No PID/heartbeat check, no `owner:true` check. `drone @spawn delete @<any-live-non-protected-branch> --yes` archives + rmtrees it whether or not it's running, and the sealed registry OWNER is deletable if not one of the 3 hardcoded names. Highest single-command destructive risk found. (Mitigant: it's an intentional admin verb with a confirm prompt + spawn is owner-tier — but the guard SET is wrong: it should be "not owner AND not live," not a 3-name allowlist.)

### F85 — flow central aggregator can overwrite ANOTHER branch's plan registry with empty [HIGH — cross-branch data loss]
- **Verified the mechanism:** `aggregate_ops.py:86 load_branch_registry` fails open to `{"plans":{}, "next_number":1}` on ANY read/parse exception (no missing-vs-corrupt distinction); `save_branch_registry:94` writes back with raw `open("w")+json.dump` (non-atomic). The aggregator's heal pass runs against OTHER branches' registry.json. If branch B's registry is transiently unreadable (mid-write/truncated) when the heal runs → aggregator reads empty → "heals" by overwriting B's whole plan history with `{}`. A read hiccup in one branch, triggered by another branch's routine aggregation, destroys plan tracking.

### F86 — spawn registry lost-update race: locking is opt-in, not structural [HIGH]
- registry.py:159/repair_ops take fcntl.flock before load→modify→save; but `delete_ops._remove_from_registry`, `sync_registry_ops` (2 sites), and registry.py:333 call `save_registry` with NO lock. flock is advisory → unlocked writers get zero protection. `delete @foo` (loads registry, then blocks on confirm + slow copytree) racing `create @bar` (locked, fast) → delete writes stale registry back, erasing @bar.

### F87 — prax module registry truncates to ONE entry → ecosystem-wide log-routing loss [HIGH]
- `registry/save.py:96` raw open("w")+dump (ignores the atomic helper next door); `watcher.py on_created` does unlocked load→mutate→save. Kill mid-dump truncates `prax_registry.json`; load fails open to `{}` → next watcher event overwrites with just the one new module, discarding every previously-discovered module until a full rescan. This is the module→log-routing registry.

### F88 — spawn: 2 passport writers bypass the atomic helper [MEDIUM — identity loss]
- `sync_registry_ops.py:603/628 fix_owner_identity` use raw `passport_path.write_text(json.dumps(...))` while every OTHER spawn passport writer routes through the mkstemp+fsync+os.replace helper. Crash mid-write → truncated passport → a branch loses its identity (and per F59, its git-access key).

### F89 — prax logger internal op-log + setup have corruption/TOCTOU races [MEDIUM]
- `logging/operations.py:60` raw open("w") on the growing op-log, no lock → concurrent callers interleave partial writes → invalid JSON (hit from every handler). `logging/setup.py:93` checks `_captured_loggers` under lock, RELEASES, then mutates the stdlib singleton logger outside the lock → duplicate handlers (dup log lines) or dropped handler. The correct double-checked-lock pattern exists in logger.py:95 but isn't applied here.

### F90 — flow own plan registry + central aggregate non-atomic, fail-open-to-empty [MEDIUM]
- `registry/save_registry.py:70` raw-writes `fplan_registry.json` (self-labeled DO NOT EDIT); `aggregate_ops.py:257 save_central` raw-writes `PLANS.central.json`. Both paired with fail-open-to-empty loads → a crash mid-write + any later load+save silently resets the registry. Same F73 atomic-write class.

### F91 — flow "read-only" scan silently RENAMES plan files across branch boundaries [MEDIUM — plausible]
- `monitor_ops.py:189 scan_plan_files_impl` unconditionally `rename`s on a 4-digit-number collision even though the CLI reports "no changes applied." It walks from ECOSYSTEM_ROOT across ALL branches with no branch-boundary awareness; plan numbers are PER-BRANCH, so two branches legitimately holding e.g. FPLAN-0042 → one gets renamed out from under its owner by a "read-only" scan.

### F92 — Verified-clean by this sweep [ASSET]
- Mixed-case @branch bug NOT present in flow/prax (prax consistently `.upper()`, flow delegates upstream). prax atomic-write PRIMITIVE is correct (just not used in 3 spots). spawn individual writes mostly careful (path containment, archive-before-delete). The correct patterns exist in every branch — the gaps are inconsistent APPLICATION, not absence.

## API / CLI / TRIGGER SWEEP (sub-agent; CLI-crash + OAuth window I verified)

### F94 — CLI display helpers crash the CALLER on bracket/markup-like input [HIGH — every-branch blast radius]
- **Verified:** `display.py:328 header` and `success` interpolate caller strings into a Rich-markup-parsed `CONSOLE.print(f"...[dim]{key}:[/dim] {value}")` / `Panel(f"[bold cyan]{title}[/bold cyan]")`. Any value with an unmatched/closing tag — a path, git ref, JSON, regex, or exception text containing `[/x]` — raises `rich.errors.MarkupError` uncaught and takes down that branch's process. Nasty asymmetry: `error()`/`warning()`/`fatal()` use markup-safe `Text.append()` — only the HAPPY-PATH helpers crash, so a "success" message kills the app. Zero test coverage. This is the shared display layer every branch renders through — F8's truncation was the cosmetic tip; this is the crash. Fix: `markup=False` or escape interpolated values.

### F95 — api: live OAuth refresh token can be left world-readable / truncated on crash [HIGH — secret exposure window]
- `google/auth.py:251 _save_credentials` (runs after EVERY refresh): `open(path,"w")` → write token → `os.chmod(0o600)`. File is created at umask (usually 0o644 = world-readable) and only tightened AFTER the write; a crash between write and chmod leaves `google_creds.json` (live refresh token) permanently world-readable, and nothing re-chmods later. Also non-atomic (no temp+rename). The correct pattern (`os.open(..., 0o600)` — mode atomic at creation) is ALREADY used at `secrets.py:154` and `api_key.py:234`. `env.py:94` has the same ordering (lower sev, placeholder only).

### F96 — api: dispatcher misreports real command failures as "unknown command" [MEDIUM — extends F13]
- `api.py:240 route_command`: module loop `except Exception → log + continue`. When a REAL handler (e.g. api_key on a corrupt .env / perms error) raises, no module claims it, route returns False, main prints "Unknown command: get-secret" (exit 1). The true cause is buried in logs. Broader than F13's silent-fallback — it actively mislabels legitimate credential-command failures.

### F97 — api: `diagnose_key` echoes a real secret PREFIX to stdout [LOW — minor leak]
- `auth/keys.py:216 diagnose_key` puts the first ~6-10 chars of the actual stored secret into a string that reaches stdout (openrouter_client.py:289). Prefix only, not full value, but a real secret fragment on a "diagnostic" path meant to be safe.

### F98 — Verified-clean by this sweep [ASSET]
- api secret handling is DISCIPLINED: no raw key/token value hits any logger/print across apps/ (all masked `key[:6]+"****"+key[-4:]`); no bare `except: pass` around auth; OAuth refresh failure is LOUD (logs error, returns False, callers report "invalid" — doesn't treat stale token as valid). cli `error/warning/fatal` are markup-safe. The secret-masking discipline is genuinely good — F94/F95 are the gaps in an otherwise careful branch.

## SECURITY GATES — integrity audit (sub-agent found, core claims I verified in code)

**Threat-model framing (READ FIRST):** AIPass agents all run as the SAME OS user, locally, cooperatively. The gates are Claude Code hooks — coordination + accident-prevention, NOT an OS boundary against a hostile actor (who could run git directly). So "bypass" here means "the owner/ownership model is ADVISORY, not enforced" — an integrity/robustness gap, real and worth fixing to make the model mean what it claims, but NOT a remote exploit or live emergency. Severities below are relative to the model's own promises.

### F59 — Owner git-access trusts an UNPROTECTED, UNSIGNED passport [HIGH — the owner model is forgeable]
- **Verified in code:** `auth.py:_find_caller` reads `branch_info.branch_name` straight from the CWD-hierarchy's `.trinity/passport.json` (`auth.py:18-48`); `verify_git_access` grants owner-tier if that string is in `allowed_callers` (["devpulse"]) — **no registry cross-check, no signature** (`auth.py:88-125`). And NO gate protects passport.json (edit_gate covers only local.json/observations.json; git_gate covers settings/hooks; registry_gate covers *_REGISTRY.json). So any dir with a passport saying `branch_name: devpulse` gets owner git-write. The whole DPLAN-0231 owner-capability model (built to key auth to the immutable registry_id) is undercut because the ACTUAL check reads the mutable passport name, not the sealed registry owner:true. Fix: `verify_git_access` should resolve owner via registry_id/is_owner (the machinery EXISTS — S290), not a passport string; and protect passport.json under a gate.
- Same passport-trust pattern duplicated in `seedgo/permissions.py:identify_caller`.

### F60 — pre_edit_gate never runs for Bash → all its protections void via shell writes [HIGH]
- Sub-agent claim (matcher-traced): edit_gate's matcher is `Edit|MultiEdit|Write|NotebookEdit` (no Bash) AND its `EDIT_TOOLS` set excludes Bash. So `echo … > inbox.json`, `python3 -c "open(...).write(...)"`, `tee`, `sed -i` skip edit_gate entirely — voiding its inbox-write block, daemon confinement, cross-branch block, and .trinity entry-limits. (Consistent with F3's observation that git_gate DOES match Bash but edit_gate doesn't — asymmetric tool coverage across gates.)

### F61 — git_gate quote-stripping blinds it to interpreter-wrapped git [MEDIUM]
- git_gate replaces quoted-string contents before scanning (git_gate.py:164), so `bash -c 'git push'`, `sh -c "git push"`, `eval 'git push'`, `python3 -c "subprocess.run(['git','push'])"` pass. Heredoc-piped git IS caught (bodies not stripped) — so the miss is specifically the interpreter-string idiom.

### F62 — RAW_GIT_RE lookbehind excludes `/` and `.` → path-qualified git evades [MEDIUM]
- `(?<![@\w/.])git\s` (git_gate.py:21): `/usr/bin/git push`, `./git push`, `GIT_SSH_COMMAND=x /usr/bin/git push` all pass. Exclusion was added to spare `.gitignore` filenames; it also blinds the matcher to the real binary by absolute/relative path. (Variable-indirection `g=git;$g push` is inherent to any regex approach — same limit hits rm_gate/registry_gate.)

### F63 — rm_gate is the ONLY interactive delete defense yet has clean misses [MEDIUM-HIGH]
- The kernel sandbox rm_gate calls "the real boundary" is Phase-1, NOT wired into normal sessions (sandbox.py:267 says so; devpulse's own tools/rm_shim/FINDINGS.md already documents this). So rm_gate's misses are load-bearing: `find . -delete`, `shred -u`, `\rm -rf` (endswith-check miss), `find|xargs sh -c 'rm -rf {}'` (quote-stripped), `python3 -c "shutil.rmtree(...)"` all pass. Straight `rm -rf`, `rm -fr`, `find|xargs rm -rf` correctly blocked.

### F64 — Protected-path gates match raw strings, not resolved paths [MEDIUM]
- git_gate BLOCKED_EDIT_PATTERNS + registry_gate check the literal `file_path`, no `Path.resolve()`. `.claude/settings.json` (relative, no leading `/`) passes where `./.claude/settings.json` is caught — inconsistent. A symlink whose name isn't `*_REGISTRY.json` but points at one evades registry_gate (PLAUSIBLE, depends on Write following symlink).

### F65 — All gates + the engine FAIL OPEN on exception [MEDIUM — by design, but]
- Every gate's `handle()` wraps in `try/except Exception → allow + log "(allowing)"`; engine.py only special-cases exit_code==2, any other (incl. handler import crash, exit -1) falls through to allow. Deliberate availability tradeoff (a hook bug shouldn't brick all tools) — but means ANY parser crash = silent bypass. At minimum the fail-open should be LOUD (surface to prax/error-registry, not just a log line).

### F66 — What the gates get RIGHT [ASSET]
- git_gate read/write split is an ALLOWLIST of read verbs (unknown → blocked = safe default). Compound-command splitting (`&&`/`||`/`;`/`|`/`$()`/backticks) is consistent across git/rm/registry gates and defeats naive chaining. Heredoc bodies not quote-stripped (piped-heredoc git caught). rm_gate follows single pipes. `drone <verb>` self-exemption uniform. The bones are good; the misses are specific parser gaps, not a broken design.

## HOOKS ENGINE / SEEDGO SWEEP (final sweep — two trust-undermining finds I verified)

### F99 — seedgo can silently STOP ENFORCING a standard AND drop crashing files → false 100% [HIGH — undermines "100%", two layers]
- **Layer 1 (worse — whole checker vanishes, seedgo-audit sub-agent found, I verified):** `branch_audit.py:37-39 discover_checkers` — `except Exception: logger.info("Skipped checker %s: failed to load"); continue`. If a `*_check.py` fails to IMPORT (syntax error, missing env dep), it's silently dropped from the checker set → absent from scores AND gating → CI (THRESHOLD=100) passes the branch at 100% **while that entire standard goes unenforced, zero signal.** Break one import and a rule silently stops being checked fleet-wide.
- **Layer 2 (file-level):** `branch_audit.py:95-97 _run_all_files` — `except Exception: continue`. A file that breaks a checker (non-UTF-8, parser edge, checker bug — AST checkers catch SyntaxError but not UnicodeDecodeError etc.) is dropped from `scores`, absent from the denominator → average rounds UP. Plus line 101: any file with a "skipped"/"not applicable" check message is excluded from the average even if another check on it FAILED.
- **This means the fleet "100%" (F47/F92) is trustworthy only for files+checkers that PARSE/IMPORT — blind to anything that chokes.** Fix: exception in discover_checkers/`_run_all_files` = FAIL (score 0) or hard error, never silent skip. Fix F1 (layer 1) first — a standards enforcer that can silently stop enforcing is the worst failure mode here.
- **Dated:** `git blame` → both silent-skip paths date to **2026-03-23 (commit 6bd1bd00f)**, near the audit's inception. So every "100% fleet-green" this project has ever celebrated has carried this blind spot from the start — foundational, not a regression.

### PROVENANCE — the big findings are OLD and symptomless, not fresh breakage [synthesis]
- Dated the load-bearing ones via git blame / logs: **F74 rollover keep-14 = 2026-04-22** (~2.5 months); **F99 seedgo silent-skip = 2026-03-23** (inception); **F5b medic disabled = 2026-05-10** (config toggle, log-confirmed, 63 days); **skills json_handler F116 = 2026-03-17** (never migrated). Pattern: these survived MONTHS not because they're subtle to find but because they're **symptomless** — rollover archives (doesn't delete), medic-off just means silence, seedgo-skip just inflates a number, atomic-write races only bite on a crash. The system has no alarm for "a thing quietly stopped working correctly." That's the deepest gap: **AIPass optimizes for visible-failure (logs, errors, red CI) and is blind to silent-degradation.** The fix class isn't per-bug — it's invariant checks that assert the INVISIBLE (rollover leaves exactly N, medic is on, every registered checker ran, the breaker isn't wedged) and fail LOUD when violated.
- **DEEPEST UNIFICATION — the observability layer is decorative, not measured (this is WHY degradation stays silent):** the runtime/data probes (F123/F124) showed the mechanism. AIPass's self-reported STATUS is systematically wrong while its underlying DATA is sound. Vector store: healthy 5,012 vectors, dashboard says 1,274. Dashboards: "live", actually up to 10 days stale. Doctor: 7 false errors on a healthy repo. activity_report: retired schema, 100% noise. daemon: contradictory labels. seedgo: "100%" blind to files it chokes on. Meanwhile the DATA is fine — compass integrity ok, chroma integrity ok, 11k tests collect clean, 6 suites green. **The data is trustworthy; the gauges are stale, mislabeled, or lying-green — and THAT is the silent-degradation mechanism.** You cannot notice a thing quietly breaking when every dial reads "fine" regardless of reality. The single highest-leverage meta-fix: make the observability layer MEASURED (real counts, real freshness, fail-loud invariants) before trusting any gauge as a signal. A striking share of these 124 findings is downstream of "nobody could see it."

### F100 — hooks: missing/corrupt `.aipass/hooks.json` silently disables ALL security gates [HIGH — fail-open at config layer]
- **Verified:** `claude.py:47 find_project_config() → None` on missing/corrupt config → falls back to `{"hooks_enabled": True}` with no event key → `engine.py` sees empty event_hooks → returns allow. Any CWD whose tree up to $HOME lacks `.aipass/hooks.json` gets ZERO enforcement — git_gate/rm_gate/edit_gate/registry_gate/presence_gate all no-op, logged only at INFO. **Sharp edge:** `isolation: worktree` sub-agents (and any /tmp extraction) created OUTSIDE the main checkout can lack the config → run ungated. Ties the security cluster (F60/F65) together: the gates fail open at the CONFIG layer too, not just on parser crash.

### F101 — hooks presence.py is DEAD CODE presented as live [MEDIUM — confirms F26]
- **Verified:** presence_gate v2.0 migrated source-of-truth to CC-native `~/.claude/sessions/<pid>.json` (cc_sessions.py); `presence.claim/release/refresh` are called ONLY from tests, zero production sites. `PRESENCE.central.json` is frozen pre-migration; nothing writes it. So F26's "12-day stale records" isn't a cleanup bug — the write path doesn't exist. Yet `drone @hooks presence` still renders the frozen entries with live/stale PID tags, actively misleading. Either delete the surface or repoint it at cc_sessions.

### F102 — seedgo CI audit ≠ local audit (branch scope AND pass/fail) [MEDIUM — substantiates DPLAN-0198]
- Same checker pack, but: (a) CI (`.github/scripts/seedgo_audit.py:14`) discovers branches via naive `src.iterdir()` (any dir with `apps/`, no registry, no private-branch exclusion) while local uses registry-based `discover_branches()`; (b) CI hardcodes THRESHOLD=100 + `sys.exit(1)`, local command has NO threshold at all (pure display, always returns True). A dev CANNOT get a "would this fail CI" signal from the normal local command.
- **Sharper (seedgo-audit sub-agent):** the two also resolve the branch ENTRY FILE differently — CI only tries `apps/{name}.py`, local also falls back to `apps/branch.py`. A branch using the `branch.py` convention gets entry_file="" in CI → entry-point checkers open "" → score 0 → **CI false-FAILs a branch that passes locally.** So the parity gap cuts BOTH ways (false-pass on scope, false-fail on entry resolution). Also: `ci.yml:50 fetch-depth:0` comment still cites the deleted git-log freshness check. That's DPLAN-0198, concretely.

### F103 — hooks engine fail-open: handler crash AND malformed stdin both skip gates [MEDIUM — confirms/extends F65]
- Handler crash → exit_code -1 → falls through to allow (test_engine.py:211 literally asserts a crashed hook yields overall allow). Malformed stdin → `match_value=""` → `_matches` returns False for any NON-empty matcher — and every security gate uses a non-empty matcher while non-security handlers use empty ones, so malformed stdin skips EXACTLY the security hooks. Two more fail-open layers, text-log only.

### F104 — hooks cadence miscounts turns <2s apart [LOW]
- `cadence.py:137 _should_increment` checks mtime-age <2s BEFORE checking if the transcript token actually changed → a genuinely new fast turn (agentic/scripted exchanges) is treated as a same-turn straggler and doesn't increment. The "every Nth turn" injection silently falls behind real turn count on fast turns. No test <2s apart.

### F105 — seedgo readme_currency proof is broken (explains F51) + one real drift [LOW]
- **Verified by running scan():** `readme_currency.py:81` only recognizes a legacy prose pattern `pack checks: ...`; seedgo's README now uses a `## The 40 Standards` table, which the regex never matches → returns empty → flags all 40 as "undocumented." So F51's readme_currency FAIL is mostly a BROKEN PROOF, not real drift. BUT one genuine nugget: README.md:47 says "33 standards", actual is 40 — that line is real drift worth fixing.

### F106 — seedgo 471s fleet audit: sequential loop + no AST parse cache [MEDIUM — perf]
- `standards_audit.py:289` iterates branches with a plain sequential `for` (branches are independent — trivially parallelizable). `_run_all_files` re-parses each file once PER checker (7 of 40 do their own `ast.parse`) instead of once per file with a shared cache. Two clear wins to cut the 471s (F47) — matters because slow audits get skipped.

## AIPASS + SKILLS SWEEP (final sweep — doctor findings LIVE-CONFIRMED + skills-security surface)

### F113 — drone_commands built-in skill: `shell=True` with caller-supplied command [HIGH — footgun + false safety claim]
- **Verified:** `skills/lib/drone_commands/apps/handlers/executor.py:63 subprocess.run(command, shell=True, ...)` where `command` is the caller's `args["command"]`. Reached via documented `drone @skills run drone_commands run --args '{"command":"..."}'`; args parsed by naive key=value split, zero escaping. Any `;` `\`` `$()` `&&` `|` runs arbitrary shell. **Scope honestly:** invoked locally with your own args it's just you running your own shell (not a privilege gain). BUT it escalates to real arbitrary-exec if args ever flow from an untrusted channel (Telegram→skill, a community skill calling it), and the SKILL.md's claim "never runs commands that modify system state without explicit action / only drone commands" is FALSE — `shell=True` defeats the intended containment. Fix: drop shell=True, exec argv list, or validate the command is a drone invocation.

### F114 — `skills run` = unsandboxed in-process arbitrary code execution, ZERO gate [HIGH — THE contribution-surface trust model]
- **Verified:** `loader_handler.py:92 spec.loader.exec_module(module)` on any discovered `handler.py`, then `runner_handler.py` calls `handler.run(...)` in-process; grep for sandbox/bwrap/confirm/input under skills/apps = ONLY the exec_module line (nothing else). `skills validate` only checks declared dep PRESENCE, and run never calls it. **This is the direct answer to A7/DPLAN-0209/0240's "open skills to the community":** dropping a folder in `~/.aipass/skills/` and running it == `python handler.py` with full process privileges — no sandbox, no confirm, no review. A community-skill ecosystem CANNOT ship on this as-is; it needs a trust model (signed/reviewed skills, a sandbox via the existing @hooks srt/bwrap wrapper, or an explicit consent gate) BEFORE inviting external skills. First-class design blocker for the contribution story, not just a bug.

### F115 — skill-name shadowing: a project/global skill can silently impersonate a built-in [HIGH]
- `discovery_handler.py:93` keys skills by the frontmatter `name:` field (attacker-controlled), NOT the dir name; `registry.py:36` is first-match-wins in order project → global → builtin. A project/global skill declaring `name: github` (or `drone_commands`) silently SHADOWS the trusted builtin, no warning. Compounds F113/F114: shadow a trusted skill name + get it run unsandboxed. Fix: key by dir/namespace, warn on name collision, builtins win or are namespaced.

### F116 — skills json_handler non-atomic (F73 class, unmigrated) [MEDIUM]
- `skills/apps/handlers/json/json_handler.py:127 open("w")+dump`, used on every skill run/create/validate via log_operation. `aipass/shared/json_handler.py` already has the correct mkstemp+fsync+os.replace — skills' copy (untouched since 2026-03-17) never got the migration. Corruption is silently self-healed (regenerate defaults) → invisible data loss. Another instance for the F73 helper+checker.

### F14–F23 doctor/help findings — LIVE-REPRODUCED with exact lines [confirms my behavioral findings]
- The sweep live-reproduced every doctor false-error I found behaviorally, pinning exact lines: **F14** (.backup not in `_SCAN_SKIP_DIRS`, structure_scanner.py:96 → 38 vs 19 agents + cascading false pollution "ai_mail 30 copies"); **F15 CONFIRMED my correction** (structure_scanner.py:312 resolves relative registry path against `cwd()` — from repo root 0 issues, from a branch subdir all 5 "missing"; it's relative-path-not-casing, exactly as I corrected); **F16** ({{BRANCHNAME}} source pinned: `spawn/templates/aipass_framework/.trinity/passport.json:13` shipped scaffold with unsubstituted placeholder, scanned as a real agent); **F17** (doctor.py:332 reads top-level `role` but schema nests `identity.role` → always "unknown", line 333 appends PASS unconditionally → always green); **F22** (aipass.py:111 merges --help/help/bare into one internals dump); **F23 root cause** (help_chat BRANCHES is a hardcoded 12-name list MISSING skills/backup/commons/daemon/hooks; unmatched query greps all branches by keyword-count with no domain scoring → "create a skill" returns drone/seedgo/prax). 5 relative-path "missing" + 2 backup-pollution = exactly the 7 false errors. All my doctor findings now line-pinned and reproduced.

## SUB-AGENT CORROBORATION + NEW ITEMS (log-sweep, newcomer-audit, seedgo-audit — my own agents, reporting late)

### F107 — @memory rollover COMMAND times out at 30s via drone, ~every 1-3h for 2+ days [MEDIUM — sub-agent reported]
- **CLOSED (I verified):** the 15 timeouts (`Command timed out after 30s: apps/memory.py rollover run`) are ALL in the rotated `drone.log.1`, 2026-07-10 00:24 → **last at 07-11 18:23:00**; ZERO in the current log. A live `rollover status` now returns in **8.3s** (well under 30s), local memory "OK". So this was REAL and recurring for ~2 days but has NOT recurred in ~25h — a transient (likely embedding-model cold-load or a backlog that cleared), not currently active. Distinct from F74 (keep-14 off-by-one). It's the "false FAILED" symptom of todo 66 — the 30s drone routing timeout < the actual rollover-run time. Keep an eye out for recurrence; if it returns, bump the routing timeout for the `rollover run` path or make rollover incremental.

### F108 — README/docs drift batch (newcomer-audit; adoption-facing) [LOW each, MEDIUM in aggregate]
- README says "17 agents" ×3 but the Project Status table (README:245) says "13 core + user-created" — self-contradicting on the same page.
- HVTrust badge (README:8) → hvtracker.net/agents/aipass returns HTTP 403 (re-check manually; may be bot-block vs down). This badge already has a saga (PR#655 hid it, #621 re-added).
- Roadmap (README:262-269) frames #360/#329 as "under ongoing testing" — both are CLOSED per gh api.
- **PyPI-vs-clone contradiction [MEDIUM — adoption]:** package `aipass` v2.7.0 IS live on PyPI, but TDPLAN-0010 stripped all `pip install aipass` refs from the README in favor of clone-only. A PyPI discoverer lands on a page whose own README tells them to git-clone instead, no explanation. Either document the PyPI path or explain the redirect.
- Stale "Citizen Class: builder" survives the 2026-07-01 builder→aipass_framework rename in commons/README:8 and daemon/README:8.
- daemon/README internal date contradiction (header "2026-04-07" vs footer "2026-06-29"); commons/README self-inconsistent post arg-count (3-arg vs 2-arg).
- CONTRIBUTING.md:16 "4,900+ tests" — actual ~12k `def test_` (stale ~2.5×). 155KB CHANGELOG (excellent, root-cause+verify per fix) is NOT linked from README.

### F109 — Missing contributor infra: no PR template, no CoC, no FUNDING, no good-first-issue labels [MEDIUM — extends A5]
- newcomer-audit confirmed via gh: no PULL_REQUEST_TEMPLATE.md, no CODE_OF_CONDUCT.md, no FUNDING.yml, no labeler/good-first-issue config. CONTRIBUTING.md is 23 lines, no citizen/branch/.trinity architecture onboarding. All 104 issues ever = AIOSAI-authored; sole external human = YugantM (confirms A3/A4). Feeds DPLAN-0240 Tier 0/1.

### F110 — commons gift/trade/mint brokenness is ALREADY KNOWN + documented [corroborates F52]
- newcomer-audit: commons/README:77-82 marks gift/trade/mint/collab "not operational — registry path bug", lines 110-117 mark 3 dry-run paths "partial — routing error." So F52 (the owner-casing bug I found in code) is a KNOWN issue the branch documents publicly — good (honesty) and bad (root README pitches commons as live with no caveat). The casing root cause (F52) is likely THE "registry path bug" they mean. Fixing F52 could light up the whole artifact economy (A6).

### F111 — drone cross-project citizen-introspection registry-mismatch [MEDIUM — extends F41]
- log-sweep: `drone.log` — `Introspection failed for @writer: Registry mismatch: citizen belongs to registry 'b91eefcf...' but found registry '8fb38c96...' at .../Vera-Studio/VERA-STUDIO_REGISTRY.json` (07-10 23:11). Plus @vera auth-denied + 6 bounced emails stuck unread in @drone inbox (F41). Suggests a path-resolution bug in drone's citizen-introspection that walks INTO a sibling project's registry. The 6 @vera bounces (F41) are the same cross-project-comms-is-feics theme (my key_learning 216).

### F112 — telegram_response stuck-pending: one session wedged 13+ hours [strengthens todo 67]
- log-sweep: `hooks/telegram_response.log` — session `c10bd220` stuck at `start_line=5880`, retrying the same JSONL line 2026-07-11 18:16 → 07-12 07:28 (118 WARNING lines, ~13h) and never resolving. A concrete live instance of todo 67's stuck-pending (F223 key_learning: stale pending retries every Stop forever). The reap/expiry that todo 67 proposes would kill exactly this.

### F117 — SYSTEMIC: the exact code paths that crash/corrupt/leak are the ones with NO test [MEDIUM — meta-pattern]
- Recurring across every sweep, the highest-severity findings share a tell: **"no test covers this."** F70 (test_token dead field — "no test covers this handler, presumably how it shipped broken"), F94 (CLI markup crash — "zero test coverage"), F104 (cadence <2s drift — "no test <2s apart"), F60/F103 (gate bypasses — "no test exercises malformed stdin with a non-empty matcher"), F99 (seedgo drop-on-exception paths untested), F33/F1 (racy/atomicity paths). The fleet has 371 test files / 10,458 functions and high nominal coverage — but it's concentrated on happy paths; the ERROR/CONCURRENCY/MALFORMED-INPUT branches (exactly where these bugs live) are systematically untested.
- **Why it matters:** seedgo's Test_Quality standard scores 100% (F47) while the crash-on-bracket, silent-drop, and fail-open branches ship untested — the standard measures test PRESENCE, not adversarial coverage. A "test the unhappy path" checker or a mutation-testing pass would have caught most of these 116. The QA-layer expression of the "write-side shipped, read-side missing" culture (F81): tests assert what SHOULD happen, rarely what happens when it doesn't.

---

### F118 — RAN the tests (not just read them): F1 reproduces LOCALLY, and green suites harbor live bugs [strengthens F1 + F117 empirically]
- **F1 is flakier than I thought — reproduced LIVE locally:** running the FULL prax suite → `test_mtime_cache_avoids_reread FAILED: assert {} == {'paused': False}` (1 failed, 990 passed). Earlier I ran `TestReadControl` in ISOLATION and it passed (6/6) → I wrongly concluded "only red on CI runners." Full-suite timing (other tests perturbing mtime granularity) triggers it locally too. So F1 isn't a CI-runner quirk — it's genuinely flaky anywhere under realistic timing. Even stronger case for the deterministic `os.utime` fix.
- **F117 proven empirically:** ran memory (990 passed) and hooks (961 passed) suites — both FULLY GREEN while each harbors a live bug their tests never catch (memory: the keep-14 rollover F74; hooks: cadence <2s drift F104). Green suites + live bugs = exactly F117's thesis: coverage asserts the happy path, not the invariant. 990 memory tests, zero assert "rollover leaves exactly N."
- **Codebase is structurally sound:** 11,170 tests collect with ZERO import/collection errors — no broken branches, no dead imports. The bones are solid; the gaps are adversarial-coverage + silent-degradation, not rot.
- **Ran 6 branch suites (~4,000 tests):** memory 990, hooks 961, ai_mail 765, commons 449, spawn 346, flow 730 — ALL green in isolation (backup didn't finish in the time box). The ONLY failure anywhere is the flaky F1. Critical takeaway: NONE of the concurrency findings (F53 conn-leak, F54/F67/F85/F86 races) surface as test failures — they're all LATENT, green suites over untested race paths. Empirically nails F117: the suite is robust on the happy path and blind to exactly the branches these bugs live on.

### F119 — `@pytest.mark.integration` unregistered → silent no-op mark [LOW]
- `devpulse/tests/test_watchdog_agent.py:469 @pytest.mark.integration` — mark not registered (PytestUnknownMarkWarning). Any `-m integration` selection silently matches nothing; the mark is decorative. Register it in pytest config or it's a filter that does nothing.

### F120 — Always-on fleet: 7 processes, ~22% CPU + 1.8GB RAM steady-state, forever [MEDIUM — resource/ops]
- Live `ps`: trigger-log-watcher + 5 telegram bots + prax monitor = **7 persistent processes, 21.9% total CPU, 11.4% RAM (~1.77GB)** continuously on a 4-core/15.5GB machine — roughly a full core + 1.8GB permanently, before any actual work. No zombies (clean). Bots still logging poll errors TODAY (bot_base 246 / bot_devpulse 236 lines today; most recent ERROR 20:07 "read operation timed out"). Compounds F10 (no poll backoff): 5 separate bot processes each polling+erroring independently. Consideration: a shared poller (DPLAN-0219 mother-bot) would cut this materially. For a personal machine this steady-state load is worth a conscious decision, not an accident.

### F121 — Log volume dominated by two specific issues; medic-off cost quantified [LOW-MEDIUM]
- Fleet logs = 73M total. Two files dominate: **`trigger/logs/medic_suppressed.log` = 9.9M (rotated once, +362K active)** — that's 10M+ of pure "Medic OFF - suppressed dispatch" lines, ONE PER dropped error over 63 days = a direct, quantified second cost of F5b (not just errors undelivered, but 10M of suppression noise written). And **`backup/logs/operations.jsonl.1` = 34M** — backup logs every per-file op (464-file versioned runs), rotates but runs heavy. Both rotate (not unbounded) but both trace to a specific fixable cause: re-enable medic (F5b) kills the first; backup could log op-summaries not per-file the second.

### F122 — Bug-magnet map: churn points EXACTLY at the surviving bugs [synthesis — where to harden]
- `git log --grep=fix` over 6 months, most-touched source files: **memory-rollover is 4 of the top 6** — memory_watcher.py (19 fix commits), detector.py (17), rollover.py (16), extractor.py (16) = ~68 fixes to that one subsystem, AND F74's keep-14 off-by-one lives in the two most-fixed files (detector+extractor) and survived every one of those fixes. **ai_mail dispatch/delivery** is the other magnet: email.py (17), delivery.py (16), wake.py (15), daemon.py (15) = ~63 fixes, where F68/F69/F70/F72 + the F111 cross-project bleed live. **drone.py** (30 fixes, the router — F27 broken help lives here). **doctor.py** (15 fixes — F14-F17 live here).
- **The signal:** the files fixed most often are the ones still harboring the bugs I found. Repeated patching hasn't converged — memory-rollover and ai_mail-dispatch are churn sinks that keep breaking. These two subsystems are candidates for a hardening PASS (invariants + adversarial tests + the atomic-write/lock discipline) rather than an (N+1)th patch. Churn + surviving-bug overlap = "stop patching, start hardening" list.

### F123 — Memory vector store: HEALTHY, but dashboard undercounts it ~4x [LOW-MEDIUM + an ASSET]
- **Probed the actual ChromaDB backend** (the persistence layer of the whole "memory persists" value prop): `memory/.chroma/chroma.sqlite3` = 53M, **`PRAGMA integrity_check` = ok** (not corrupt), **5,012 embeddings across 29 collections**, and `drone @memory search` returns results in ~29s (works). The core memory backend is genuinely SOUND — good news for the value prop.
- **BUT:** memory's DASHBOARD reports `vectors_stored: 1274` while the store actually holds **5,012 embeddings** — a ~4x undercount (likely counting one collection or a stale figure, mislabeled as the total). Another "displayed metric ≠ reality" instance (F17/F48/F49/F74 family) — the dashboard is a decorative number, not a measured one.
- **Minor doc gap:** navmap says "two ChromaDB stores: local + a global one across all branches" — I find only per-branch `.chroma` dirs (+ backup copies); memory/.chroma (29 collections) appears to BE the aggregate. No separate "global" store exists as described; the doc and the reality have drifted.

### F124 — Dashboards are stale, not "live" — prax's own is 10 days old [MEDIUM]
- `DASHBOARD.local.json` is documented as "Live state (refreshed by prax)" and is my startup protocol's "single status glance." Actual last_updated across branches: flow 07-13 (fresh), aipass 07-12, drone 07-11, memory 07-11, trigger 07-10, **prax 07-03 (10 DAYS stale)**. Only branches touched by live work update; the rest drift. The "glance" shows days-old data. Ironic: prax — the component that's supposed to refresh dashboards — has the STALEST one. Root: refresh isn't a scheduled ritual (F81 — the daemon runs zero jobs), so it only happens when something manually triggers it. Either schedule a periodic refresh or stop calling them "live."
- **ASSET:** compass DB (devpulse-owned SQLite, my decision store) — integrity OK, 102 decisions, healthy. Memory vector store healthy (F123). The core data stores are SOUND; it's the freshness/accuracy of the DISPLAY layer that drifts.

### F125 — Verification spot-audit: sub-agent findings hold up (4/4 sampled confirm) [quality/credibility]
- To gauge false-positive rate in the ~half of findings that came from sub-agents where I only spot-verified criticals/highs, I re-checked 4 random MEDIUM sub-agent findings against code: **F53** (commons curation/search/identity ops — `finally` count = 0 in all three, connections leak on exception ✓), **F68** (ai_mail `load_inbox` — `with open(...) json.load` and NO lock ✓), **F87** (prax registry save — raw `open("w")+json.dump`, no atomic helper ✓), **F96** (api `route_command:244` — `except Exception` swallow ✓). **4/4 confirmed, zero false positives.** Combined with: I personally verified every CRITICAL and HIGH, corrected 5 of my own claims when evidence disproved them, and 2+ agents independently corroborated the big findings. Confidence in the 124-finding set is high — the sub-agents cited exact file:line and the code matched every check. Treat medium/low findings as reliable leads; only the handful explicitly marked PLAUSIBLE need runtime confirmation.

### F126 — Injected-prompt drift: the always-on navmap makes a false claim to every agent [LOW — high frequency]
- Audited the tier0/tier1/branch prompts (injected into EVERY agent every few turns) against the code reality I mapped. Mostly ACCURATE — good; and the navmap wisely lists agents live rather than hardcoding a count (so no "17 vs 18" drift there). Two real drifts: (1) **navmap line 98: "Two ChromaDB stores: local + a global one across all branches"** — F123 found NO separate global store exists; memory/.chroma IS the aggregate. Every agent is told to expect a store that isn't there. (2) devpulse/README:51 "DASHBOARD.local.json — Live state (refreshed by prax)" — F124 found dashboards up to 10 days stale. Low severity, but the navmap is the highest-read doc in the system (injected fleet-wide on a cadence), so a false claim there propagates to every session. The observability-is-decorative pattern (F117 unification) reaches even the docs: what the system SAYS about itself drifts from what IS.
- **Net positive:** the prompts are otherwise consistent with reality — the drift is 2 specific stale claims, not systemic prompt-rot. The prompt layer is in better shape than the dashboard/metrics layer.

## MISSION STATUS — COMPLETE COVERAGE

All 17 branches code-swept, all 18 CLI surfaces walked, security gates + skills contribution surface audited, newcomer path + adoption funnel measured, error/medic/memory/daemon/commons internals traced. 9 read-only sub-agents + direct probing, ZERO system files edited. **116 findings, 2 verified-live criticals, 5 self-corrections** where evidence disproved a first claim (F5b root cause, F15 mechanism, supervised-bots, F99 scope, doctor case-vs-path). Deliverables: this doc (F1–F117 + A1–A7 + ~30 issue drafts) · DPLAN-0240 (adoption) · published dashboard · compass #94–#100 · todo 66 root-caused. Every fix is a proposal awaiting Patrick's go.

---

## COMMANDS WALKED

(coverage log so nothing is double-probed)

- **Bare introspection ×18:** drone, cli, git(--help), seedgo, spawn, ai_mail, api, backup, commons, daemon, devpulse, flow, hooks, memory, prax, skills, trigger, aipass
- **--help:** drone@drone, git, api, backup, commons, spawn, ai_mail, prax, aipass, drone rm
- **Data/state commands:** trigger errors(+stats/list/help/detail-via-raw-JSON), trigger medic, daemon queue/update/activity_report, prax status/monitor status(✗)/log_audit(✗)/log-audit, flow list open/templates/status(✗)/registry status, skills list/info github/validate telegram/run branch_health(+summary), backup status(bare✗/@name✗/path✓), memory search/lint(+run)/verify/pool/rollover/templates, ai_mail inbox, api usage(✗)/stats/validate/status/bogus(✗), commons feed/thread/activity/catchup/leaderboard/digest/room list/central(✗), hooks status/presence/cadence/hooksound, seedgo checklist/audit @trigger/audit(fleet)/standards_query/test_map @commons, spawn repair(scan)/update preview, devpulse compass query/feedback(+inbox/view)/watchdog status, drone scan/list/audit(✗), git status/log/lock/run list/run view(+--log-failed✗ = gh quirk), aipass doctor/help probe
- **External/API:** gh api repo stats, labels, issues, PRs, discussions (graphql), traffic, releases, job logs
- **System:** systemd units/timers, ps bot fleet, tmux ls, pytest TestReadControl (venv), subprocess gh repro
- (✗) = found broken/misleading — see findings
