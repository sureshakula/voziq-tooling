---
name: system_status
description: Check system health -- disk usage, memory, running processes, uptime
version: 1.0.0
tags: [system, monitoring, health]
requires:
  pip: []
  bins: []
  config: []
has_handler: true
---

# System Status Skill

Check system health metrics without leaving your workflow. Returns structured data about disk usage, memory, running processes, and system uptime.

## Available Actions

| Action      | Description                                    |
|-------------|------------------------------------------------|
| `disk`      | Disk usage for the root filesystem             |
| `memory`    | Memory usage from /proc/meminfo (Linux)        |
| `uptime`    | System uptime from /proc/uptime                |
| `processes` | Count of currently running processes            |
| `summary`   | All of the above combined into one report       |

## Usage

```bash
drone @skills run system_status disk
drone @skills run system_status memory
drone @skills run system_status uptime
drone @skills run system_status processes
drone @skills run system_status summary
```

## Output Format

All actions return structured dicts:

```python
{"success": True, "output": "...", "error": None}
```

## When to Use

- Quick health check before resource-intensive operations
- Diagnosing slow performance (memory pressure, disk full)
- Monitoring system state during long-running tasks
- Getting a snapshot of system health for reports

## Notes

- All data comes from stdlib / procfs -- no external dependencies
- Memory info reads from `/proc/meminfo` (Linux only)
- Uptime reads from `/proc/uptime` (Linux only)
- Disk usage uses `shutil.disk_usage()` (cross-platform)
- Process count uses `/proc` directory listing (Linux only)
