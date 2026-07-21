# Working in this repository

Org-wide policy in the managed CLAUDE.md applies on top of this file; read it first if you haven't.

## Stack

Python, dbt-core, DuckDB, Parquet. Orchestration is Jenkins. Each client runs an isolated deployment in their own cloud; this codebase must work for all of them with zero code changes per client, which is why everything client-specific is YAML.

## Layout that matters

- dbt models: `staging/` is 1:1 with sources and light cleaning; `intermediate/` holds business logic and joins; `features/` is final feature vectors for ML; `marts/` is aggregates for BI. Put logic at the right layer; feature definitions never depend on ML output.
- Client configs extend a common base. New client means new YAML, never new code.
- Features are immutable snapshots: computed for a date, stored permanently, with metadata (description, computation date, source).

## Conventions

- DuckDB for analytical queries in prototypes and tools. Not SQLite, not Postgres.
- Parquet for file-based data.
- Run ruff before considering Python work done; the PostToolUse hook will tell you about violations anyway, so fix them as they appear.
- Tests use synthetic data only. Never fixtures derived from real customer rows.

## Hooks in this repo

Three enforced gates run on your tool calls: a customer-data boundary (blocks `data/staging/`, `.parquet`, `.duckdb`, `.env`, and credential-shaped content), a no-hardcoded-client gate on `.py` and `.sql`, and ruff feedback after edits. If a gate blocks you, the message says what to do instead; don't look for workarounds, and tell the engineer if you think a block is a false positive.

## Knowledge

Search the voziq-brain repo before re-deriving anything about clients, pipelines, or past decisions. File durable lessons there with `/brain-memo` at session end.
