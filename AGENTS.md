# AIPass

Multi-agent framework. Autonomous agents (citizens) live in branches, deploy disposable sub-agents to do work.

User: user

# Startup protocol

On any greeting, silently read these files and run the commands — no narration, no announcing steps. Just do it and respond with the status.

 - Read (cat): `.trinity/passport.json`, `.trinity/local.json`, `.trinity/observations.json`, `README.md`, `STATUS.local.md`
 - Check: `drone @ai_mail inbox` — process any mail, don't ask.
 - Run: `drone @git status`
 - Refresh: If `STATUS.local.md` is stale (last updated date older than latest session in local.json), update it from your memories. Keep Current Work accurate.

Use drone commands for all operations. Never raw git, gh, file access, or python -m when drone provides it.

# Memories

Update `.trinity/` at natural breakpoints, after milestones, and on `/memo`.