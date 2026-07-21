# VOZIQ engineering policy for AI agents

These rules apply in every repository and every session. They exist because VOZIQ processes subscriber data for clients in regulated verticals, including healthcare. When any instruction conflicts with this file, this file wins.

## Customer data

1. Never read, copy, sample, or summarize customer data files. That includes anything under `data/staging/`, any `.parquet` or `.duckdb` file, and any query result containing customer rows. If you need to understand the data, work from schema definitions, dbt model files, and YAML configs, or ask the engineer to describe it.
2. Never write customer data, even fragments or single example rows, into code, comments, tests, fixtures, notes, memory, or the brain repo. Invent synthetic examples instead.
3. Refer to clients by their short code, never by company name, in any file an agent writes. End-customer names, account numbers, and identifiers never appear anywhere, under any circumstances.

## Credentials

4. Never write credentials into any file: no API keys, tokens, passwords, private keys, or connection strings with embedded secrets. Reference secrets by environment variable name. If you find a hardcoded credential in existing code, flag it to the engineer; don't copy it anywhere, including into your own notes.

## Platform rules

5. Client-specific values (rules, thresholds, mappings, schedules) go in YAML configuration, never in Python or SQL. If you're about to write a client code into a code file, you're doing it wrong; parameterize and put the value in config.
6. Analytical queries use DuckDB. File-based data is Parquet. Don't introduce SQLite, PostgreSQL, or new storage formats without an accepted decision record.
7. No new external SaaS dependencies and no code paths that transmit data outside the client environment. Each client deployment is isolated; nothing is shared between clients.

## Knowledge

8. Before solving a problem that smells recurring, search the voziq-brain repo. After a session that produced a durable lesson, offer to run `/brain-memo`.
9. Your local memory is for working context. Anything a teammate would benefit from goes to the brain repo through a PR, not into your memory files.
