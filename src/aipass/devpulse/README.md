[← Back to AIPass](../../../README.md)

# DevPulse

> Orchestration hub for AIPass. Plans, coordinates, dispatches. Never the builder.

DevPulse is the central coordination branch. It does not ship features of its own — it works with the user on design, dispatches real work to branch specialists, tracks plans and memory, and keeps the system moving. If a task belongs to another branch, DevPulse emails that branch and waits for the reply.

## Start here

| You want to | Read |
|---|---|
| Install, update, uninstall, or troubleshoot | [SETUP.md](SETUP.md) |
| What's happening right now | [STATUS.local.md](STATUS.local.md) |
| Identity, memory, session history | [`.trinity/`](.trinity/) |
| Diagnostic scanners | [`tools/`](tools/) |
| Branch health audits | [`branch_audits _only/`](branch_audits%20_only/) |
| Active plans | `drone @flow list open` |

## Invoke

```bash
cd src/aipass/devpulse
claude
```

Say "hi" and DevPulse picks up where the last session left off.

## Role in one line

Manager, not builder. Coordinates via dispatch + sub-agents. Does not read or edit code across branches — that burns context that belongs to coordination.

---

[← Back to AIPass](../../../README.md)
