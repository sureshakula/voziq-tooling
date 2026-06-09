# Cadence Investigation — DPLAN-0200

Per-turn injection cadence mechanism for prompt loaders (global_loader, branch_loader, identity).
Investigation only — no build. Findings for @devpulse.

---

## 1. Per-session turn counter — session keying

YES, fully reliable. `CLAUDE_CODE_SESSION_ID` is available as an env var to every hook invocation (confirmed live: UUID format, stable across turns, unique per session). This is the same mechanism `auto_process.py` already uses for its once-per-session guard (`auto_process.py:24`, `/tmp` sentinel keyed by session_id).

`hook_data` (the parsed stdin JSON) does NOT contain session_id — it comes from the env var only. For UserPromptSubmit, hook_data contains `{"user_prompt": "..."}` and sometimes other fields, but session keying must use `os.environ`.

A new session gets a new UUID — fresh counter automatically. No inheritance risk.

## 2. Counter state location

Engine has NO per-session state infrastructure today. `auto_process.py`'s `/tmp` sentinel is the closest precedent — existence-only, no data payload.

**Recommended:** `/tmp/aipass-cadence-{session_id}.json` — tiny JSON file (`{"turn": N}`), one per session, naturally cleaned on reboot. Same `/tmp` pattern as auto_process but with a data payload instead of touch-only.

This is net-new state. The engine doesn't need to know about it — a shared cadence module handles it.

## 3. Mechanism sketch — feasible, confirmed

Shared module: `apps/handlers/prompt/cadence.py`

Key insight: the bridge spawns ONE Python process per UserPromptSubmit dispatch, and the engine runs all handlers SEQUENTIALLY within that process (`engine.py:114` loop). So a module-level cache ensures the counter increments exactly ONCE per turn, even though 3 handlers call into it.

```python
# cadence.py sketch
_turn = None  # process-level cache, reset each dispatch = each turn

def _load_and_increment():
    global _turn
    if _turn is not None:
        return _turn  # already incremented this dispatch
    path = _state_path()  # /tmp/aipass-cadence-{session_id}.json
    if path is None:
        _turn = 0
        return 0
    count = 0
    if path.exists():
        data = json.loads(path.read_text())
        count = data.get("turn", 0) + 1
    path.write_text(json.dumps({"turn": count}))
    _turn = count
    return count

def should_fire(offset, period=5):
    turn = _load_and_increment()
    if turn == 0:
        return True  # first turn ALWAYS fires
    return (turn % period) == offset
```

Each loader adds ONE guard line:

```python
from aipass.hooks.apps.handlers.prompt.cadence import should_fire

def handle(hook_data):
    if not should_fire(offset=0):  # different offset per loader
        return {"stdout": "", "exit_code": 0}
    # ... existing logic unchanged
```

**Stagger example (period=5):**

| Loader | Offset | Fires on turns |
|--------|--------|----------------|
| global_loader | 0 | 0, 5, 10, 15... |
| branch_loader | 2 | 0, 2, 7, 12... |
| identity | 4 | 0, 4, 9, 14... |

Turn 0 = ALL fire (first turn guarantee). After that, max 1 loader per turn, each refreshed every 5 turns, staggered so they never collide.

## 4. Edge cases

**FIRST TURN:** Handled — `should_fire` returns True unconditionally when `turn==0`. Agent always gets full context on session start.

**CONCURRENT SESSIONS:** Safe — counter file is keyed by session_id. Two sessions in different branches use different files, no conflict.

**COMPACTION — CRITICAL INTERACTION:** When Claude Code compacts, injected prompts from prior turns get summarized or dropped from context. If a loader's next fire is 3-4 turns away post-compaction, the agent operates without that prompt content until it re-fires.

**Fix:** Add a PreCompact handler (or extend the existing `compact.py`) that RESETS the cadence counter to -1. On the next UserPromptSubmit after compaction, `_load_and_increment` reads `-1+1=0`, and turn 0 = all loaders fire. Cost: one extra full-injection turn after each compaction, which is exactly right — the agent needs the prompts re-injected after losing context.

**FILE I/O COST:** Negligible. One stat + read + write of ~15 bytes per turn. Way cheaper than the ~3,750 tokens saved.

## 5. Robustness assessment — SOLID

**Strengths:**
- Pattern is simple and deterministic. No async, no races, no distributed state.
- Sequential dispatch (`engine.py`) guarantees no concurrent access to the counter file within a single turn.
- `/tmp` cleanup on reboot = no accumulation. Session files are tiny and ephemeral.
- Module-level cache (`_turn`) prevents double-increment even if called from multiple handlers.
- Testable in isolation — mock `os.environ` + `/tmp` path, assert `should_fire` returns correctly.

**One fragility to flag:** if Claude Code ever changes to dispatch UserPromptSubmit handlers in PARALLEL (separate processes), the module-level cache breaks and you'd get 3 increments per turn. Current architecture is sequential — but worth a comment noting the assumption. Mitigation: use file locking (`fcntl.flock`) if parallelism ever arrives, but don't build it now.

No other fragility concerns. The mechanism is as robust as `auto_process.py`'s session guard, which has been running reliably since S10.

---

## Summary

Fully feasible. Shared `cadence.py` module, `/tmp` state file keyed by session_id, modulo+offset check per handler, turn-0 guarantee, PreCompact counter reset for compaction safety. Ready for implementation when DPLAN-0200 greenlights it.

*Investigation by @hooks, 2026-06-08*
