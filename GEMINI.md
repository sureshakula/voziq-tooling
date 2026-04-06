# AIPass

A multi-agent framework where autonomous citizens live in branches and deploy disposable agents to do work.

## Branches

Every branch follows this structure:
```
src/aipass/{name}/
├── .trinity/           # Identity & memory (passport.json, local.json, observations.json)
├── .aipass/            # System prompt
├── .ai_mail.local/     # Mailbox (inbox.json, sent/)
├── apps/
│   ├── {name}.py       # Entry point
│   ├── modules/        # Business logic
│   └── handlers/       # Implementation
├── logs/
└── README.md
```

15 branches: drone, seedgo, prax, cli, flow, ai_mail, api, trigger, spawn, devpulse, backup, daemon, memory, commons, skills

## Commands

drone systems                                    # List all branches
drone @seedgo audit aipass                       # Run standards audit
drone @ai_mail inbox                             # Check email
drone @ai_mail email @target "Subject" "Body"    # Send email
drone @flow list open                            # Active plans

## Identity

Read .trinity/passport.json to understand your role. Read .trinity/local.json for session history. Read STATUS.local.md for current work.

## Key Principles

- Code is truth. Running code beats architecture.
- Memory is everything. Update .trinity/ often.
- Dispatch, don't do. Branches are experts in their domain.
- Fail honestly. Errors over silent fallbacks.
