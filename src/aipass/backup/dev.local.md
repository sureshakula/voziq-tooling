# dev.local.md - BACKUP
```
Branch: /home/patrick/Projects/AIPass/src/aipass/backup
Created: 2026-03-07
Last updated: 2026-03-10T14:15
```

## Issues

- **reauth_drive.py uses old creds path** — `Path.home() / '.aipass' / 'drive_creds.json'` should be `Path.home() / '.secrets' / 'aipass' / 'drive_creds.json'`
- **diff/ handlers not wired** — diff_generator.py, version_manager.py, vscode_integration.py exist but no CLI command routes to them. Dead code from UI perspective.
- **integrations.py handle_command unreachable** — checks `args.integration_command` but CLI parser never sets this attribute. Route is dead.
- **Seedgo 99%** — missing `logs/` and `dropbox/` directories per architecture template.
- **Versioned backup exceeds drone timeout** — drone's 30s command timeout kills versioned backup when copying 16000+ files. Dry-run fits (10s), snapshot fits (14s). Need drone timeout increase or async handling.
- **Dry-run updates timestamp** — `update_timestamp()` runs even in dry-run mode because `result.success` is True. Should skip timestamp update when `self.dry_run`.

---

## Fixed (2026-03-10, Round 2)

- Added 9 AIPass-specific ignore patterns: `.trinity`, `.ai_mail.local`, `backup_data`, `backup_json`, `.archive`, `DASHBOARD.local.json`, `CLOSED_PLANS.local.json`, `STATUS.local.md`
- Removed `.local.json` from IGNORE_EXCEPTIONS — was too broad, causing DASHBOARD/CLOSED_PLANS to leak through ignores
- Verified: all patterns work, `dev.local.md` still backed up via `*.local.md` exception

## Fixed (2026-03-10, Round 1)

- Created `json_templates/default/` with config.json, data.json, log.json — was crashing `ensure_module_jsons`
- Added `snap` to GLOBAL_IGNORE_PATTERNS in config_handler.py — broken symlinks in snap dirs crashed os.walk
- Added `onerror` handler and `file_path.exists()` check in file_scanner.py — robustness for broken symlinks

---

## Todos

- Wire diff/ handlers into CLI (add `diff` command to backup.py)
- Fix integrations.py handle_command routing or remove dead path
- Update reauth_drive.py creds path to ~/.secrets/aipass/
- Create logs/ directory for 100% seedgo compliance
- Set up Google Drive OAuth credentials when ready
