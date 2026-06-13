# AIPass

Multi-agent framework. Autonomous agents (citizens) live in branches, deploy disposable sub-agents to do work.

User: user

# Startup protocol

On any greeting, silently run this sequence — no narration, no announcing steps. Just do it and respond with the status.

These steps are sequential and dependent — run each ONCE, wait for the result, then proceed. Never batch a command with its own follow-up read, and never fire duplicate calls. If output looks blank, wait — don't retry.

 - Read: `.trinity/passport.json`, `.trinity/local.json`, `.trinity/observations.json`, `README.md`
 - Refresh: `drone @prax dashboard refresh @<self>` — where `<self>` is your branch name (CWD directory name)
 - Dashboard: Read `DASHBOARD.local.json` — act on what needs attention (new mail → check inbox, active plans → note them). This is your single status glance.

Use drone commands for all operations. Never raw git, gh, file access, or python -m when drone provides it.

# Memories

Update `.trinity/` at natural breakpoints, after milestones, and on `/memo`.