# VOZIQ agent tooling

Starter kits for VOZIQ's AI-assisted engineering workflow, built on native Claude Code. Two pieces:

| Folder | What it is |
|---|---|
| `voziq-brain/` | Shared team knowledge repo scaffold: folder conventions, templates, contribution rules, the `/brain-memo` capture command, and an MCP server spec. Meant to become its own repository. |
| `voziq-pilot-kit/` | Per-seat pilot kit: org-policy CLAUDE.md, project CLAUDE.md template matched to the dbt/DuckDB/Parquet stack, and three enforced hooks (customer-data boundary, no hardcoded client identifiers, ruff on edit). |
| `project-seed/` | The tool-agnostic on-ramp seeded into every project via the GitLab project template: AGENTS.md brain section (with CLAUDE.md shim), the brain-memo command for Claude Code, Codex, and Copilot, CI enforcement jobs, and the `BRAIN_REPO_PATH` convention. |

Each folder's README covers deployment. Start with the pilot kit on two or three seats, seed the brain repo in week one, and judge both after two weeks.
