# /brain-lint

The maintenance loop, borrowed from Karpathy's LLM wiki pattern but adapted to our review model: an agent finds the problems, a human merges the fixes. Run it monthly, or after any big platform change. Copy into the brain repo's `.claude/commands/brain-lint.md`, or run it from a session opened in the brain checkout.

---

Audit this knowledge repo for consistency and health. Read every note, then work through these checks.

1. Contradictions. Two notes that assert incompatible things. Pair them up and, where the truth is determinable from timestamps or context, mark the loser `status: superseded` with a forward link. Where it isn't determinable, list the pair for a human to adjudicate.

2. Staleness. Notes describing systems, processes, or client arrangements that have plausibly changed. Flag, don't guess: propose a `status: draft` demotion only when another note or commit proves the staleness.

3. Orphans and dead links. Notes nothing references and no tag reaches, and Related-section links pointing at files that no longer exist. Fix the links; for orphans, add tags or propose promotion or supersession.

4. Front matter. Every note needs valid YAML with at least `type`. Fix violations using the folder's template.

5. Promotion candidates. The same lesson appearing in two or more session notes. Draft the promoted decision, runbook, or domain note, and mark the sources superseded with forward links.

6. Hygiene. Anything that looks like a credential, end-customer identifier, raw client data, or commercially sensitive material that slipped past review. Do not copy the finding into your report; describe its location and flag it as urgent.

Then file the results: branch `lint/YYYY-MM-DD`, commit the fixes, open a merge request whose description lists what was found, what was fixed, and what needs human adjudication. Never push to main. If nothing at all was found, say so and stop; do not open an empty MR.
