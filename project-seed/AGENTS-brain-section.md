# Team knowledge (append this section to the project AGENTS.md)

## The brain

VOZIQ's shared knowledge lives in the brain repo (`voziq/brain` on git.voziq.com; local checkout at `$BRAIN_REPO_PATH`). Before solving anything that smells recurring, search it: client quirks, pipeline gotchas, past decisions, runbooks. Grep works; front-matter tags are reliable; trust `decisions/` and `runbooks/` as reviewed team positions.

At the end of a session that produced a durable lesson, file a brain memo: distill the lesson into a half-page note using the brain's `sessions/TEMPLATE.md`, show it to the engineer for approval, then open a merge request to the brain (branch `memo/YYYY-MM-DD-slug`, note at `sessions/YYYY-MM-DD-slug.md`). If your tool has the `/brain-memo` command installed, use it; the procedure is the same either way. All brain writes go through merge requests, never direct pushes, and never include credentials, end-customer identifiers, client data, or commercially sensitive material.
