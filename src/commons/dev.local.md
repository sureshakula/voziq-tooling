# dev.local.md - commons
```
Branch: src/commons
Created: 2026-03-10
```

## Issues

- 1 type error: `dashboard_writer.py` imports `aipass.devpulse.apps.modules.dashboard` which can't resolve (devpulse dependency)
- Architecture: missing `logs/`, `dropbox/` dirs (template requirements, low priority)

---

## Todos

- Investigate devpulse dashboard import — may need conditional import or email devpulse

---

## Session Notes

### 2026-03-10 — First Systems Check
- **DB init fixed**: 5 bugs — sys.path shadowing, double .aipass path, wrong registry name, registry discovery, identity detection
- **Seedgo audit**: 98%
- **All commands working**: feed, post, room, enter, craft, search, explore, leaderboard, capsules, who
- **15/15 branches registered** as agents
- **Identity detection**: uses AIPASS_CALLER_CWD + .trinity/passport.json walk-up
